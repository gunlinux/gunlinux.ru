// k6 load test for gunlinux.ru.
//
// wrk-style HTTP load, scripted in JavaScript (k6). Unlike a canned URL list:
//   - the homepage is fetched in setup() and real post/tag aliases are
//     extracted from it, so the test always exercises live pages;
//   - full-page HTML and htmx fragment requests (HX-Request header) are mixed,
//     matching the site's dual-mode rendering; fragment latency is tracked
//     separately (page_fragment_duration);
//   - POST /md/ (the markdown-preview renderer, the most CPU-heavy public
//     endpoint) is hammered with a realistic urlencoded body;
//   - thresholds encode the SLO, so a degraded site fails the run.
//
// Usage:
//   k6 run scripts/perf/load-test.js                       # localhost:8000
//   BASE_URL=https://gunlinux.ru k6 run scripts/perf/load-test.js
//   k6 run --stage 5s:20,30s:100,10s:0 scripts/perf/load-test.js   # custom profile
//
// Install k6: brew install k6  (or https://k6.io/docs/getting-started/installation/)

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';

// Load profile: warm-up -> peak -> cool-down. Override with `k6 run --stage ...`.
export const options = {
  stages: [
    { duration: '10s', target: 10 }, // warm-up
    { duration: '30s', target: 50 }, // peak
    { duration: '10s', target: 0 }, // cool-down
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
    checks: ['rate>0.99'],
    page_fragment_duration: ['p(95)<300'],
    md_render_duration: ['p(95)<300'],
  },
};

const pageFull = new Trend('page_full_duration');
const pageFragment = new Trend('page_fragment_duration');
const mdRender = new Trend('md_render_duration');

const HX = { 'HX-Request': 'true' };

const mdSample = [
  '# Заголовок статьи',
  '',
  'Обычный **жирный** текст с `инлайн-кодом` и [ссылкой](https://gunlinux.ru).',
  '',
  '```rust',
  'fn main() {',
  '    println!("hello");',
  '}',
  '```',
].join('\n');

function reqHome() {
  const res = http.get(`${BASE}/`, { tags: { page: 'home' } });
  check(res, { 'home 200': (r) => r.status === 200 });
  pageFull.add(res.timings.duration);
}

function reqHomeHx() {
  const res = http.get(`${BASE}/`, { headers: HX, tags: { page: 'home-hx' } });
  check(res, { 'home fragment 200': (r) => r.status === 200 });
  pageFragment.add(res.timings.duration);
}

function reqPosts() {
  const res = http.get(`${BASE}/posts`, { tags: { page: 'posts' } });
  check(res, { 'posts 200': (r) => r.status === 200 });
}

function reqPost(data) {
  const alias = data.posts.length
    ? data.posts[Math.floor(Math.random() * data.posts.length)]
    : 'posts';
  const res = http.get(`${BASE}/${alias}`, { tags: { page: 'post' } });
  check(res, { 'post 200': (r) => r.status === 200 });
  pageFull.add(res.timings.duration);
}

function reqPostHx(data) {
  const alias = data.posts.length
    ? data.posts[Math.floor(Math.random() * data.posts.length)]
    : 'posts';
  const res = http.get(`${BASE}/${alias}`, { headers: HX, tags: { page: 'post-hx' } });
  check(res, { 'post fragment 200': (r) => r.status === 200 });
  pageFragment.add(res.timings.duration);
}

function reqTags() {
  const res = http.get(`${BASE}/tags`, { tags: { page: 'tags' } });
  check(res, { 'tags 200': (r) => r.status === 200 });
}

function reqTag(data) {
  if (!data.tags.length) {
    reqTags();
    return;
  }
  const alias = data.tags[Math.floor(Math.random() * data.tags.length)];
  const res = http.get(`${BASE}/tags/${alias}`, { tags: { page: 'tag' } });
  check(res, { 'tag 200': (r) => r.status === 200 });
}

function reqFeeds() {
  const path = Math.random() < 0.5 ? '/sitemap.xml' : '/rss.xml';
  const res = http.get(`${BASE}${path}`, { tags: { page: 'feeds' } });
  check(res, { 'feed 200': (r) => r.status === 200 });
}

function reqMd() {
  const res = http.post(`${BASE}/md/`, { data: mdSample }, { tags: { page: 'md' } });
  check(res, { 'md 200': (r) => r.status === 200 });
  mdRender.add(res.timings.duration);
}

// Request mix (relative weights). post/post-hx degrade to /posts when the
// site has no discoverable aliases; tag degrades to the tag index.
const MIX = [
  { weight: 20, name: 'home', fn: reqHome },
  { weight: 10, name: 'home-hx', fn: reqHomeHx },
  { weight: 10, name: 'posts', fn: reqPosts },
  { weight: 25, name: 'post', fn: reqPost },
  { weight: 15, name: 'post-hx', fn: reqPostHx },
  { weight: 5, name: 'tags', fn: reqTags },
  { weight: 5, name: 'tag', fn: reqTag },
  { weight: 5, name: 'feeds', fn: reqFeeds },
  { weight: 5, name: 'md', fn: reqMd },
];

let cumulative = [];
let mixTotal = 0;
for (const m of MIX) {
  mixTotal += m.weight;
  cumulative.push({ end: mixTotal, entry: m });
}

function pick() {
  const r = Math.random() * mixTotal;
  for (const c of cumulative) {
    if (r < c.end) return c.entry;
  }
  return MIX[MIX.length - 1];
}

// Fetch the index, the posts listing and the tag cloud once, then harvest
// real post/tag aliases from their links so the test hits live pages.
export function setup() {
  const home = http.get(`${BASE}/`);
  const postsPage = http.get(`${BASE}/posts`);
  const tagsPage = http.get(`${BASE}/tags`);

  const blocked = ['/tags', '/admin', '/static', '/posts', '/hx/', '/md/', '/rss.xml', '/sitemap.xml', '/robots.txt'];
  const postAliases = [];
  const seenPosts = {};
  for (const res of [home, postsPage]) {
    if (res.status !== 200 || !res.body) continue;
    for (const a of extractAliases(res.body, '/', blocked)) {
      if (!seenPosts[a]) {
        seenPosts[a] = true;
        postAliases.push(a);
      }
    }
  }

  const tagAliases = [];
  const seenTags = {};
  if (tagsPage.status === 200 && tagsPage.body) {
    for (const a of extractAliases(tagsPage.body, '/tags/', [])) {
      if (!seenTags[a]) {
        seenTags[a] = true;
        tagAliases.push(a);
      }
    }
  }

  return {
    posts: postAliases.slice(0, 10),
    tags: tagAliases.slice(0, 5),
    homeStatus: home.status,
  };
}

// Harvest bare path segments from href="/prefix/seg" links, skipping any
// whose full path starts with one of `blocked`.
function extractAliases(body, prefix, blocked) {
  const re = new RegExp('href="' + prefix + '([a-z0-9][a-z0-9_-]*)"', 'g');
  const seen = {};
  const out = [];
  let m;
  while ((m = re.exec(body)) !== null) {
    const full = prefix + m[1];
    let skip = false;
    for (let i = 0; i < blocked.length; i++) {
      if (full.startsWith(blocked[i])) {
        skip = true;
        break;
      }
    }
    if (!skip && !seen[m[1]]) {
      seen[m[1]] = true;
      out.push(m[1]);
    }
  }
  return out;
}

export default function (data) {
  const entry = pick();
  entry.fn(data);
  sleep(0.2 + Math.random() * 0.3); // think time 200–500 ms
}

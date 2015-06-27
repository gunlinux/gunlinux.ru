// configuration
var input = 'pro/static/src/style.css';
var output = 'pro/static/css/';
var autoprefixerOptions = {browsers: ['> 1%', 'IE 7']};
var atImport = require('postcss-import');
var vhash = require('gulp-vhash');
var gulp = require('gulp');
var postcss = require('gulp-postcss');
var autoprefixer = require('autoprefixer-core');
var csslint = require('gulp-csslint');
var download = require('gulp-download');
var htmllint = require('gulp-htmllint');
var html5Lint = require('gulp-html5-lint');

processors = [
    atImport({path: ['pro/static/sass']}),
    require('autoprefixer-core'),
    require('postcss-nested'),
    autoprefixer(autoprefixerOptions)
];

gulp.task('sass', function () {
    return gulp.src(input)
        .pipe(postcss(processors))
        .pipe(gulp.dest(output));
});

var urls = [
    'http://dev.gunlinux.org'
];

gulp.task('testprepare', function () {
    return download(urls)
        .pipe(gulp.dest('tmp/test/'));
});

gulp.task('htmllint', ['testprepare'], function () {
    return gulp.src('tmp/test/*')
        .pipe(htmllint())
        .pipe(html5Lint());
});

gulp.task('hash', ['sass'], function () {
    return gulp.src('./pro/static/{css,js}/*.css')
        .pipe(vhash('./pro/templates/**/*.html'));
});

gulp.task('csstest', ['sass'], function () {
    gulp.src('pro/static/css/style.css')
    .pipe(csslint({
        'compatible-vendor-prefixes':false,
        'box-sizing':false,
        'star-property-hack':false,
        'unique-headings':false,
        'qualified-headings':false

    }))
    .pipe(csslint.reporter());
});
gulp.task('test', ['csstest', 'htmllint']);
gulp.task('build', ['sass', 'hash']);
gulp.task('default', ['build', 'test']);


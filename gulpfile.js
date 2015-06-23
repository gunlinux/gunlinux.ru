// configuration
var input = 'pro/static/src/style.css';
var output = 'pro/static/css/';
var autoprefixerOptions = {browsers: ['> 1%', 'IE 7']};
var atImport = require('postcss-import');

var gulp = require('gulp');
var postcss = require('gulp-postcss');
var autoprefixer = require('autoprefixer-core');
var nano = require('gulp-cssnano');
var vhash = require('gulp-vhash');

processors = [
    atImport({path: ['pro/static/sass']}),
    require('autoprefixer-core'),
    require('postcss-nested'),
    autoprefixer(autoprefixerOptions)
];

gulp.task('sass', function () {
    return gulp.src(input)
        .pipe(postcss(processors))
        .pipe(nano())
        .pipe(gulp.dest(output));
});

gulp.task('hash', function () {
    return gulp.src(
        'pro/static/{css,js}/*.{css,js}'
    )
    .pipe(vhash('pro/templates/**/*.html'));
});

gulp.task('default', ['sass', 'hash']);

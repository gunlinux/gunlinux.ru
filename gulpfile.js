// configuration
var css = 'pro/static/src/*.css';
var output = 'pro/static/css/';
var autoprefixerOptions = {browsers: ['> 1%', 'IE 7']};

var gulp = require('gulp');
var postcss = require('gulp-postcss');
var notify = require('gulp-notify');
var sourcemaps = require('gulp-sourcemaps');
var concat = require('gulp-concat');

// utils
function errorhandler() {
    var args = Array.prototype.slice.call(arguments);
    // Send error to notification center with gulp-notify
    notify.onError({
        title: 'Compile Error',
        message: '<%= error %>'
    }).apply(this, args);

    // Keep gulp from hanging on this task
    this.emit('end');
};

processors = [
    require('postcss-nested'),
    require('autoprefixer')(autoprefixerOptions)
];

gulp.task('styles', function () {
    return gulp.src(css)
        .pipe(sourcemaps.init())
        .pipe(postcss(processors).on('error', errorhandler))
        .pipe(concat('styles.css'))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(output));
});

gulp.task('watch', function () {
    // Отслеживание файлов .css
    gulp.watch(css, ['styles']);
});

gulp.task('default', ['styles']);

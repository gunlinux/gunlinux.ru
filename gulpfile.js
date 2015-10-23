// configuration
var css = 'pro/static/src/*.css';
var output = 'pro/static/css/';

var gulp = require('gulp');
var postcss = require('gulp-postcss');
var notify = require('gulp-notify');
var sourcemaps = require('gulp-sourcemaps');
var inlinesource = require('gulp-inline-source');
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

var autoPrefixerOptions = {browsers: ['last 2 versions']};

processors = [
    require('postcss-import'),
    require('postcss-nested'),
    require('postcss-cssnext')({
        browsers: ['last 2 versions', 'ie 10', 'ie 11'],
        features: {
            rem: true
        }
    }),
    require('postcss-discard-comments'),
    require('autoprefixer')(autoPrefixerOptions),
    require('cssnano')({autoprefixer: autoPrefixerOptions})
];

gulp.task('styles', function () {
    return gulp.src(css)
        .pipe(sourcemaps.init())
        .pipe(postcss(processors).on('error', errorhandler))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(output));
});

gulp.task('inlinesource', ['styles'], function () {
    return gulp.src('pro/templates/layout.html')
        .pipe(inlinesource({compress: false}))
        .pipe(gulp.dest('pro/templates/'));
});

gulp.task('watch', function () {
    // Отслеживание файлов .css
    gulp.watch('pro/static/src/**/*.css', ['styles', 'inlinesource']);
});

gulp.task('default', ['styles']);

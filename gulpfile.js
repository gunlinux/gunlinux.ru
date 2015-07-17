// configuration
var input = 'pro/static/src/style.css';
var output = 'pro/static/css/';
var autoprefixerOptions = {browsers: ['> 1%', 'IE 7']};

var gulp = require('gulp');
var postcss = require('gulp-postcss');
var csslint = require('gulp-csslint');

processors = [
    require('postcss-import')({path: ['pro/static/sass']}),
    require('autoprefixer-core'),
    require('postcss-nested'),
    require('autoprefixer-core')(autoprefixerOptions)
];

gulp.task('sass', function () {
    return gulp.src(input)
        .pipe(postcss(processors))
        .pipe(gulp.dest(output));
});

gulp.task('csstest', ['sass'], function () {
    return gulp.src('pro/static/css/style.css')
        .pipe(csslint({
            'compatible-vendor-prefixes':false,
            'box-sizing':false,
            'star-property-hack':false,
            'unique-headings':false,
            'qualified-headings':false,
            'font-sizes':false
        }))
        .pipe(csslint.reporter());
});

gulp.task('default', ['sass', 'csstest']);

gulp.task('test', ['csstest']);

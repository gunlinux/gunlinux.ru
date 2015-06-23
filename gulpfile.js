
// configuration
var input = 'pro/static/src/style.css';
var output = 'pro/static/css/';
var autoprefixerOptions = { browsers: ['> 1%', 'IE 7'] };
var atImport = require("postcss-import");

var gulp = require('gulp'),
    postcss = require('gulp-postcss'),
    autoprefixer = require('autoprefixer-core'),
    nano = require('gulp-cssnano');

processors = [
    atImport({path: ["pro/static/sass"]}),
    require('autoprefixer-core'),
    require('postcss-nested'),
    autoprefixer(autoprefixerOptions)
    /*
    function(css) {
        // sans-serif fallback
        css.eachDecl('font-family', function(decl) {
            decl.value = decl.value + ', sans-serif';
        });
    }, */
];

gulp.task('sass', function() {
    return gulp.src(input)
        .pipe(postcss(processors))
        .pipe(nano())
        .pipe(gulp.dest(output))
});




gulp.task('watch', function() {
  return gulp
    // Watch the input folder for change,

    // and run `sass` task when something happens
    .watch('pro/static/sass/*.sass', ['sass'])
    // When there is a change,
    // log a message in the console
    .on('change', function(event) {
      console.log('File ' + event.path + ' was ' + event.type + ', running tasks...');
      gulp.task('sass');
    });
});

gulp.task('default', ['sass']);

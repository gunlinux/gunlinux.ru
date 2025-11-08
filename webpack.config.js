const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const CopyWebpackPlugin = require('copy-webpack-plugin');

module.exports = {
  mode: 'production',
  context: path.resolve(__dirname),
  entry: './blog/static/src/styles.css',
  output: {
    path: path.resolve(__dirname, 'blog/static/dist'),
    filename: 'js/[name].js',
    clean: true,
  },
  module: {
    rules: [
      {
        test: /\.css$/,
        use: [
          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader',
            options: {
              url: false, // Disable CSS url() handling - we'll handle it separately
              import: true,
            }
          },
          'resolve-url-loader' // This helps resolve relative paths in CSS
        ]
      },
      {
        test: /\.(png|jpe?g|gif|svg|webp)$/i,
        type: 'asset/resource',
      },
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/i,
        type: 'asset/resource',
        generator: {
          filename: 'fonts/[name][ext]'
        }
      }
    ],
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'css/bundle.css',
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: path.resolve(__dirname, 'blog/static/fonts'),
          to: 'fonts',
        },
      ],
    }),
  ],
  optimization: {
    minimizer: [
      new CssMinimizerPlugin({
        test: /\.css$/g,
      })
    ],
  },
  devtool: 'source-map',
};

[![Maintainability](https://api.codeclimate.com/v1/badges/a096eddf8f8dbfdbd05b/maintainability)](https://codeclimate.com/github/gunlinux/gunlinux.ru/maintainability)
[![Python CI](https://github.com/gunlinux/gunlinux.ru/actions/workflows/main.yml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/main.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/a096eddf8f8dbfdbd05b/test_coverage)](https://codeclimate.com/github/gunlinux/gunlinux.ru/test_coverage)

## Install


```bash

$ cp config.example.sh config.sh

$ cp gunicorn.example.conf gunicorn.conf

$ python3 -m venv venv

$ source venv/bin/activate

$ pip install -r requirements.txt 

$ flask dbinit

```

## Configs

* config.sh

* gunicorn.conf

## Debug

```bash 
$ source env/bin/activate

$ source config.sh

$ flask run
```

## Deploy

```bash

$ source env/bin/activate

$ source config.sh

$ gunicorn -c gunicorn.conf "app:create_app()" 

```

## Contribution

Check for linter and tests

`$ make check`

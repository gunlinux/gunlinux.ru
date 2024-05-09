[![Maintainability](https://api.codeclimate.com/v1/badges/a096eddf8f8dbfdbd05b/maintainability)](https://codeclimate.com/github/gunlinux/gunlinux.ru/maintainability)
[![Python application](https://github.com/gunlinux/gunlinux.ru/actions/workflows/python-app.yml/badge.svg)](https://github.com/gunlinux/gunlinux.ru/actions/workflows/python-app.yml)
[![Test Coverage](https://api.codeclimate.com/v1/badges/a096eddf8f8dbfdbd05b/test_coverage)](https://codeclimate.com/github/gunlinux/gunlinux.ru/test_coverage)

## Install


```bash

$ cp gunicorn.example.conf gunicorn.conf

$ python3 -m venv venv

$ source venv/bin/activate

$ pip install -r requirements.txt 

$ flask dbinit

```

## Configs

* .env 

* gunicorn.conf

## Debug

```bash 
$ source venv/bin/activate

$ flask run --debug
```

## Deploy

```bash

$ source venv/bin/activate

$ gunicorn -c gunicorn.conf "app:create_app()" 

```

## Contribution

Check for linter and tests

`$ make check`

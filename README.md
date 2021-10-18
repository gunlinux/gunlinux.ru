[![Maintainability](https://api.codeclimate.com/v1/badges/a096eddf8f8dbfdbd05b/maintainability)](https://codeclimate.com/github/gunlinux/gunlinux.ru/maintainability)

## Install


```bash

$ cp config.example.sh config.sh

$ cp gunicorn.example.conf gunicorn.conf

$ mkdir -p pro/static/upload tmp 

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

$ gunicorn -c gunicorn.conf "manage:create_app()" 

```

## Contribution

Check for a PEP-0008 compliance:

`$ pep8 --ignore=E501,E128 pro`

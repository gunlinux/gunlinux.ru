#Install


```bash

cp config.example.sh config.sh

cp gunicorn.example.conf gunicorn.conf

mkdir -p pro/static/upload tmp pro/static/components


virtualenv venv

pip install -r requirements.txt 


npm install

gulp

bower install

python pro/static/components/highlight/tools/build.py


./manage.py dbinit

```

#Configs

* config.sh

* gunicorn.conf

#Debug

`$ source env/bin/activate`

`$ source config.sh`

`$ ./manage runserver -p PORT`

#Deploy

`$ source env/bin/activate`

`$ source config.sh`

`$ gunicorn -c gunicorn.conf manage:app `

#Contribution

Check for a PEP-0008 compliance:

`$ pep8 --ignore=E501,E128 pro`

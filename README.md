#Install


```bash
$ ./bootstrap.sh
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

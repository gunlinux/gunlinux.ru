VERSION = 0.0.5


all: check

lint:
	flake8 blog app.py

pytest:
	FLASK_ENV=testing FLASK_APP=pro pytest

test-coverage:
	( \
    . venv/bin/activate;\
		FLASK_ENV=testing FLASK_APP=blog pytest --cov=blog --cov-report xml\
	)

check: lint pytest

run:
	flask db upgrade
	flask run --host="0.0.0.0" --debug 

docker-build:
	docker build . --tag="gunlinux:$(VERSION)"

docker:
	-docker stop gunlinux
	-docker rm gunlinux
	docker run --rm -d --name gunlinux -v /home/loki/projects/gunlinux.ru/tmp:/app/tmp -p 5000:5000 gunlinux:$(VERSION)

docker-shell:
	docker run --rm -it --entrypoint="" gunlinux:$(VERSION) sh 

docker-test:
	docker build --target test-image -t gunlinux:$(VERSION)-test .

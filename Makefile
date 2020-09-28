.PHONY: server
server:
	cd src/ && gunicorn server:api -b 127.0.0.1:3001 --reload

.PHONY: webui
webui:
	cd src/web/ && yarn start

.PHONY: test
test:
	cd src/ && python -m pytest src/tests/

.PHONY: coverage
coverage:
	cd src/ && coverage run -m pytest tests/ && coverage html



	
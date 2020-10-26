.PHONY: server
server:
	cd src/ && gunicorn server:api -b 127.0.0.1:3001 --reload

.PHONY: webui
webui:
	cd src/web/ && yarn start

.PHONY: test
test:
	cd src/ && python -m pytest tests/

.PHONY: coverage
coverage:
	cd src/ && coverage run -m pytest tests/ && coverage html

.PHONY: docs
docs:
	pdoc --html src/lib --force

.PHONY: docs-server
docs-server:
	cd src/ && pdoc --html lib --http localhost:8080


	

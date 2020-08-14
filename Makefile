.PHONY: server
server:
	cd src/server/ && gunicorn main:api --reload

.PHONY: webui
webui:
	cd src/web/ && yarn start


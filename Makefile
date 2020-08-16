.PHONY: server
server:
	cd src/server/ && gunicorn main:api -b 127.0.0.1:3001 --reload

.PHONY: webui
webui:
	cd src/web/ && yarn start


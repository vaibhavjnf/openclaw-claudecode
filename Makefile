OPENCLAW_HOME ?= /opt/openclaw

.PHONY: venv deps start stop status restart install-services onboard doctor package

venv:
	python3 -m venv venv

deps:
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt

start:
	sudo systemctl start openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog

stop:
	sudo systemctl stop openclaw-watchdog openclaw-scheduler openclaw-bridge openclaw-runtime

restart:
	sudo systemctl restart openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog

status:
	sudo systemctl status openclaw-runtime openclaw-bridge openclaw-scheduler openclaw-watchdog --no-pager

install-services:
	./scripts/install_services.sh

onboard:
	$(OPENCLAW_HOME)/venv/bin/python -m app.onboarding_cli init

doctor:
	$(OPENCLAW_HOME)/venv/bin/python -m app.onboarding_cli doctor

package:
	./scripts/package_release.sh v0.1.0

.PHONY: all deps run

all: deps run

deps:
	mkdir -p venv
	python3 -m venv venv
	bash -c 'source venv/bin/activate && pip install -r requirements.txt'

run:
	bash -c 'source venv/bin/activate && python3 main.py'

.PHONY: install
install:
	pip install -r requirements.txt

.PHONY: test
test:
	python -m unittest src.tests.main_test

.PHONY: compile
compile:
	pyinstaller particle_converter.spec

.PHONY: clean_build
clean_build:
	rmdir /s /q build

.PHONY: build
build: compile clean_build

.PHONY: format
format:
	black . -l 100 -q
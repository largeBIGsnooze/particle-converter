install:
	pip install -r requirements.txt
test:
	pytest -v
compile:
	pyinstaller particle_converter.spec
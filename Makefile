setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -e .

install:
	pip install .

serve:
	. .venv/bin/activate && atenea serve

status:
	. .venv/bin/activate && atenea status

clean:
	rm -rf .venv

test:
	pytest -m "not nautilus and not performance and not skip"

test-all:
	pytest

test-changes:
	pytest --testmon -m "not nautilus and not performance and not skip"

# This Makefile defines several targets to run tests and other useful scripts.
#
# To execute a target, issues the command "make <target>". Requires GNU Make.
#
# test: run the typical tests of DESDEO, skipping tests marked to be skipped,
# 	and other tests that should be skipped for one reason or the other.
#
# test-all: run all the tests found in DESDEO, regardges of mark. This can be
# 	very slow.
#
# test-changes: Utilizes pytest-testmon to run only necessary tests given the
# 	changes in the code. This should be quick for checking that changes
# 	have not broke anything, and running the tests that are specific to the
# 	changes made.
#
# requirements-rtd: Exports the current requiremetns into a requirements.txt
# 	file and ouputs it into the docs folder. This file is needed when the DESDEO
# 	docs are built on readthedocs.org.
#
# requirements-pip: Like above, but creates a requirements.txt file for
# 	installing DESDEO utilizing pip/pipx.

test:
	pytest -m "not nautilus and not performance and not skip"

test-all:
	pytest

test-changes:
	pytest --testmon

requirements-rtd:
	poetry export --format requirements.txt --with=dev --extras "standard" --without-hashes --output docs/requirements.txt

requirements-pip:
	poetry export --format requirements.txt --with=dev --extras "standard viz api" --without-hashes --output ./requirements.txt

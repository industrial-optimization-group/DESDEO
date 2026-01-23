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
# test-failures: rerun the last falures only.
#
# fullstack: run the web-API and web-GUI for local develpment.

test:
	pytest -n auto -m "not nautilus and not performance and not skip and not fixme" --disable-warnings

test-all:
	pytest -n auto

test-changes:
	pytest -n auto --testmon

test-failures:
	pytest -n auto --lf

fullstack:
	./run_fullstack.sh

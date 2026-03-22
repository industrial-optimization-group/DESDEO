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

# Pytest conf (defined with `?=` can be overridden, e.g., `make test
# PYTST_MARK="-m slow"`)
PYTEST 		?= pytest -n auto
PYTEST_SKIP 	?= -m "not fixme"
PYTEST_OPTS 	?= --disable-warnings

# Other conf
TEST_API_PATH := ./desdeo/api/tests

test:
	$(PYTEST) $(PYTEST_SKIP) $(PYTEST_OPTS)

test-api:
	$(PYTEST) $(PYTEST_SKIP) $(PYTEST_OPTS) $(TEST_API_PATH)

test-all:
	$(PYTEST)

test-changes:
	$(PYTEST) --testmon

test-failures:
	$(PYTEST) --lf $(PYTEST_SKIP) $(PYTEST_OPTS)

fullstack:
	./run_fullstack.sh

docs-fast:
	mkdocs serve -f mkdocs.yml

docs-rtd:
	mkdocs serve -f mkdocs.rtd.yml

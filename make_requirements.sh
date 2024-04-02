#!/bin/bash

# Run this script to create a 'requirements.txt' file with poetry from the current dependencies of the project.
#
# The script takes one argument: either 'rtd' or 'pip'
#
# With 'rtd' argument, the script exports all the regular dependencies, the development dependencies, and the 'regular' version
# of polars. This version of the requirements.txt file is used when building the documentation on readthedocs.org.
#
# With the 'pip' argument, the script imports the same dependencies as above, but also invlude visualization and
# web-API dependencies. This version of the 'requirements.txt' file is adequate when one wishes to install the
# project utilizing pip/pipx.

if [ "$1" = "rtd" ]; then
	echo "Exporting readthedocs.org dependencies."
	echo "poetry export --format requirements.txt --with=dev --extras \"standard\" --without-hashes --output docs/requirements.txt"
	poetry export --format requirements.txt --with=dev --extras "standard" --without-hashes --output docs/requirements.txt
elif [ "$1" = "pip" ]; then
	echo "Exporting pip dependencies."
	echo "poetry export --format requirements.txt --with=dev --extras \"standard viz api\" --without-hashes --output ./requirements.txt"
	poetry export --format requirements.txt --with=dev --extras "standard viz api" --without-hashes --output ./requirements.txt
else
	echo "Please supply a single argument, either 'rtd' or 'pip'"
fi

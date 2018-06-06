#!/bin/bash

MYPYPATH=./stubs mypy desdeo examples tests --ignore-missing-imports

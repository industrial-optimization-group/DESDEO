# IMPORTANT NOTICE
This version of DESDEO is no longer supported. Information on the latest, and actively developed version of desdeo,
can be found [here](https://desdeo.misitano.xyz/software).

# DESDEO README #

<p align="center">
<a href="https://badge.fury.io/py/desdeo"><img src="https://badge.fury.io/py/desdeo.svg" alt="Available on PyPI" height="18"></a>
<a href="https://desdeo.readthedocs.io/en/latest/?badge=latest"><img alt="Documentation Status" src="https://readthedocs.org/projects/desdeo/badge/?version=latest"></a>
<a href="https://travis-ci.com/industrial-optimization-group/DESDEO"><img alt="Build Status" src="https://travis-ci.com/industrial-optimization-group/DESDEO.svg?branch=master"></a>
<a href="https://github.com/ambv/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

DESDEO is a free and open source Python-based framework for developing and
experimenting with interactive multiobjective optimization.

[Documentation is available.](https://desdeo.readthedocs.io/en/latest/)

[Background and publications available on the University of Jyväskylä Research Group in Industrial Optimization web pages.](https://desdeo.it.jyu.fi)

## Try in your browser ##

You can try a guided example problem in your browser: [choose how to deal with
river pollution using
NIMBUS](https://mybinder.org/v2/gh/industrial-optimization-group/desdeo-vis/master?filepath=desdeo_notebooks%2Fnimbus-river-pollution.ipynb).
You can also [browse the other
examples](https://mybinder.org/v2/gh/industrial-optimization-group/desdeo-vis/master?filepath=desdeo_notebooks).

## What is interactive multiobjective optimization? ##

There exist many methods to solve [multiobjective
optimization](https://en.wikipedia.org/wiki/Multi-objective_optimization)
problems. Methods which introduce some preference information into the solution
process are commonly known as multiple criteria decision making methods. When
using so called [interactive
methods](https://en.wikipedia.org/wiki/Multi-objective_optimization#Interactive_methods),
the decision maker (DM) takes an active part in an iterative solution process
by expressing preference information at several iterations. According to the
given preferences, the solution process is updated at each iteration and one or
several new solutions are generated. This iterative process continues until the
DM is sufficiently satisfied with one of the solutions found.

Many interactive methods have been proposed and they differ from each other
e.g. in the way preferences are expressed and how the preferences are utilized
when new solutions. The aim of the DESDEO is to implement aspects common for
different interactive methods, as well as provide framework for developing and
implementing new methods.

## Installation ##

### From conda-forge using Conda ###

This is the **recommended installation method**, especially for those who are
newer to Python. First download and install the [Anaconda Python
distribution](https://www.anaconda.com/download/).

Next, run the following commands in a terminal:

    conda config --add channels conda-forge
    conda install desdeo desdeo-vis

Note: if you prefer not to install the full Anaconda distribution, you can
install [miniconda](https://conda.io/miniconda.html) instead.

### From PyPI using pip ###

Assuming you have Pip and Python 3 installed, you can [install desdeo from
PyPI](https://pypi.org/project/desdeo/) by running the following command in
a terminal:

    pip install desdeo[vis]

This installs desdeo *and*
[desdeo-vis](https://github.com/industrial-optimization-group/desdeo-vis),
which you will also want in most cases.

## Getting started with example problems ##

To proceed with this section, you must [first install Jupyter
notebook](http://jupyter.org/install). If you're using Anaconda, you already
have it!

You can copy the example notebooks to the current directory by running:

    python -m desdeo_notebooks

You can then open them using Jupyter notebook by running:

    jupyter notebook

After trying out the examples, the next step is to [read the full
documentation.](https://desdeo.readthedocs.io/en/latest/)

## Development ##

### Set-up ###

You should install the git pre-commit hook so that code formatting is kept consistent automatically. This is configured using the pre-commit utility. See [the installation instructions](https://pre-commit.com/#install). In short, pre-commit hook can be installed as

    pip install --upgrade pre-commit
    pre-commit install

If you are using pipenv for development, you can install desdeo and its
dependencies after obtaining a git checkout like so:

    pipenv install -e .[docs,dev,vis]

### Tests ###

Tests use pytest. After installing pytest you can run:

    pytest tests

### Release process ###

1. Make a release commit in which the version is incremented in setup.py and an entry added to HISTORY.md

2. Make a git tag of this commit with `git tag v$VERSION`

3. Push -- including the tags with `git push --tags`

4. Upload to PyPI with `python setup.py sdist bdist_wheel` and `twine upload dist/*`

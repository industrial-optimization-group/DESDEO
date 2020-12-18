Contributing
============

We welcome anybody interested to contribute to the packages found in the DESDEO
framework. These contributions can be anything. Contributions do not have to necessarely be
ground-breaking. From fixing typos in the documentation to implementing new multiobjective
optimization methods, everything is welcome!

Guidelines and Conventions
--------------------------

The guidelines for code to be included in DESDEO should follow a few simple rules:

- Use spaces instead of tabs. Four spaces are used for indenting blocks when writing Python.
- Each line of code should not exceed 120 characters.
- Try to use type annotations for functions using Python's `type hints`_.
- For naming classes use ``CamelCase``, and for naming functions and methods use ``snake_case``.
- Do not use global or file level declarations. Try to always encapsulate your declarations inside classes.
- Classes should be designed with `duck typing`_ conventions in mind.


Docstring style
^^^^^^^^^^^^^^^

The docstring style used throughout the DESDEO framework follows the
style_ dictated by Google. Each function, class, and method should be documented.

Software development
--------------------

This sections contains some basic tips to get started in contributing to DESDEO.
We expect contributors to be proficient in at least the basics of Python.

Version control
^^^^^^^^^^^^^^^

DESDEO and all of its packages are under version control managed with ``git``.
It is highly suggested that anybody wanting to contribute to DESDEO should be first
familiar with the basic principles of ``git``. If terms such as `branching`, `committing`,
`merging`, `staging`, and `cloning` are alien to the reader, a brief review of the 
basics of ``git`` is in place before contributing to DESDEO can start. At least if the reader
wishes to make the experience as painless as possible...

For resources to learn git, `git's official documentation`_ is a very good place to start.
Many other resources exists on the web as well. We will not be listing them all. However, if a 
gamified approach is desired instead of having to read documentation, an in-browser tutorial
is available `here`__.

__ gitgame_

Project management
^^^^^^^^^^^^^^^^^^

The packages in DESDEO depend on many external Python packages. Sometimes a particular version
of an external package is needed, which does not match the current version of the same
external package on the computer's system DESDEO is going to be developed on. This can lead
to many dependency problems. It is therefore 
highly recommended to
use `virtual environments` when developing DESDEO to separate the packages needed by DESDEO from the
packages present on the system's level.

Poetry_ is a modern and powerful tool to manage Python package dependencies and for building Python
packages. ``Poetry`` is used throughout the DESDEO framework to manage and build its packages. While ``Poetry``
is `not` a tool for managing virtual environments, it nonetheless offers very simple commands to trivialize
the task. Anybody contributing code to DESDEO should be familiar with ``Poetry``.

Sometimes the Python version installed on a system is not compatible with the Python version required
in DESDEO (3.7.x). In this case, it is recommended to use an external tool, such as `pyenv`_, to facilitate
the task of switching from one Python version to an other.

Example on how to get started
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the reader is familiar with ``git`` and ``Poetry``, starting to develop DESDEO should proceed
relatively painlessly. Suppose we have a feature X which we wish to implement in DESDEO's ``desdeo-mcdm``
package. It is higly recommended to first ``fork`` the ``desdeo-package`` on GitHub on a separate repository
and then cloning that repository. When doing so, use the forked repository's URL instead of the 
main repotiry's URL when cloning the project using ``git``. Make sure to also setup your forked repository
to be configured__ properly to be able to synchronize it later with the upstream repository.

__ upstream_

We proceed by cloning the repository on our local machine:

::

    $ git clone https://github.com/industrial-optimization-group/desdeo-mcdm

Next, we should switch to the newly created directory:

::

    $ cd desdeo-mcdm

We can now easily use ``Poetry`` to first create a Python virtual environment by issuing Poetry's ``shell``-
command and then use Poetry's ``install``-command to install the ``desdeo-mcdm`` package locally in our
newly created virtual environment:

::

    $ poetry shell
    $ poetry install

The ``install`` command might take a while. Once that is done, ``desdeo-mcdm`` should now be installed
in our virtual environment and be fully usable in it.

To start implemeting our new feature X, we should start by making a new ``branch`` and switching to it
using ``git``. This ensures that the changes we make are relative to ``desdeo-mcdm``'s master branch,
at least the version of it which was available at the time of cloning it. Let us create a new branch now
for our featrue X named ``feature-X``:

::
    
    $ git branch feature-X
    $ git checkout feature-X

We are now ready to start implementing our changes to the package. Frequent ``committing`` is
encouraged.

Suppose that we are now done impelenting our feature X. We now wish it was included to the master
branch of ``desdeo-mcdm``. To do so, we need to first switch back to the master branch

::

    $ git checkout master

Then we need to make sure the master branch is up-to-date with the upstream version of the branch
by issuing a pull. (If a ``forked`` repository is being used, the repository must first be 
synchronized__ with the upstream repository.) 

__ sync_

::

    $ git pull

Lastly, we will have to merge our ``feature-X`` branch containing our changes with the master branch

::

    $ git merge feature-X
 
If all went well, we should now be ready to issue a ``pull request``. However, if any conflicts emerge during the
merging of the branches, these conflicts should be addressed before making a ``pull request``. When the merge
is free of conflicts, a ``pull request`` can be issued on GitHub or from the terminal. A maintainer of the repository
will then review your changes and either accept them into the upstream or request revisions to be made before
the new code can be accepted.

Documentation
-------------

Introduction
^^^^^^^^^^^^

To build the documentation for the DESDEO framework and its various modules,
Sphinx_ is used. Sphinx offers excellent utilities for automatically
generating API documentation based on existing documentation located in
source code, and for adding custom content.

Automatically generated documentation and custom content is specified as
reStructuredText_. ReStructuredText is a markup language
just like Markdown or html, but offers the possibility to extend the language
for specific domains. The file extention ``.rst`` is used for files containing
reStructuredText content. Sphinx can then be used to generate documentation
in various formats, such as html and pdf, based on content provided as
reStructuredText.

Resources to get started with Sphinx
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The official documentation offers a good guide_ for getting started. It is
advised to read through the guide before contributing to the documentation.
After reading the guide, the reader is encouraged to check out the contents
of the source file used to generate the current page. The source file can be
accessed by going to the top of this page and following the `Edit on GitHub`-link.
It is also advised to check out the content of the `docs` file found in the main 
repository_ of the DESDEO framework.
After checking the source file used to generate this page, the user should be
familiar with at least basic sectioning, hyperlinks, code blocks, note blocks,
and lists.

Other useful resources include:

 - Official_ documentation for reStructuredText.
 - ReStructuredText syntax cheatsheet_.
 - A conference talk_ about Sphinx given during PyCon 2018. (YouTube has also
   many other videos on Sphinx as well)
 - A more through tutorial_ written by the matplotlib developers on how to
   achieve a documentation similar to theirs.

Extensions
^^^^^^^^^^

In the DESDEO framework, some Sphinx extensions are used to faciliate automatic documentation generation.
At least the following extensions are used:

Included in Sphinx:

- Sphinx.ext.autodoc_ for automatically generating documentation based on docstrings.
- Sphinx.ext.napoleon_ for parsing the Google styled docstrings.
- Sphinx.ext.viewcode_ for accessing the documented source code from the documentation itself.

User provided extensions:

- Sphinx-autodoc-typehints_ for better type hints.
- automodapi_ for even better automatic API documentation generation.
- nbsphinx_ for converting Python notebooks into rst pages.

Building and testing the documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If Sphinx has been setup following the official quick guide_, the
documentation can be build by running the commnad
::

   make html

in the root direcotry containing the documentation. This will produce
documentation in an html format residing in the ``_build`` folder in the
documentation's root directory. To view the documentation built, use any web
browser. For example, with Firefox, this is achieved by issuing the command
::

  firefox _build/html/index.html

.. note::

   The directory ``_build`` generated by ``sphinx-quickstart`` should not be
   under version control.

Deployment
^^^^^^^^^^

.. note::

   Most of the content in this section is relevant only when setting up the
   documentation for the first time for a module.

The documentation for each of the DESDEO modules is hosted on
readthedocs.org_. For the documentation to be build correctly, a YAML
congiguration file named ``.readthedocs.yml`` should be present in the root
directory of the project (not the root directory of the documentation!) A
minimal configarion file could look like this:
::

   # Required
   version: 2

   # Build documentation in the docs/ directory with Sphinx
   Sphinx:
   configuration: docs/conf.py

   # Optionally set the version of Python and requirements required to build your docs
   python:
   version: 3.7
   install:
       - requirements: docs/requirements.txt

Especially the locations of the configuration files ``docs/conf.py`` and
``docs/requirements.txt`` are important to enable readthedocs to correctly
build the documentation.

.. note::

   The requirements file should contain the requirements for **building the
   documentation**. It does not necessarely need to contain all the
   requirements of the module the documentation is being build for.
   However, for building the documentation for some of the modules, like
   ``desdeo-mcdm`` for example, the whole module needs to be installed for
   Sphinx to be able to compile the documentation. In that case, having the
   project's whole requirements in the requirements file pointed at in
   ``.readthedocs.yml`` is justified.

If a ``requirements.txt`` if required, but `poetry` is used to manage
dependencies, then the command
::

   poetry export --dev -f requirements.txt > requirements.txt

can be used to generate a requirements file.

For more configuration options, `go here <https://docs.readthedocs.io/en/stable/config-file/v2.html>`_.
The whole documentation for readthedocs can be found `here <https://docs.readthedocs.io/en/stable/index.html>`_.
 
Caveats
^^^^^^^

Some common caveats with Sphinx:

 - The intendation Sphinx expects in the reStructuredText files is **three spaces**
   to specify the scope of the `options` and `content` of a
   `directive`. Options should follow the directive immediately on the
   following line, one option per line, and the content should be separated by
   one blank line from the options (if no options are provided, the blank line
   should be between the directive and the contents). For example, the following is correct:
   ::

      .. toctree::
         :maxdepht: 2
   
         content
         morecontent
    
   The following, however, is **incorrect**:
   ::

      .. toctree::
         :maxdepht: 2
         content
         morecontent

 - If the contents of an item in a list span more than one line, the lines
   following the first line should have their indentation starting at the same
   level as the content on the first line. I.e.:
   ::

      - This is the first line
        this is the second line
        this is the third line
        notice the indentation



.. _Sphinx: https://www.Sphinx-doc.org/en/master/
.. _reStructuredText: https://docutils.sourceforge.io/rst.html
.. _guide: https://www.Sphinx-doc.org/en/master/usage/quickstart.html
.. _repository: https://github.com/industrial-optimization-group/DESDEO/tree/migrate-to-new/docs
.. _cheatsheet: https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst
.. _Official: https://docutils.sourceforge.io/rst.html
.. _talk: https://www.youtube.com/watch?v=0ROZRNZkPS8
.. _style: https://www.Sphinx-doc.org/en/master/usage/extensions/example_google.html#example-google
.. _Sphinx.ext.autodoc: https://www.Sphinx-doc.org/en/master/usage/extensions/autodoc.html
.. _Sphinx.ext.napoleon: https://www.Sphinx-doc.org/en/master/usage/extensions/napoleon.html
.. _Sphinx-autodoc-typehints: https://github.com/agronholm/Sphinx-autodoc-typehints
.. _Sphinx.ext.viewcode: https://www.Sphinx-doc.org/en/master/usage/extensions/viewcode.html
.. _automodapi: https://Sphinx-automodapi.readthedocs.io/en/latest/index.html
.. _readthedocs.org: https://www.readthedocs.org
.. _tutorial: https://matplotlib.org/sampledoc/
.. _nbsphinx: https://nbsphinx.readthedocs.io/en/0.7.1/
.. _type hints: https://docs.python.org/3/library/typing.html
.. _duck typing: https://en.wikipedia.org/wiki/Duck_typing
.. _git's official documentation: https://git-scm.com/doc
.. _gitgame: https://learngitbranching.js.org/
.. _Poetry: https://python-poetry.org/
.. _pyenv: https://github.com/pyenv/pyenv
.. _sync: https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/syncing-a-fork
.. _upstream: https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork

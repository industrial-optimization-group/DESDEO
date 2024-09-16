---
hide:
- navigation
---

# Contributing to DESDEO

In this tutorial, step-by-step instructions are given on how to begin
contributing to DESDEO, and what one should consider when developing DESDEO,
such as coding practices and typical workflows. We first cover the required
software to be installed in the section [Installing required
software](#installing-required-software).  Then, we discuss how to download
DESDEO's source code and setup a virtual environment in the section [Setting up
a virtual environment and installing
DESDEO](#setting-up-a-virtual-environment-and-installing-desdeo).  A typical Git
workflow is then described in the section [Typical Git workflow for contributing
to DESDEO](#typical-git-workflow-for-contributing-to-desdeo).  Development
practices and utilized tools are discussed in the section [Development
practices](#development-practices), and how to integrate some of these into an
integrated development environment are discussed in the section [Integrated
development environments](#integrated-development-environments).
The main points of this tutorial are then summarized in
the section [Summary](#summary). Lastly, conclusions and potential
next steps in contributing to DESDEO are outlined in the
section [Conclusions, where to go next, and our Discord
server](#conclusions-where-to-go-next-and-our-discord-server).

## Installing required software

In this section, instructions are provided for installing the software
required to start contributing to DESDEO. Instructions
have been provided for the most common operating systems. We have
assumed a command line environment to be available on each operating system
(indicated by the `$` symbol).
Applications with a graphical user interface may also be utilized, but will not
be covered in this tutorial. However, most of the presented content
should be applicable even outside a command line environment. Instructions
for each platform can be found in the following sections:

- [Windows platforms](#windows)
- [Linux-based platforms](#linux)
- [macOS platforms](#macos)

Lastly, we also assume that we have a GitHub account setup. If not,
we can visit [GitHub](https://github.com/) to setup a new account.

### Windows

Here, we assume to be operating in a __powershell__ environment. The first step
is to install Python on the system, unless it is already installed. To check
which version of Python are supported, check the section
[Requirements](../index.md#installation-instructions). If utilizing the `.exe`
installer for installing Python, we should ensure that the installer also sets the
necessary `Path` environment variables. There should be a check-box for this
during the installation. Python binaries for Windows platforms can be found [on
the Python website](https://www.python.org/downloads/).

!!! Note "Ensuring Path variables are updated"
    To ensure changes in `Path` variables are in effect, it is advisable to logout
    of the current Windows session, and then log back in.

To check that Python has been installed correctly on you system, we can open powershell
and run the command

```shell
$ python --version
```

this should report the version of the currently installed Python interpreter.

Next, we need to install _Git_ for version control and _poetry_ for managing
packages and the virtual environment for developing DESDEO. To facilitate this,
it is recommended to install [scoop](https://scoop.sh/). Installation
instructions are provided on scoop's webpage. Using scoop is optional, but we
will assume that it has been installed for the remainder of this section.

To install poetry, we will follow the [recommended way and use _pipx_](https://python-poetry.org/docs/#installation).
To install pipx, in a powershell, we run [the commands](https://pipx.pypa.io/stable/installation/)

```shell
$ scoop install pipx
$ pipx ensurepath
```

After successfully installing pipx, installing poetry is as simple as

```shell
$ pipx install poetry
```

It might be a good idea to run

```shell
$ pipx ensurepath
```

once more after installing poetry. After this, we should log out and back into a Windows session.

Finally, we can install Git utilizing scoop

```bash
$ scoop install git
```

We should now have all the necessary tools to be able to start developing and contributing to DESDEO
on a Windows operating system.

### Linux

Git and Python are most probably already available on our system. If not, we can
use our systems's package manager to install both. We can follow the instruction on
[poetry's webpage](https://python-poetry.org/docs/#installation) to install
poetry. After this, we should be set to begin developing on Linux-based systems.

### macOS

(this section should be written by somebody who has access to a Mac.)

Homebrew something something. I have no idea. Just follow and adapt
the instructions for [Linux-based systems](#linux).

## Setting up a virtual environment and installing DESDEO

In this section, we will download DESDEO, and install it in a virtual
environment. It is highly recommended to install DESDEO into such an
environment when developing it to ensure that there is no clash between
system-level Python packages and the packages utilized by DESDEO. Despite the
fancy name, a virtual environment is nothing more than a set of [environment
variables](https://en.wikipedia.org/wiki/Environment_variable) that point to a
specific, usually isolated, Python installation and its packages.

### Downloading the source code of DESDEO

Before we proceed to setting up our virtual environment,
we will have to download (clone) the source code of DESDEO. To do so,
first, we navigate to a directory where we wish to download the
source code to. For example:

```bash
$ cd ~/workspace/
```

where the tilde `~` is a shorthand for our `$HOME` directory. We
may also create such a directory in our current working
directory, and switch to it, with the commands

```bash
$ mkdir workspace
$ cd workspace
```

We can then proceed to download the source code for DESDEO.
It is highly recommended to _fork_ the repository first.
Forking the repository is described in the section
[Forking the DESDEO repository](#forking-the-desdeo-repository).
Assuming our fork has the url _https://github.com/ourusername/DESDEO_,
we can clone the repository on our machine with the command:

```bash
$ git clone git@github.com:ourusername/DESDEO.git
```

We should remember to replace _ourusername_ with our actual GitHub username.

<span id="note:ssh"></span> 
!!! Note "On SSH and keys"
    It is recommended to utilize the SSH (secure shell) url when
    cloning DESDEO. This, however, requires that an SSH key-pairs has been
    generated, and
    that a public key
    has been added to one's GitHub user account.
    For instructions on how to setup and SSH key,
    see [Adding a new SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account?platform=windows).

Lastly, we should change to the newly cloned directory with the source code

```bash
$ cd DESDEO
```

!!! Note "Ensuring we work on the correct branch"
    For now, we should also make sure to be checked in the `desdeo2`
    branch of the project with the command

    ```shell
    $ git checkout desdeo2
    ```

    pulling changes on the branch might also be necessary

    ```shell
    $ git pull origin desdeo2
    ```

We are now in a position to setup our virtual environment.

### Setting up a virtual environment

There are many ways to setup a virtual environment. Here, we will
be utilizing poetry (c.f., section [Required software](#required-software))
for the task. First, we should ensure
that we are utilizing a correct version of Python

```bash
$ python --version
```

This prints the version of the current
Python interpreter installed on our system.
If the version is correct, then we can proceed. If not,
we should point poetry to the Python binary of the version we wish to utilize,
e.g.,

```shell
$ poetry env use /usr/bin/python
```

!!! Note "Managing multiple Python versions"
    For managing multiple Python versions, a tool, such
    as [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file)
    is recommended.

Before proceeding, it is useful to set the poetry configuration
`virtualenvs.in-project` to `true`. This will ensure that our
virtual environment will be created in the `.venv/` directory
in our project's directory. To configure poetry to do this,
we run

```shell
$ poetry config virtualenvs.in-project true
```

Assuming we are still in the DESDEO's project directory
(e.g., `~/workspace/DESDEO`), we can now create and activate
a virtual environment with the command

```shell
$ poetry shell
```

This should create a virtual environment and activate it. To install
DESDEO and download all of its software (development) dependencies to the
environment, we can now run

<span id="bash:poetry_install_dev"></span>
```shell
$ poetry install -E standard -E api --group=dev # (1)!
```

1.  The option `-E standard` installs the regular version of polars. If we are on an
    older CPU, we might want to install the legacy version with the option `-E legacy`.
    The option `-E api` install the packages required to run DESDEO's web API. Having the
    web API dependencies is beneficial when developing the API, database, or both,
    aspects found in DESDEO.
    The `-E` flag is used to indicate to poetry extra dependencies
    we wish to install. Likewise, the `--group=dev`
    tells poetry that we want to install the dependencies listed as development
    dependencies.

This might take a while. After poetry is done installing, and there
are no error messages, we should be able to run

```shell
$ pytest
```

which runs all the tests present in DESDEO. Not all of them
will be passing, but a majority of them should. This should indicate
to us now that DESDEO has been correctly installed, and our
virtual environment is now setup correctly. Pytest and tests
are discussed in more detail in the section [Testing](#testing).

To exit the virtual environment, simply run

```bash
$ exit
```

and to re-activate it,

```bash
$ poetry shell
```

Activating the environment requires that our current working
directory is set to be the DESDEO directory with the source code.
The command `poetry shell` will not re-create the virtual environment
if it already exists, only reactivate it.

## Typical Git workflow for contributing to DESDEO

This section outlines the standard process for contributing to DESDEO using Git
and GitHub. This workflow assumes that we have a GitHub account. If this is not
the case, we should create one at [GitHub](https://github.com/) first. The workflow
involves forking the DESDEO repository, cloning our fork of the repository to
our local machine, making changes, and then submitting these changes as a pull
request.

### Forking the DESDEO repository

A fork is a copy of a repository that we manage and that is a completely
separate entity from the original repository, which is often referred to as the
_upstream_. Forking a repository allows us to freely experiment with changes
without affecting the original project.

To fork a repository:

- Visit the [DESDEO GitHub](https://github.com/industrial-optimization-group/DESDEO) repository.
- In the top-right corner of the page, click the __Fork__ button.
- This action creates a copy of the DESDEO repository in your GitHub account.
- To ensure we are working on a fork, the url to our repository should be of the form _https://github.com/ourusername/DESDEO_. We might
have a different name for the forked repository if we chose one when making the fork.

### Cloning the fork

To work on our fork on a local machine, we need to clone it first. Cloning
creates a local copy of our fork. In practice, it downloads the repository
and its history to our machine.

To clone our fork:

- On GitHub, we navigate to our fork of the DESDEO repository.
- Above the file list, there should be a green button labeled "Code". Clicking the button should
reveal a smaller window. We should select the "SSH" tab and copy the given url.
- In a terminal, we then navigate to where we want to place the local repository.
- Then we clone the fork using the command:

```bash
$ cd ~/workspace # (1)!
$ git clone <URL-of-the-fork>
$ cd DESDEO
```

1.  _workspace_ is just a directory where we want to store the directory
    containing our fork. this is just an example, we can use any directory we want.

It is highly recommended to use the SSH url. This requires setting up a
SSH key pair on our local machine and uploading the public key to GitHub.
[This info box](#note:ssh) gives further details on the process.

### Setting the upstream repository

It is beneficial that we periodically check the upstream, e.g., the original
repository of DESDEO for changes, and update our fork. This ensures
that our local version of DESDEO is up to date with new changes, and
allows us to fix any potential conflicts between the two versions as they
emerge.

Assuming we are in the DESDEO directory with the contents of
our cloned fork, we can set the upstream with the following command:

```bash
$ cd DESDEO
$ git remote add upstream git@github.com:industrial-optimization-group/DESDEO.git
```

The upstream should now be successfully set.

### Creating a new branch

Before making changes to DESDEO's code, we should create a new branch on our
local fork of DESDEO. It is a good practice to name the branch something
relevant to the changes we plan to make.

!!! Warning "DESDEO 2.0 pre-release era"
    Before making a branch on our fork, we should make sure
    we are on the `desdeo2` branch of the repository:

    ```bash
    $ git checkout desdeo2
    $ git status # (1)!
    ```
    
    1. The output should be "On branch desdeo2... etc."

Before making a branch, we should update the `desdeo2` branch first
(once DESDEO 2.0 is released, this would be the `main` branch instead). We
issue the commands

```bash
$ git pull upstream desdeo2 # (1)!
$ git log # (2)!
```

1.  We should make sure we are on the `desdeo2` branch first!
2.  This will print a log of the most recent changes to the branch.
    We should see fairly recent changes here, if not, we should double
    check we are on the correct branch. To exit the log, we can press 'q'.    

We are now in a position to create our own branch, which branches from
`desdeo2`. To create a branch with the name `feature-x` and switch to it,
we issue the command

```bash
$ git branch feature-x
$ git checkout feature-x
```

We have now created a new branch and switched to it.

### Making changes

We are finally in a position where we can begin making our changes
to DESDEO and start implementing our new feature. It is advisable to
check the section [Development practices](#development-practices)
to learn about some of the practicalities to consider when developing
DESDEO.

Assuming we have made changes, we can _stage_ the changes using the command

```bash
$ git add . # (1)!
```

1.  This assumed we are in the root directory of the project, i.e., the
    directory containing our fork. Otherwise we can stage all files
    with changes with the command `git add -A`.

!!! Note "What files to commit?"
    In general, we should commit only source files, not
    compiled files. This means that no Python byte-code
    should ever be committed (i.e., `__pycache__` directories and their
    contents). Luckily, rules for Git to ignore the most common
    types of files that should not be committed have been defined in the
    `.gitignore` file defined at the root level of the DESDEO project.

We can always check which files are staged, and which are not, with the command

```bash
$ git status
```

!!! Note "On Git status"
    The command `git status` will 99% of the time tell us exactly
    what we should in case of errors related to Git. Carefully reading the
    output of the command is important and can save us a lot of troubles.

Once we have staged all our changes, we can add then to the branch by
_committing_ them

```bash
$ git commit # (1)!
```

1.  This should open our system's default text editor. To configure it,
    we can change the option, we can issue the command

    ```bash
    $ git config --global core.editor "editor_name"
    ```

    where editor name can be, for instance, "nano", "vim", "code", etc.

Alternatively, to avoid opening a text editor for giving our commit message,
we can also issue the command

```bash
$ git commit -m "Our commit message"
```

!!! Note "On commit messages"
    In a good commit message, we should give enough information for another
    developer to understand what was changed. Usually the first line
    of the commit should be a short summary, e.g., "Added a few new tests.",
    which is then followed (separated by a blank new line) with more details,
    e.g., "A test was dded to test the correct functioning of the NIMBUS method.
    A similar test was also added for the E-NAUTILUS methods. Both of these 
    tests should be passing." __There is no such thing as a "too long"
    commit message!__

We can make as many commits as we like. We do not need to have anything "ready"
when making a commit. We should not be afraid of committing _too often_; there
is no such thing!
Actually, the more commits the better. Committing can be understood as "saving"
our changes to the version control system, which also creates a "checkpoint" we
can roll our project back to at any point in time. The changes in the commits
are still only local, i.e., on our own local machine. To integrate them into our fork
on GitHub, or the DESDEO upstream, we would have to push them first.

### Pushing changes to our fork

After committing our changes, we can push them to our fork on GitHub:

```bash
$ git push origin feature-x # (1)!
```

1.  `origin` refers to the GitHub repository with our fork, it points
    to the repository we originally cloned from, which in this case is
    our fork.
    `feature-x` is the branch name we have been working on and committing to.
    To check where `origin` point to, we can issue the command
    `git remote -v`, which lists all the remotes and their urls.

This does not make any changes to the original upstream repository of
DESDEO. For our changes to be integrated in the upstream, we
have to make a pull request.

### Creating a pull request

A pull request is a GitHub feature where we can notify the maintainers of an
upstream repository, usually the one we originally forked (in this case DESDEO),
that we have made changes that we would like to integrate into the upstream. When
making a pull request, it is assumed that a feature, or features, to be added
are complete and not work in progress. Once a pull request has been made, the
maintainers of DESDEO will be notified. They will then check the changes, and
either accept them as they are and pull them into the upstream, or they can give
feedback on what needs to be changed for the pull request to be accepted.
The more commits in a pull request, the easier it is for a maintainer to review
the changes.

In practice, making a pull request consists of the following steps:

1. Go to the fork on GitHub.
2. Switch to the branch with our new feature, e.g., `feature-x`.
3. There should be a green "Pull request" button next to our branch. Click it.
4. We can then review the changes in the pull request against the upstream. We can also
provide additional information about the contents of the pull request.
5. Once we are done creating the pull request and describing it, we can then create it.

We may still continue working on our local branch and pushing commits to our fork.
The pull request can always be updated with the new changes in GitHub.

### Keeping your fork up to date

While working on our fork, it is a good practice to keep it up to
date with the upstream. This is important because, for example,
a pull request from another contributor might have been accepted into the
mainstream while we have been working on our local fork. Some of these changes might also
affect the code we have been working on, and we should make sure our changes are
based on the latest code in the upstream. This can avoid overly complicated 
merge conflicts in the repository when making a pull request.

The following commands can be used to update our fork (remember to commit any changes to your
own branch (e.g., `feature-x`) first!):

```bash
$ git fetch upstream # (1)!
$ git checkout desdeo2 # (2)!
$ git merge upstream/desdeo2 # (3)!
$ git push origin desdeo2 # (4)!
```

1.  The `fetch` command downloads all the changes made to the upstream but does not apply them, unlike the `pull` command would.
2.  Remember, this is the main branch of the upstream, which we forked and which we want to keep up with.
3.  This adds all the changes made in the upstream to our local fork. The `desdeo2` branch of our __local__ fork is now up to date.
4.  Lastly, we want to update the fork in our repository, or remote as well, __which is on GitHub__. This command pushes the updated
    version of the main working branch to our fork on GitHub as well.

If we have work in progress in our feature branch (e.g., `feature-x`), we can then change back to it and attempt to merge the most recent
changes in the upstream with our work:

```bash
$ git checkout feature-x  # (1)!
$ git merge desdeo2 # (2)!
```

1.  We are now in our feature branch again.
2.  This will attempt to merge all the changes in the upstream with our feature branch.

If we have made changes in our code to parts of the code that have also been
changed in the upstream, then we would have a _merge conflict_. The output of
the command `git status` should give us plenty of information on how to proceed
to resolve the conflict.
For further instructions on how to resolve merge conflicts, see the section
[Further resources](#further-resources).

### Further resources

Git is a very powerful tool for version control. What we have covered in this tutorial
thus far barely scratches the surface of what Git is capable of, and how to use it.
The interested reader is encouraged to checkout further resources, such as the official
[documentation for Git](https://git-scm.com/doc) and the references therein.

The process of learning Git has also been gamified by many. Two popular examples
for learning a Git are:

- [Learn Git Branching](https://learngitbranching.js.org/), and
- [Oh My Git!](https://ohmygit.org/).

Combined with the official documentation, these games can supplement one's
learning journey on coming a proficient Git user.

Lastly, there is a seminar talk by Giovanni Misitano, where the Git workflow
discussed in this section is presented in more detail. While the talk
references an older version of DESDEO, the contents relevant to Git
and GitHub are still very much relevant. A recording of Giovanni's talk
can be found on [YouTube](https://www.youtube.com/watch?v=JCZRBx55KBQ).

## Development practices

There are at least three important aspects we should keep in mind
when it comes to the development practices of DESDEO:

- First, we should adhere to common coding practices so that the codebase
of DESDEO can be kept coherent and similar across its different modules and
files.
- Second, we should ensure to test as much as possible the code
have written, ensuring that it works as expected and that we do not
break any existing code in DESDEO with out additions.
- Three, we should document our additions carefully to ensure
their usability and reusability, and to support other users in utilizing
our additions.

These topics are discussed in their respective sections 
[Code style, linting](#code-style-linting); [Typechecking](#typechecking);
[Testing](#testing); and [Documenting](#documenting).

### Code style and linting

The practices we should adhere to while writing code, such
as line length, quotation style, and such, are determined by
the _code style_. Luckily, we do not have to remember
each detail ourselves each time we type a new line of code,
instead, we can rely on _linters_. Linters are external tools that,
once run, will check the code we have written to ensure
it follows the code style we have chosen, and also that
our code is syntactically valid. If not, the linter will
alert us of any discrepancies. Instead of manually correcting
each discrepancy, we can also utilize _code formatters_, which
can be combined with a linter to automatically format our
code such that it follows the established code style.

In DESDEO, we have chosen to utilize [Ruff](https://docs.astral.sh/ruff/) which
is _both_ a linter and code formatter. If we have installed DESDEO utilizing
poetry, including its development dependencies (c.f., [this
example](#bash:poetry_install_dev)), then Ruff should be installed on our
machines.

To run Ruff on a file and check for any errors or discrepancies, we
can issue the command

```bash
$ ruff check desdeo/problem/schema.py
```

The output could then look like

```bash
desdeo/problem/schema.py:31:5: D417 Missing argument description in the docstring for `parse_infix_to_func`: `cls`
desdeo/problem/schema.py:394:7: TD002 Missing author in TODO; try: `# TODO(<author_name>): ...` or `# TODO @<author_name>: ...`
desdeo/problem/schema.py:394:7: TD003 Missing issue link on the line following this TODO
desdeo/problem/schema.py:394:7: FIX002 Line contains TODO, consider resolving the issue
Found 4 errors. # (1)!
```

1.  In case Ruff finds no errors, its output will read `All checks passed!`

We can also ask Ruff to try and fix the found errors in the same file with the command

```bash
$ ruff check desdeo/problem/schema.py --fix
```

This will automatically fix the errors, if possible. If not, we will have to
manually address them. Luckily, Ruff's output is very rich, and the fix is often
easy to implement.

The code style itself utilized in DESDEO has been configured in the
project's configuration file `pyproject.toml`, which is found in the root
directory of the project. Ruff related options are found in sections
starting with `[tool.ruff...]`.

For more information on Ruff, the reader is encouraged to check [its official
documentation](https://docs.astral.sh/ruff/).

### Typechecking

While Python is not a typed language, it still offers the options
to provide _typehints_ in function and variable declarations. For example

```python
def divide_numbers(nominator: int | float, denominator: int | float) -> float:
    return nominator / denominator
```

In the above example, the types following each function argument (after the colon),
denote the type of the arguments, in this case, either an `int` or a `float`. 
The type after the arrow `->` in the function definition defines the
return type of the function, in this a case `float`.

Python itself does not enforce the types of variables or functions based on the
typehints, but rather, they can help users and developers to reason about the code.
Moreover, tools have been implemented to do static type checking for
Python code enhanced with typehints. One such tool is _mypy_, and it is
utilized in DESDEO as well.

As was the case
with Ruff, mypy should be already installed on our machine if we installed
desdeo with its [development dependencies](#bash:poetry_install_dev). To check
a file with mypy, we can run the command

```bash
$ mypy desdeo/problem/utils.py 
```

As an example, the output of `mypy` could look like

```bash
desdeo/problem/utils.py:26: error: Argument 1 to "len" has incompatible type "float"; expected "Sized"  [arg-type]
desdeo/problem/utils.py:28: error: Value of type "float" is not indexable  [index]
desdeo/problem/utils.py:58: error: Value expression in dictionary comprehension has incompatible type "float | None"; expected type "float"  [misc]
desdeo/problem/utils.py:70: error: Value expression in dictionary comprehension has incompatible type "float | None"; expected type "float"  [misc]
Found 4 errors in 1 file (checked 1 source file)
```

We would then have to manually fix the typehints highlighted by mypy.

It is important to keep in mind that mypy does not guarantee any form or
type of type safety. It may enhance it, but it relies heavily on the typehints
provided by users, which may be wrong or only partially correct. Moreover,
mypy does not remove the need for runtime type checks. Nevertheless,
mypy is a useful tool to check the consistency and correctness of user
provided typehints in DESDEO, which can improve the overall quality of the code.

For more information on mypy, the reader is encouraged to check [its official
documentation](https://mypy.readthedocs.io/en/stable/index.html).

### Testing

Another way to ensure the code quality in DESDEO is _testing_. 
DESDEO utilizes _pytest_ as its testing library, which should
come installed with the project if we installed DESDEO with its
[development dependencies](#bash:poetry_install_dev).

Tests should be located in the `tests/` directory found at the root of the
directory. Tests are written inside `.py` files with the `test_` prefix, e.g.,
`test_feature.py`. Tests themselves should be defined as test cases, each in its
own Python function with its name starting with the prefix `test_`, e.g., `def
test_feature():`.  It is important that these naming conventions are followed
because pytest relies on them during test discovery (i.e., when it tries to
figure out where tests have been defined).

As an example of a test case, let us consider the following

```python
@pytest.mark.feature  # (1)!
def test_feature_correct_output():
    output: int = double(5) # (2)!
    expected = 10

    assert output == expected # (3)!
```

1.  To add marks, we must remember to import pytest first (`import pytest`).
2.  We can imagine we are testing a feature that doubles a given integer and
    returns an integer corresponding to the doubled value of the argument. This function
    has been imported, e.g., `from feature_file import double`.
3.  An `assert` statement will raise an `AssertionError` whenever the expression following
    it resolves to be `False`.

!!! Note "What should a test test?"
    Because DESDEO is currently mainly developed my researchers, we do not
    have the time or resources to implement tests in a systematic fashion.
    I.e., unit tests for every single feature, and then more comprehensive
    tests. Instead, we have taken a code-coverage approach, where
    out goal is to write at least _some_ tests for all the code
    found in the code base that visits each line in the code at least once.
    It is better to write a test that at least checks that a piece of code
    executes without error with some input. Even better if the output can be
    checked to be _logically correct_. And even even better,
    if multiple input and outputs of a piece of code and be checked.

    A bare minimum test would look something like the following

    ```python
    def test_no_error():
        double(5)
    ```

    An optimal test like this:

    ```python
    def test_correct_output():
        output = double(5)
        expected = 10

        assert output == expected
    ```

    And in an ideal case we would have multiple tests like the above
    for other inputs as well, and more logical checks, e.g.,

    ```python
    def test_sign():
        output = double(-4)
        expected = 8

        assert is_positive(output) # (1)!
        assert output == expected
    ```

    1.  This is just some function that checks that a number is positive,
        returning `True` if it is, otherwise it returns `False`.

In the example, we have defined a test case `test_feature_correct_output`,
where we check that the output of `double` given the argument `5` is
`10`. If not, the test will raise and `AssertionError` and the test will not pass.
A passing test is such that it does not raise _any_ errors. We have also utilized the
_decorator_ `@pytest.mark.feature`, which tells pytest that this test has been marked
with the mark `feature`. Marks should be registered in the configuration of pytest,
which can be found in the `pyproject.toml` file's section `[tool.pytest.ini_options]`.
Each mark should be registered only once, and can be
re-utilized as many times as needed.
Multiple test cases can have the same mark, or multiple marks. Marks are a useful
way to not run all tests each time we run pytest, but to run only a subset of them, which
are relevant to the changes we have made when implementing for a new feature, for instance.
We can then run the test with the command

```bash
$ pytest -m feature # (1)!
```

1.  The option `-m feature` tells pytest to only run tests with the mark `feature`. To exclude tests with mark, and run every other test instead,
we can, for instance, issue the command `pytest -m "not feature"`, which would
run all tests that are _not_ marked with the mark `feature`.

The output of pytest will be very explicit whether the test is passing or not. We can
also run all the tests (that have not been explicitly marked to be skipped), with the
command

```bash
$ pytest
```

Since DESDEO has quite many tests defined, this may take a while. It is therefore
recommended to use marks during development to run only a subset of tests that are
relevant to the ongoing work.

However, there are some instances when all the tests should be always run. These
are

1.  Before starting developing any new features, or making modifications. That
    is, after a `git pull` in a clean working tree.
2.  Before we push our changes to a remote repository, e.g., before a `git push`.
3.  Optionally, we might want to run all the tests before any commits as well, e.g.,
    before a `git commit` command.

Running tests in the described cases ensures that we, first of all, start working on
a functioning code base. We can check which tests are passing before we make our
changes. If, after we have made our changes, some of the previously passing
tests are no longer passing, then we know that the changes _we_ introduced,
are likely the source of the tests breaking. In this case, we should investigate
the reason and implement adequate fixes.

Running tests before pushing is also important to ensure that we have not broken
any existing code, and that the code we have introduced (and written tests for!)
is also working as intended. We should never push code that breaks existing code,
unless we have a _very_ good reason to do so. For similar reasons, running all tests
before committing is also advisable.

For examples of existing tests in DESDEO, the reader is encouraged to
check the directory `tests` at the root of the project and the tests therein.
[The official documentation](https://docs.pytest.org/en/8.0.x/) for
pytest is also a valuable resource to check out.

### Documenting

DESDEO comes with a comprehensive documentation. When developing
new features, these should be carefully documented as well. Documentation
in DESDEO can be roughly divided into three main types:

1.  comments found in the source code,
2.  docstrings, and
3.  external or project documentation.

Comments are found in the files containing Python source code
found across DESDEO. These are often pieces of very specific information
related to a line or block of code. They are often present to
help a developer understand what a specific part of the code does.
Comments are often specific and technical, and depend on the context.
They are not meant to be understandable outside the source code.
An example of a comment could be:

```python
def log2(x: float) -> float:
    # argument must be positive and non-zero, if not, raise an error
    if not x > 0:
        msg = f"Argument {x=} must be positive and non-zero." # (1)!
        raise ValueError(msg)

    # we utilize log10 and the change of base formula for computing the base-2
    # logarithm
    return log10(x) / log10(2)  # (2)!
```

1.  In Python f-strings, the formatter `{x=}` prints the name of the variable and its value.
    E.g., instead of writing `x={x}`, we can write `{x=}`.
2.  We assume that we have a function `log10` available that computes the base-10
    logarithm of its argument.

As we can see, comments start with a hash `#`. Taken out of their context, the
comments do not make much sense, but in the code, they provide valuable information.

!!! Note "Write informative comments"
    When writing comments, avoid redundant comments, such as:

    ```python
    # the value '5' is stored in the variable 'a' (1)
    a = 5
    ```

    1.  This is obvious and the comment does not provide any additional informative value.

    instead, try and provide additional information that helps a
    reader understand _why_ a particular piece of code has been written,
    for instance. For instance:

    ```python
    # this value is used to determine an important multiplier in a later
    # function (1)
    a = 5
    ```

    1.  This is not obvious and provides valuable information for understanding the rest of the code.

Docstrings, on the other hand, are a lot more self-contained and informative
than comments.
Docstrings are Python literals (they start and end with thee double quotation marks `"""`)
that are often used to describe Python functions and classes, though they can also be used
to describe many other things as well, e.g., class and module level variables. To illustrate a docstring,
let us return to the previous example:

```python
def log2(x: float, useless: str) -> float:
    """Computes the base-2 logarithm of a given number.

    Computes the base-2 logarithm of a given non-zero and positive number.
    Utilizes a base-10 logarithm and the change of base formula. The formula
    is defined as `y = log10(x) / log10(b)`, where `x` is the
    number for which the logarithm is computed, `y` is the logarithm
    of `x` in the base `b`, and `log10` is the base-10 logarithm. In
    this case, `b=2` since we are computing the base-2 logarithm.

    References:
        Napier, J. (1614). Mirifici Logarithmorum Canonis Descriptio
            [Description of the Wonderful Rule of Logarithms]        

    Raises:
        ValueError: the given argument `x` is either zero or negative.

    Arguments:
        x (float): the number for which the base-2 logarithm should be computed.
            Must be non-zero and positive.
        useless (str): an unused variable to just showcase how we can have
            multiple entries in a section.
        
    Returns:
        float: the base-2 logarithm of `x`.
    """ # (1)!
    # argument must be positive and non-zero, if not, raise an error
    if not x > 0:
        msg = f"Argument {x=} must be positive and non-zero."
        raise ValueError(msg)

    # we utilize log10 and the change of base formula for computing the base-2
    # logarithm
    return log10(x) / log10(2) 
```

1.  The first line of the docstring should be a short summary of the function.
    This is then followed by a more detailed description.
    
    The more detailed description is then followed by sections. The
    section `References` can be used to list one or more references
    related to the function, for example, when it is based on the
    works of others. Each entry in any section starts on an
    indented line. Following lines must be further indented if they
    are related to the entry. A new entry would start on a new line with
    an indentation level one lower than the section name, in this case `References`.

    Likewise, the section `Raises` describes what exceptions may raise
    from the the function. The type of the exception is followed by a colon
    and a description of the reason for the exception.

    In the `Arguments` section, each argument of the function is described.
    The name of the arguments is followed by its type in parentheses, and then
    a colon, after which details about the argument are given.

    Lastly, the return of the function is described in the `Returns`
    section. Here, the type of the return value if followed by a colon
    and a description of the value.

    Each function docstring should have at least an `Arguments` and
    `Return` section.

As we can notice, a docstring is a lot more informative that a mere comment.
The docstring alone is understandable even without the function definition.
However, there exist multiple styles for docstrings. The one illustrated
here follows the docstring format described in
[Google's style guide](https://google.github.io/styleguide/pyguide.html),
which is also the style for docstrings utilized in DESDEO.

Lastly, we have _external_ or _project documentation_. This is easy
to illustrate since we are reading it right now! In other words,
this refers to the part of the documentation that does not
reside in the Python source code itself, but it, as the name
suggests, external, and documents larger entities related
to DESDEO, such as different concepts, or like in this 
tutorial, how to contribute to DESDEO.

The tool utilized for building the very documentation we are
reading, is _mkdocs_. We also utilize its extension
_mkdocstirngs_, for automatically generating reference
documentation from the docstrings written in the Python
source code found across the DESDEO project, and the _Materials_
theme for mkdocs. As with the other tools
discussed in this section, mkdocs is installed on our local machine
if we installed DESDEO with its development dependencies.

The external documentation of DESDEO resides in the directory
`docs` found at the root of the project. The overall structure and
the configuration related to mkdocs, and the other documentation tools 
used, are found in the file `mkdocs.yml`, which is also found at the root
level of the project.

To build and view the current documentation, we can issue the command

```bash
$ mkdocs serve
```

This will build the documentation and create a local server, allowing
us to view the built documentation by opening the url `http://localhost:8000/`
in a web browser.

To better understand the structure of DESDEO's documentation, it is 
best to take a moment and explore the file `mkdocs.yml`, starting with
its top-level contents, and especially the contents in the section `nav:`,
which describes the structure of the generated web page containing this 
documentation. The actual contents of the documentation are written in a rich
markdown format, and are logically arranged in the sub-folders found in `docs/`.
Rich here just refers to the fact that we are using extensions of
the markdown language that support $\LaTeX$, for instance. 
To given an example of the structure, the
contents of this tutorial can be found in the file
`docs/tutorials/contributing.md`.

We will not discuss mkdocs and its extensions further in this tutorial.
A novice contributor will find the easiest time by studying how 
the existing documentation has been written, and
working by example. For further reading resources,
the documentation for [mkdocs](https://www.mkdocs.org/),
[mkdocstrings-python](https://mkdocstrings.github.io/python/),
and [Materials for mkdocs](https://squidfunk.github.io/mkdocs-material/),
are good reference material. 

## Integrated development environments 

Thus far, we have separately discussed the tools utilized
when developing DESDEO. While these tools can be used
as demonstrated, it is often too inconvenient
from a practical point of view. In practice, many of the 
discussed tools are run automatically, or managed though
other, arguably more user friendly tools, such as various
graphical user interfaces.

Integrated development environments, or IDEs, are
programs that offer an environment for developing code,
often integrating many other tools, such as Git and different
linters. They also offer a text, or rather code, editor for
editing the source code found in a project.

Many different IDEs exist, and the choice of the
right IDE is very subjective. For this reason, we have
introduced the tools for developing DESDEO on their own,
without making assumptions regarding use of any IDE. It is
also perfectly fine to not use IDEs, but with modern code bases
and tools, IDEs can streamline an otherwise complicated
tool chain and development process, and thus significantly save
a developer's time.
That being said, we will briefly mention one IDE and
some recommended extensions for easing the process of developing
and contributing to DESDEO.

### Visual studio code

One of the most popular IDEs currently being used, is [Visual studio
code](https://code.visualstudio.com/) (Vscode for short). 
It is available on all major platforms,
making it a portable solution. Its development is backed by a major company, and
it is based on mostly open source software. Vscode is also very
customizable, and has a plethora of different extensions available, both
official and user made. [A more open source version of Vscode is also
available](https://vscodium.com/), which mainly disables Microsoft's telemetry
and strips the application of other proprietary parts. Whichever
version we use, they are virtually the same, but the proprietary version does
come with some extensions that are otherwise not available in the open source
version. However, these are not required or necessary for developing DESDEO.

Vscode comes with Git support out of the box and [is nicely
documented](https://code.visualstudio.com/docs/sourcecontrol/overview).
To manage GitHub specific aspects from Vscode, we need to install the
extension [GitHub Pull Requests](https://marketplace.visualstudio.com/items?itemName=GitHub.vscode-pull-request-github).
This extension allows us to make pull request form Vscode, open and browse issues, and much
more.

For better Python support, including support for enabling code auto-completion, running
tests, and debugging,
the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
is recommended. This extension also supports virtual environments,
which are automatically activated if they reside in the project's
directory.

For linting and code formatting, [the Ruff extension for Vscode](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
is very useful. This extension allows to run Ruff automatically on
our code whenever we, for instance, save our changes. Auto-fixable
issues will be fixed automatically, while other issues will be
highlighted and reported inside Vscode.

To help with documentation, the
[autoDocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring)
extension is useful. It will automatically
generate docstrings templates, populating them
intelligently with relevant sections, e.g.,
`Arguments` by picking the arguments from the
function definition.

To avoid most typos, the extension [Code Spell Checker](https://marketplace.visualstudio.com/items?itemName=streetsidesoftware.code-spell-checker)
can be useful. It is smart enough to identify typographical errors
in source code despite Python's syntax. Perhaps most importantly, it will
point out errors in docstrings and markdown files as well when writing
documentation.

All of these extensions can be configured to further match one's needs,
but we are not going to to discuss these aspects in this tutorial.
Many other extensions exist as well that can prove to be useful. What
we have listed here is a bare minimum to get us started. And as said,
the choice of, or lack of, the best IDE is personal and subjective.
One is free to explore the many other alternatives available as well.

## Summary

We have covered many topics in this tutorial, and at first,
its contents may feel overwhelming. However, despite first
impression, most of the discussed steps and practices will 
become almost second nature fairly quickly. To support
the reader's endeavors in contributing to DESDEO, we have
summarized the main steps to take into account when contributing
to DESDEO in this last section.

### Contribution workflow

1.  Fork the DESDEO repository. This is done on GitHub.
2.  Clone the fork (`$ git clone <url to fork>`)
3.  Make sure the fork is up to date with the upstream, or main repository, of DESDEO. 
    ```bash
    $ git remote add upstream \ # (1)!
        git@github.com:industrial-optimization-group/DESDEO.git
    ```

    1.  This just indicates that the line continues on a new row.

3.   If no virtual environment exists, create and activate a virtual environment. (`$ poetry shell`)
4.   Else activate an existing virtual environment. (`$ poetry shell`)
5.  Run tests and make sure at least most of them are passing. (`$ pytest`) 
6.  Create or switch to a local branch. 
    ```bash
    $ git branch feature-x
    $ git checkout feature-x
    ```
7.  Make changes to the code. Stage them, and  keep committing the changes and running tests now and then.
    ```bash
    $ git add -A
    $ git commit
    ```
8.  Remember to write tests and documentation, including comments, docstrings, and external documentation,
    when relevant.
9.  Me mindful of the outputs of Ruff and mypy. Fix errors and warnings whenever possible.
10.  Push your commits to your fork on GitHub. (`$ git push origin feature-x`)
11.  Make a pull request on GitHub. 
12.  Goto 3.

## Conclusions, where to go next, and our Discord server

Many of the topics covered in this tutorial are not
unique to DESDEO, but rather adhere to some common modern
practices in developing Python software. By investing a little
bit of our time in familiarizing ourselves with the various tools
discussed, we will be able to save a lot of time in the future. Moreover,
a lot of the information covered is applicable to other open source
projects as well.

We are now in a position to start contributing to DESDEO. If
we do not know where to start, we can check the
[open issues](https://github.com/industrial-optimization-group/DESDEO/issues)
found on DESDEO's GitHub repository.

For further support, feel free to join the MCDM Community's Discord server.
It has dedicated channels for DESDEO as well. There, you may ask for further assistance
and discuss DESDEO and its development in general.

To join the Discord server, [click here!](https://discord.gg/TgSnUmzv5M)

Happy coding!
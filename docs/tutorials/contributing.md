# Contributing to DESDEO

In this tutorial, step-by-step instructions are given on how to begin
contributing to DESDEO, and what one should considers when developing DESDEO,
such as coding practices and typical workflows. 

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

### Windows

Here, we assume to be operating in a __powershell__ environment. The first step
is to install Python on the system, unless it is already installed. To check
which version of Python are supported, check the section
[Requirements](./installing.md#requirements). If utilizing the `.exe.`
installer for installing Python, we should ensure that the installer also sets the
necessary `Path` environment variables. There should be a check-box for this
during the installation. Python binaries for Windows platforms can be found (on
the Python website)[https://www.python.org/downloads/].

!!! Note
    To ensure changes in `Path` variables are in effect, it is advisable to logout
    of the current Windows session, and then log back in.

To check that Python has been installed correctly on you system, we can open powershell
and run the command

```shell
$ python --version
```

this should report the version of the currently installed Python interpreter.

Next, we need to install _git_ for version control and _poetry_ for managing
packages and the virtual environment for developing DESDEO. To facilitate this,
it is recommended to install (scoop)[https://scoop.sh/]. Installation
instructions are provided on scoop's webpage. Using scoop is optional, but we
will assume that it has been installed for the remainder of this section.

To install poetry, we will follow the (recommended way and use _pipx_)[https://python-poetry.org/docs/#installation].
To install pipx, in a powershell, we run (the commands)[https://pipx.pypa.io/stable/installation/]

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

once more after installing poetry. After this, we should log out and back in into a Windows session.

Finally, we can install git utilizing scoop:

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

Homebrew something something. I have no idea. Just follow
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

We can then proceed to download the source code for DESDEO
using git with the command

```bash
$ git clone git@github.com:industrial-optimization-group/DESDEO.git
```

!!! Note
    It is recommended to utilize the SSH (secure shell) url when
    cloning DESDEO. This, however, requires that an SSH public key
    has been generated and added to one's GitHub user account.
    For instructions on how to setup and SSH key,
    see [Adding a new SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account?platform=windows)

Lastly, we should change to the newly cloned directory with the source code

```bash
$ cd DESDEO
```

!!! Note
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
that we are utilizing a correct version of Python. Run

```bash
$ python --version
```

to check the version. If the version is correct, then we can proceed. If not,
we should point poetry to the Python binary of the version we wish to utilize,
e.g.,

```shell
$ poetry env use /usr/bin/python
```

!!! Note
    For managing multiple Python versions, a tool, such
    as [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file)
    is recommended.

Before proceeding, it is useful to set the poetry configuration
`virtualenvs.in-project` to `true`. This will ensure that our
virtual environemnt will be created in the `.venv/` directory
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

```shell
$ poetry install -E standard --with-group dev
```

This might take a while. After poetry is done installing, and there
are no error messages, we should be able to run

```shell
$ pytest
```

which runs all the tests present in DESDEO. Not all of them
will be passing, but a majority of them should. This should indicate
to us now that DESDEO has been correctly installed, and our
virtual environment is now setup correctly.

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

## Workflow for contributing to DESDEO
# Installing DESDEO

This guide goes over on how to install DESDEO on your machine and start utilizing it.

## Requirements

DESDEO requires at least Python version `3.12`. Ensure this version is available on your system.

### Third party optimizers

DESDEO relies on many 3rd party optimizers, we need to ensure that these are
present on your system and available in the environment DESDEO is run.
Currently, the external optimizers needed in DESDEO are:

- Bonmin,
- cbc, and
- ipopt.

These optimizers are part part of the [COIN-OR project](https://www.coin-or.org/). You may install these
optimizers manually, or you can utilize pre-compiled binaries provided by the AMPL team [here](https://ampl.com/products/solvers/open-source-solvers/).
You will need to register (which is free). Once registered, download the coin module for your system's architecture (Windows, Mac, or Linux). We also provide these 
same files in DESDEO's repository (under releases). To get specific binaries, use one of the following links:

- [Windows](https://github.com/industrial-optimization-group/DESDEO/releases/download/supplementary/coin.mswin64.20230221.zip)
- [Mac](https://github.com/industrial-optimization-group/DESDEO/releases/download/supplementary/coin.macos64.20211124.tgz)
- [Linux (X86_64)](https://github.com/industrial-optimization-group/DESDEO/releases/download/supplementary/solver_binaries.tgz)

After downloading the archive file with the solvers, ensure the contents of the unpacked directory (the binaries `bonmin`, `cbc`, and `ipopt`) are available in you
system's `PATH` variable. It might be a wise idea to keep the binaries in the extracted folder in case they come with, e.g., shared libraries, which may depend
on your architecture.

## Installation (general)

!!! Note "Read first"

    This section covers on how to install DESDEO using the source on GitHub.
    DESDEO is also available on PyPI to be installed via `pip`:

    ```shell
    pip install desdeo
    ```

    However, you may still required some of the [third party
    optimizers](#third-party-optimizers), and [setting up a virtual
    environment](#setting-up-a-virtual-environment) is never a bad idea.

    If you intend to install DESDEO from its current source on GitHub, read on!

The following instructions assume you have (mostly) full control of your system.
If you are installing DESDEO on a more restricted Windows environment, such as a work
laptop, please see [this section](#installation-for-restricted-windows-pcs).

### Getting the source code
To begin, use `git` (or download the source of DESDEO [here](https://github.com/industrial-optimization-group/DESDEO/)). If using `git`,
you can get DESDEO's latest source code with the command (open a terminal or powershell):

```bash
git clone git@github.com:industrial-optimization-group/DESDEO.git
```

### Setting up a virtual environment

Before proceeding, we need to set up a virtual environment to run DESDEO and install its dependencies.
Make sure you are at the root level of the DESDEO directory, which you should now have downloaded in your
current working directory. E.g., in a terminal, `cd DESDEO`. To ensure you are in the correct directory,
you should be able to see files like `pyproject.toml`, `README.md`, and others.

There are many ways to setup and activate a virtual environment. Some examples have been given below:

=== "Python's venv module"

    ```bash
    python -m venv .venv # (1)!
    ```

    1. Ensure that your Python's version is at least 3.12!

    To activate the environment:

    === "Mac and Linux"

        ```bash
        source .venv/bin/activate
        ```

    === "Windows"

        ```powershell
        .venv\Scripts\activate
        ```

=== "Anaconda"

    ```bash
    conda create --name .myenv python=3.12
    ```

    To activate the environment:

    ```bash
    conda activate .myenv
    ```

=== "Poetry"

    !!! Note

    Version 2.2 or greater of `poetry` is required!
 
    This assumes you already have [`poetry`](https://python-poetry.org/) available on your system.

    ```bash
    poetry env activate # (1)!
    ```

    1. This assumes your system's Python version is 3.12. If not, you can use `poetry env use python3.12`, but this requires that version
        3.12 is available on your system. 

    __This command will print the command you must execute to activate the virtual environment. It does
    not activate it.__ Copy-paste the command printed by poetry and execute it to activate the virtual
    environment.

=== "uv"

    This assumes you already have [`uv`](https://github.com/astral-sh/uv) available on your system.

    `uv` is handy, as it can be used to manage Python versions as well. To install Python 3.12 and
    create a virtual environment, run

    ```bash
    uv venv --python 3.12
    ```

    This will download the latest version fo Python 3.12 (if not already available) and then create
    a virtual environment in the current directory under a new folder `.venv`.

    If using the default virtual environment name `.venv`, `uv` will automatically
    use the virtual environment in subsequent invocations. Otherwise, the environment
    needs to be activated locally. 

!!! Note

    Remember to reactivate your virtual environment if you exit it, and then return to it.

### Installing dependencies

After setting up a virtual environment, we next need to install DESDEO's dependencies.
For this, we can utilize either `poetry` or `uv`. It is also possible to use `pip` directly,
but it is not recommended. Make sure your virtual environment
is activated!

=== "Poetry"

    If not already done, we need to first install `poetry`:

    ```bash
    pip install poetry # (1)!
    ```

    1. If `poetry` is already installed in your virtual environment, you may skip this step.

    After installing poetry, we can use the following command to install DESDEO's core-logic dependencies

    ```bash
    poetry install --only main
    ```

    If you wish to install the development and web dependencies as well, then run the following command instead:

    ```bash
    poetry install
    ```

=== "uv"

    If not already done, we need to first install `uv`:

    ```bash
    pip install uv
    ```

    To install DESDEO's core-logic dependencies, run

    ```bash
    uv sync --no-default-groups
    ```

    If you wish to install the development and web dependencies as well, then run the following command instead:

    ```bash
    uv sync
    ```

=== "pip"

    You can install desdeo and all optional dependencies by running

    ```bash
    pip install -e . --group all-dev
    ```

    If you don't want all the optional stuff, you can also specify different group(s) or no group at all.

    It's worth noting that pip does not automatically do anything to your virtual environments, so you will need to handle that manually. It also
    won't help you figure out conflicting dependencies.

And now we should be done! DESDEO should now be available on your system in your current virtual environment.

!!! Note "Extra dependencies?"

    By default, an 'poetry install' and 'uv sync' will install just the dependencies of
    the __core-logic__. This is meant for cases where DESDEO is used like a library, i.e.,
    you do not intend to develop DESDEO or use the web-API or web-GUI parts of it. In case you
    wish to develop or utilize DESDEO past what the core-logic has to offer, then it is 
    recommended to install all the extra dependencies.

## Installation (for restricted Windows PCs)

This guide showcases how to install DESDEO specifically on a Windows machines,
which might impose strict restrictions on what can be installed on the system,
such as the work machines supplied by the University of Jyväskylä (JYU) using
Anaconda.  The steps outlined here should work on most Windows systems as long
as you are using Anaconda for your Python installation.

If you successfully installed DESDEO using the
[general instructions](#installation-general), you do not need
to read further.

!!! Note
    
    While this guide will refer to _JYU Windows machines_, it should be
    applicable to your restricted work machine regardless of company. However,
    if this is not the case, feel free to open an issue, and we will see what
    can be done.

### Anaconda

First, install Anaconda. If you are on a JYU (or any other company's) Windows
machine, you can get it from the Software Center (or equivalent) **without
needing admin rights** for the installation. If not, please ask your IT support
to install Anaconda on your machine.

You can also download Anaconda from
[https://www.anaconda.com/download](https://www.anaconda.com/download). If you
prefer or have limited space available on your computer,
[Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main) should
work fine too.

### Installing DESDEO

First, you need to open an Anaconda prompt. To find that, press the windows key
and type `anaconda prompt`.

#### Figure out the install location

Next, you need to decide where on your computer you want to install DESDEO. If
you are on a JYU Windows machine, I recommend something like
`C:\MyTemp\code\DESDEO`.

In your Anaconda prompt, type

```cmd
mkdir C:\MyTemp\code
```

and

```cmd
cd C:\MyTemp\code
```

That will create the desired folder and navigate there.

!!! question "Why I should not install DESDEO on my Desktop?"

    On JYU Windows machines, your Desktop and Documents folders are not stored
    only on your hard drive, but on a network server. That can cause issues when
    running your own code, so you should store any code you write on your
    computer's hard disk. The `C:\MyTemp\` folder is a good place for that.

#### Creating a virtual environment

DESDEO requires at least Python version `3.12`. To control the version of Python
we are using and what packages are available, we are first going to create a
virtual environment, which we will name `desdeo`.

In your Anaconda prompt, type

```bash
conda create -n desdeo python=3.12
```

That will create a new virtual environment named desdeo that has Python 3.12
installed. You will probably be asked if you want to continue. You should
probably answer yes.

Then activate your new virtual environment by typing in your Anaconda prompt

```cmd
conda activate desdeo
```

!!! question "Why do I need a virtual environment?"

    It is very common for your different programming projects to require
    different versions of Python and Python packages. By using virtual
    environments you do not have to uninstall and reinstall packages to get
    compatible versions, and you avoid _dependency hell_. You can just change
    the active virtual environment instead.

#### Downloading DESDEO

The best way to download DESDEO is to use git. If you do not know what git is or
if you have it installed, type in your Anaconda prompt

```cmd
git
```

If you get a response saying something like `'git' is not recognized as an internal or external command, operable program or batch file.`, then you likely do not have git installed.

To install git, type in your Anaconda prompt

```cmd
conda install git
```

and say yes when asked if you want to proceed.

Once you have git installed, you can use it to download DESDEO. Type

```cmd
git clone -b master --single-branch https://github.com/industrial-optimization-group/DESDEO.git
```

That creates a clone of the master branch of the DESDEO project. If you want all the branches, just use `git clone https://github.com/industrial-optimization-group/DESDEO.git`.

Git should have created a new subfolder called DESDEO. Let us navigate there by typing

```cmd
cd DESDEO
```

#### Installing dependencies
After setting up a virtual environment and downloading the source code, we next
need to install DESDEO's dependencies. Type in your Anaconda prompt

```cmd
pip install -e . --group all-dev
```
If you don't want all the extras, you can list some other groups or no groups at all.

#### Using uv with Anaconda

You can also use uv if you want. Make sure you have it installed first (`pip install uv`).

The default cache location for uv will likely not work on a JYU machine, because a normal user
doesn't have the necessary rights there. Thus, you should change the default cache location of
uv to, for example, the anaconda environment.
```cmd
conda env config vars set UV_CACHE_DIR=%CONDA_PREFIX%\uv_cache
conda activate desdeo
```

You can then use uv to install DESDEO and the required packages by typing

```cmd
uv sync
```

Newer versions of uv are able to automatically detect that you have a conda env active and will install the dependencies there.


## Where to go next?

To get a feel on how DESDEO can be utilized to model and solve multiobjective optimization problems
in practice, checkout [this guide](./full_example.ipynb).
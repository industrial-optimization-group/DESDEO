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

    This assumes you already have `poetry` available on your system.

    ```bash
    poetry env activate # (1)!
    ```

    1. This assumes your system's Python version is 3.12. If not, you can use `poetry env use python3.12`, but this requires that version
        3.12 is available on your system. 

    __This command will print the command you must execute to activate the virtual environment. It does
    not activate it.__ Copy-paste the command printed by poetry and execute it to activate the virtual
    environment.

!!! Note

    Remember to reactivate your virtual environment if you exit it, and then return to it.

### Installing dependencies

After setting up a virtual environment, we next need to install DESDEO's dependencies.
For this, we will need to first install `poetry` in our virtual environment:

```bash
pip install poetry # (1)!
```

1. If `poetry` is already installed in your virtual environment, you may skip this step.

After installing poetry, we can use the following command to install DESDEO's dependencies

```bash
poetry install
```

If you wish to install the development dependencies as well, then run the following command instead:

```bash
poetry install --with dev
```

And now we should be done! DESDEO should now be available on your system in your current virtual environment.

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

```bash
mkdir C:\MyTemp\code
```

and

```bash
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

```bash
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

```bash
git
```

If you get a response saying something like `'git' is not recognized as an internal or external command, operable program or batch file.`, then you likely do not have git installed.

To install git, type in your Anaconda prompt

```bash
conda install git
```

and say yes when asked if you want to proceed.

Once you have git installed, you can use it to download DESDEO. Type

```bash
git clone -b master --single-branch https://github.com/industrial-optimization-group/DESDEO.git
```

That creates a clone of the master branch of the DESDEO project. If you want all the branches, just use `git clone https://github.com/industrial-optimization-group/DESDEO.git`.

Git should have created a new subfolder called DESDEO. Let us navigate there by typing

```bash
cd DESDEO
```

#### Installing dependencies
After setting up a virtual environment and downloading the source code, we next
need to install DESDEO's dependencies.  For this, we will need to first install
`poetry` in our virtual environment. Type in your Anaconda prompt

```bash
pip install poetry
```

Next, we need to set up some environmental variables to make sure that we do not
run into trouble when installing Python packages using Poetry. Type the four
following commands in your Anaconda prompt:

```bash
    conda env config vars set POETRY_CACHE_DIR=C:/MyTemp/temp
    conda env config vars set TEMP=C:/MyTemp/temp
    conda env config vars set TMP=C:/MyTemp/temp
    conda activate desdeo
```

You can then install DESDEO and the required packages by typing

```bash
poetry install
```
If you want the development dependencies installed as well, use `poetry install --with dev` instead.

!!! question "Why did I have to do that thing with the env configs?"

    Installing Python packages with Poetry requires the creation and running of
    some temporary files. However, the default locations where those files are
    placed are not accessible without admin rights on JYU Windows machines.
    That's why we are using `C:\MyTemp\temp` folder, because every user has the
    necessary rights to do things there.

    If you are not on a JYU Windows machine, you can probably safely skip that
    part. If you are in some other tightly managed system, you might need to
    figure out a different folder to use.


## Where to go next?

To get a feel on how DESDEO can be utilized to model and solve multiobjective optimization problems
in practice, checkout [this guide](./full_example.ipynb).
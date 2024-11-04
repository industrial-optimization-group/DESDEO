# Installing DESDEO
This is a more advanced guide on how to install DESDEO with more details than the README.

## Requirements
DESDEO requires at least Python version `3.12`. Ensure this version is available on your system.

### Third party optimizers
DESDEO relies on many 3rd party optimizers, we need to ensure that these are available as well on your system.
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

## Installation
### Getting the source code
To begin, use `git` (or download the source of DESDEO [here](https://github.com/industrial-optimization-group/DESDEO/archive/refs/heads/desdeo2.zip)). If using `git`,
you can get DESDEO's source code with the command (open a terminal or powershell):

```bash
git clone --branch desdeo2 git@github.com:industrial-optimization-group/DESDEO.git
```

This command will download DESDEO's `desdeo2` branch in your current working directory.

!!! Note

    Ensure you are in the `desdeo2` branch of the repository! Following the above steps this should be the case,
    but caution is advised.

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
    poetry shell # (1)!
    ```

    1. This assumes your system's Python version is 3.12. If not, you can use `poetry env use python3.12`, but this requires that version
        3.12 is available on your system.

    You virtual environment should be now active.

!!! Note

    Remember to reactivate your virtual environment if you exit it!

### Installing dependencies
After setting up a virtual environment, we next need to install DESDEO's dependencies.
For this, we will need to first install `poetry` in our virtual environment:

```bash
pip install poetry # (1)!
```

1. If `poetry` is already installed in your virtual environment, you may skip this step.

After installing poetry, we can use the following command to install DESDEO's dependencies

```bash
poetry install -E "standard"
```

!!! Note

    If the `polars package complains about CPU architecture on your system when trying to run
    DESDEO, try installing DESDEO with the following command instead:

    ```bash
    poetry install -E "legacy"
    ```

And now we should be done! DESDEO is not available on your system in your current virtual environment.

## Where to go next?
To get a feel on how DESDEO can be utilized to model and solve multiobjective optimization problems
in practice, checkout [this guide](../notebooks/full_example.ipynb).
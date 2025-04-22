# Simple guide for Installing DESDEO

This is a less advanced guide on how to install DESDEO specifically on a JYU Windows machine using Anaconda.
The steps outlined here should work on most Windows systems as long as you are using Anaconda for your Python installation.

If you have opinions about operating systems or Anaconda, you should check out the more advanced [installation guide](./installing.md) instead.

## Anaconda

First, install Anaconda. If you are on a JYU Windows machine, you can get it from the Software Center **without needing admin rights** for the installation.

You can also download Anaconda from [https://www.anaconda.com/download](https://www.anaconda.com/download). If you prefer or have limited space available on your computer, [Miniconda](https://www.anaconda.com/docs/getting-started/miniconda/main) should work fine too.

## Installing DESDEO

First, you need to open Anaconda prompt. To find that, press the windows key and type `anaconda prompt`.

### Figure out the install location

First, you need to decide where on your computer you want to install DESDEO. If you are on a JYU Windows machine, I recommend something like `C:\MyTemp\code\DESDEO`.

In your Anaconda Prompt, type
```
mkdir C:\MyTemp\code
```
and
```
cd C:\MyTemp\code
```
That will create the desired folder and navigate there.

!!! question "Why shouldn't I install DESDEO on my Desktop?"

    On JYU Windows machines, your Desktop and Documents folders are not stored only on your hard drive, but on a network server. That can cause issues when running your own code, so you should store any code you write on your computer's hard disk. The `C:\MyTemp\` folder is a good place for that.

### Creating a virtual environment

DESDEO requires at least Python version `3.12`. To control the version of Python we are using and what packages are available, we are first going to create a virtual environment. I'm going to call mine `desdeo`.

In your Anaconda Prompt, type
```
conda create -n desdeo python=3.12
```
That will create a new virtual environment named desdeo that has Python 3.12 installed. You will probably be asked if you want to continue. You should probably answer yes.

Then activate your new virtual environment by typing in your Anaconda Prompt
```
conda activate desdeo
```

!!! question "Why do I need a virtual environment?"

    It is very common for your different programming projects to require different versions of Python and python packages. By using virtual environments you don't have to uninstall and reinstall packages to get compatible versions. You can just change the active virtual environment instead.

### Downloading DESDEO

The best way to download DESDEO is to use git. If you don't know what git is or if you have it installed, type in your Anaconda Prompt
```
git
```
If you get a response saying something like `'git' is not recognized as an internal or external command, operable program or batch file.`, then you probably don't have git installed.

To install git, type in your Anaconda Prompt
```
conda install git
```
and say yes when asked if you want to proceed.

Once you have git installed, you can use it to download DESDEO. Type
```
git clone -b desdeo2 --single-branch https://github.com/industrial-optimization-group/DESDEO.git
```
That creates a clone of the desdeo2 branch of the DESDEO project. If you want all the branches, just use `git clone https://github.com/industrial-optimization-group/DESDEO.git`.

Git should have created a new subfolder called DESDEO. Let's navigate there, by typing
```
cd DESDEO
```

### Installing dependencies
After setting up a virtual environment and downloading the source code, we next need to install DESDEO's dependencies.
For this, we will need to first install `poetry` in our virtual environment. Type in your Anaconda Prompt

```
pip install poetry
```
Next, we need to set up some environmental variables to make sure that we don't run into trouble when installing Python packages using Poetry. Type the four following commands in your Anaconda Prompt
```
    conda env config vars set POETRY_CACHE_DIR=C:/MyTemp/temp
    conda env config vars set TEMP=C:\MyTemp\temp
    conda env config vars set TMP=C:\MyTemp\temp
    conda activate desdeo
```
You can then install DESDEO and the required packages by typing
```
poetry install -E "standard"
```
If you want the API packages installed as well, use `poetry install -E "standard api"` instead.

!!! question "Why did I have to do that thing with the env configs?"

    Installing Python packages with Poetry requires the creation and running of some temporary files. However, the default locations where those files are placed are not accessible without admin rights on JYU Windows machines. That's why we are using `C:\MyTemp\temp` folder, because every user has the necessary rights to do things there.

    If you are not on a JYU Windows machine, you can probably safely skip that part. If you are in some other tightly managed system, you might need to figure out a different folder to use.

### Third party optimizers
DESDEO relies on many 3rd party optimizers, we need to ensure that these are available as well on your system.
Currently, the external optimizers needed in DESDEO are:

- Bonmin,
- cbc, and
- ipopt.

These optimizers are part part of the [COIN-OR project](https://www.coin-or.org/). You may install these
optimizers manually, or you can utilize pre-compiled binaries provided by the AMPL team [here](https://ampl.com/products/solvers/open-source-solvers/).
You will need to register (which is free). Once registered, download the coin module for your system's architecture (Windows, Mac, or Linux). We also provide these 
same files in DESDEO's repository (under releases). You can get the Windows version [here](https://github.com/industrial-optimization-group/DESDEO/releases/download/supplementary/coin.mswin64.20230221.zip).

Extract the zip-file and copy the contents of the contents of the unpacked directory (the binaries `bonmin`, `cbc`, and `ipopt`) somewhere that is listed in your
system's `PATH` variable. The folder where your virtual environment is located is a good option. If you used the name desdeo on a JYU Windows machine, the folder should be `C:\devel\anaconda3\envs\desdeo`.

## Where to go next?
To get a feel on how DESDEO can be utilized to model and solve multiobjective optimization problems
in practice, checkout [this guide](../notebooks/full_example.ipynb).
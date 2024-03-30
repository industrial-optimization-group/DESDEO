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

Lastly, we also assume that we have a GitHub account setup. If not,
we can visit (GitHub)[https://github.com/] to setup a new account.

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
    cloning DESDEO. This, however, requires that an SSH public key
    has been generated and added to one's GitHub user account.
    For instructions on how to setup and SSH key,
    see [Adding a new SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account?platform=windows)

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

!!! Note "Multiple Python versions"
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

## Typical git workflow for contributing to DESDEO

This section outlines the standard process for contributing to DESDEO using Git
and GitHub. This workflow assumes that we have a GitHub account. If this is not
the case, we should create one at [GitHub](https://github.com/) first. The workflow
involves forking the DESDEO repository, cloning our fork of the repository to
our local machine, making changes, and then submitting these changes as a pull
request.

### Forking the DESDEO repository

A fork is a copy of a repository that we manage and that is a completely
separeate entity from the original repository, often referred to as the
_upstream_. Forking a repository allows us to freely experiment with changes
without affecting the original project.

To fork a repository:

- Visit the [DESDEO GitHub](https://github.com/industrial-optimization-group/DESDEO) repository.
- In the top-right corner of the page, click the __Fork__ button.
- This action creates a copy of the DESDEO repository in your GitHub account.
- To ensure we are working on a fork, the url to our repository should be of the form _https://github.com/ourusername/DESDEO_. We might
have a different name for the forked reposiotry if we chose one when making the fork.

### Cloning the fork

To work on our fork on a local machine, we need to clone it first. Cloning
creates a local copy of our fork. In practice, it downloads the repository
and its history to our machine.

To clone our fork:

- On GitHub, we navigate to our fork of the DESDEO repository.
- Above the file list, there should be a green button labeled "Code". Clicling the button should
reveal a smaller window. We should select the "SSH" tab and copy the given url.
- In a terminal, we then navigate to where we want to place the local repository.
- Then we clone the fork using the command:

```bash
$ cd ~/workspace # (1)!
$ git clone <URL-of-the-fork>
$ cd DESDEO
```

1.  _workspace_ is just a directory where we want to store the direcotry
    containing our fork. this is just an example, we can use any directory we want.

It is highly recommended to use the SSH url. This requires setting up a
SSH key pair on our local machine and uploading the public key to GitHub.
[This info box](#note:ssh) gives further details on the process.

### Setting the upstream repository

It is beneficial that we periodically check the upstream, e.g., the original
reposiotry of DESDEO for changes, and update our fork. This ensures
that our local version of DESDEO is up to date with new canges, and
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
(once DESDEO 2.0 is released, this would be the `main` branch). We
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
    directory containing our fork.

We can always check which files are staged, and which are not, with the command

```bash
$ git status
```

!!! Note "On git status"
    The command `git status` will 99% of the time tell us exactly
    what we should in case of errors related to git. Carefully reading the
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
    A simialr test was also added for the E-NAUTILUS methods. Both of these 
    tests should be passing." __There is no such thing as a "too long"
    commmit message!__

We can make as many commits as we like. We do not need to have anything "ready"
when making a commit. We should not be afraid of committing _too often_; there
is no such thing!
Actually, the more commits the better. Committing can be understood as "saving"
our changes to the version control system, which also creates a "checkpoint" we
can roll our project back to at any point in time. The changes in the commits
are still only local, i.e., on our own machine. To integrate them into our fork
on GitHub, or the DESDEO upstream, we would have to push them first.

### Pushing changes to our fork

After committing our changes, we can push them to our fork on GitHub:

```bash
$ git push origin feature-x # (1)!
```

1.  `origin` refers to the GitHub repository with out fork, it points
    to the repository we originally cloned from, which in this case is
    our fork.
    `feature-x` is the branch name we have been working on and committing to.

This does not make any changes to the original upstream repository of
DESDEO. For our changes to be integrated in the upstream, we
need to make a pull request.

### Creating a pull request

A pull request is a GitHub feature were we can notify the maintainers of an
upstream repository, usually the one we originally cloned (in this case DESDEO),
that we have made changes that we would like to integrate in upstream. When
making a pull request, it is assumed that a feature, or features, to be added
are complete and not work in progress.  One a pull request has been made, the
maintainers of DESDEO will be notified.  They will then check the changes, and
either accept them as they are and pull them into the upstream, or they can give
some feedback on what needs to be changed for the pull request to be accepted.
The more commits in a pull request, the easier it is for a maintainter to review
the changes.

In practice, making a pull request consists of the following steps:

1. Go to the fork on GitHub.
2. Swith to the branch with our new feature, e.g., `feature-x`.
3. There should be a green "Pull request" button next to our branch. Click it.
4. We can then review the changes in the pull request againts the upstream. We can also
provide additional information about the contents of the pull request.
5. Once we are done creating the pull request and describing it, we can then create it.

We may still continue working on our local branch and pushing commits to our fork.
The pull request can always be updated with the new changes in GitHub.

### Keeping your fork up to date

While working on our fork, it is a good practice to keep it up to
date with the upstream. This is important because, for example,
a pull request from another contributor might have been accepted into the
mainstream while we have been working on our local fork. Some of these changes might also
affect the code we have been working, and we should make sure our changes are
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
2.  Remember, this is the main branch ofthe upstream, which we forked and which we want to keep up with.
3.  This adds all the changes made in the upstream to our local fork. The `desdeo2` branch of our __local__ fork is now up to date.
4.  Lastly, we want to update the fork in our repository, or remote as well, __which is on GitHub__. This command pushesh the updated
    version of the main working branch to our fork on GitHub as well.

If we have work in progress in our feature branch (e.g., `feature-x`), we can then change back to it and attempt to merge the most recent
changes in the upstream with our work:

```bash
$ git checkout feature-x  # (1)!
$ git merge desdeo2 # (2)!
```

1.  We are now in our feature branch again.
2.  This will attempt to merge all the changes in the upstream with our feature branch.

If we have made changes in our code to part of the code that has also been
changed in the upstream, then we would have a _merge conflict_. The output of
the command `git status` should give us plenty of information on how to proceed.
For further instuctions on how to resolve merge conflicts, see the section
[Further resources](#further-resources).

### Further resources

TODO.

## Development practices

TODO.
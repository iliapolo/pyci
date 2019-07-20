[![Build Status](https://travis-ci.org/iliapolo/pyci.svg?branch=release)](https://travis-ci.org/iliapolo/pyci)
[![Requirements Status](https://requires.io/github/iliapolo/pyci/requirements.svg?branch=release)](https://requires.io/github/iliapolo/pyci/requirements/?branch=release)
[![Coverage Status](https://coveralls.io/repos/github/iliapolo/pyci/badge.svg?branch=release)](https://coveralls.io/github/iliapolo/pyci?branch=release)
[![PyPI Version](http://img.shields.io/pypi/v/py-ci.svg)](https://pypi.org/project/py-ci/)
[![Supported Python Versions](https://img.shields.io/pypi/pyversions/py-ci.svg)](https://pypi.org/project/py-ci/)
[![Is Wheel](https://img.shields.io/pypi/wheel/py-ci.svg?style=flat)](https://pypi.org/project/py-ci/)
[![PyCI release](https://img.shields.io/badge/pyci-release-brightgreen.svg)](https://github.com/iliapolo/pyci)

PyCI provides a set of opinionated CI related operations, specifically built for Python projects.

## Why should I use it?

What if I were to tell you, that you could, **automatically**:

- Package your project to binary executables (Linux, Mac, Windows). As well as a Windows installer!
- Create GitHub releases with a pretty changelog and automatic version bumps
- Upload wheels to PyPI

Would that be something you might be interested in?

If your answer is yes, or if you just got the reference, carry on 😎

## Notable Features

* [Fully automated release process](https://github.com/iliapolo/pyci#release)
* [Changelog generation](https://github.com/iliapolo/pyci#changelog-generation)
* [Packaging to various formats](https://github.com/iliapolo/pyci#packaging)
* [Remote GitHub commits](https://github.com/iliapolo/pyci#remote-github-commits)

### Release  

The release command integrates with your existing CI providers and enables continuous release of 
the project. All you have to do is invoke the command at the end of your CI workflow. Once you run the command `pyci
 release`, it will detect the CI provider and perform a release of the associated commit.

```text
    ___    _  _    ___     ___
   | _ \  | || |  / __|   |_ _|
   |  _/   \_, | | (__     | |
  _|_|_   _|__/   \___|   |___|
_| """ |_| """"|_|"""""|_|"""""|
"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'

* Detected CI Provider: CircleCI
→ Releasing branch 'release'
  → Validating build https://circleci.com/gh/iliapolo/pyci/420
    * Build is not a PR... ✓
    * Build is not a TAG... ✓
    * Build branch is 'release'... ✓
  → Validating commit
    * Commit references an issue... ✓
    * Issue is labeled with a release label... ✓
  → Generating changelog
    * Collecting commits
    → Analyzing 2 commits
      * Initial release (#2) ✓
      * Initial commit ✓
  * Bumping version to 0.2.0
  * Creating a GitHub release
  * Uploading changelog... ✓
  * Updating release branch... ✓
  * Updating master branch... ✓
  → Closing issues
    * Closing issue number 1... ✓
→ Creating and uploading packages
  → Binary
    * Packaging binary... ✓
    * Uploading py-ci-x86_64-Linux... ✓
  → Wheel
    * Packaging wheel... ✓
    * Uploading py_ci-0.2.0-py2.py3-none-any.whl... ✓     
→ Hip Hip, Hurray! :). Your new version is released and ready to go.
  * Github: https://github.com/iliapolo/pyci/releases/tag/0.2.0
  * PyPI: https://pypi.org/manage/project/py-ci/release/0.2.0/
```

Once the command completes, navigate to the release on GitHub. You should see something like this:

[![release](./assets/release.png)](./assets/release.png)

### Packaging

###### Usage → pyci pack --help
<details closed>
<summary>Show</summary>

```text
Usage: pyci pack [OPTIONS] COMMAND [ARGS]...

  Sub-command for packing source code.

  Notice that in case neither --sha nor --path are provided, the last commit
  from your repository's default branch will be used.

Options:
  --repo TEXT  Github repository full name (i.e: <owner>/<repo>). When running
               inside a CI system, this will be automatically detected using
               environment variables.
  --sha TEXT   Pack a specific sha.
  --path TEXT  Pack a local copy of the repo.
  --help       Show this message and exit.

Commands:
  binary  Create a binary executable.
  wheel   Create a python wheel.
```
</details>
<br>

PyCI helps you create various packages from you project with a single command line tool. These 
commands are just wrappers around some popular python packaging tools.

In case your project is just a library, all you really need is to package it as a wheel, which is
straightforward and not very interesting. However, if you are building a command line tool, 
its a good idea to pack to various formats so that your users can easily install and run 
it, without having to be familiar with the python echo system (essentially pip). For example, 
imagine packaging your tool as a PyInstaller binary file, docker image, deb/rpm/dmg package...

You can create packages from your local repository, or a remote one (no need to clone)


#### Wheel

###### Usage → pyci pack wheel --help
<details closed>
<summary>Show</summary>

```text
Usage: pyci pack wheel [OPTIONS]

  Create a python wheel.

  see https://pythonwheels.com/

Options:
  --universal        Use this if your project supports both python2 and
                     python3 natively. This corresponds to the --universal
                     option of bdis_wheel
                     (https://wheel.readthedocs.io/en/stable/)
  --target-dir TEXT  The directory to create the wheel in. Defaults to the
                     current directory.
  --help             Show this message and exit.
```
</details>
<br>

Create a Python wheel using *bdist_wheel*.

#### Binary

###### Usage → pyci pack binary --help
<details closed>
<summary>Show</summary>

```text
Usage: pyci pack binary [OPTIONS]

  Create a binary executable.

  This command creates a self-contained binary executable for your project.
  The binary is platform dependent (architecture, os). For example, on a
  64bit MacOS the name will be: pyci-x86_64-Darwin

  The cool thing is that users can even run the executable on environments
  without python installed, since the binary packs a python version inside.

  Under the hood, pyci uses PyInstaller to create binary packages.

  see https://pythonhosted.org/PyInstaller/

Options:
  --name TEXT        The base name of the binary executable to be created.
                     Defaults to the top most python package of your project.
                     Note that the full name will be a suffixed with platform
                     specific info. This corresponds to the --name option used
                     by PyInstaller
                     (https://pythonhosted.org/PyInstaller/usage.html)
  --entrypoint TEXT  Path (relative to the repository root) of the file to be
                     used as the executable entry point. This corresponds to
                     the positional script argument passed to PyInstaller
                     (https://pythonhosted.org/PyInstaller/usage.html)
  --target-dir TEXT  The directory to create the binary in. Defaults to the
                     current directory.
  --help             Show this message and exit.
```
</details>
<br>
 

Create a binary executable file. This packaging format is extremely useful for distributing your 
CLI with minimum requirements. All users have to do is download a single file based on their 
platform. This also alleviates the need for an internet connection during installation since all 
dependencies are packaged inside. 

##### Good to know

Binary packages may greatly differ from the wheel distribution you are used to. That is, code 
that runs properly from within a wheel, may fail when its running from inside the installer. The 
main differences revolve around these issues:

- Accessing resource files

    When you package a wheel, it looks in the setup.py file for your package data declaration and 
    includes these files in the target wheel. [PyInstaller]()https://www.pyinstaller.org/ does not do
    this unfortunately, and you have to specify your package data in 
    a [spec](https://pyinstaller.readthedocs.io/en/v3.3.1/spec-files.html) file (similar to setup.py).  
    You can see an example in PyCI itself, which uses [this](pyci.spec#L11) spec file.

- Invoking python command line tools

    When you run within a wheel, you are running inside a standard python runtime environment. 
    Which  means you have access to all command lines that were installed to that environment. 
    However, the python runtime inside a PyInstaller package is not standard, and by default, 
    does not include the *bin* directory from the installation. This means you have to add it 
    yourself, again using a spec file. You can see an example in PyCI itself, which 
    uses [this](pyci.spec#L19) spec file.
    
    Also, the path to these command line tools will **not** be the same. Remember, you running 
    inside a compressed package that embeds the python library. When your command line is invoked,
    the PyInstaller boot loader extracts the package to a temp directory on your file system, and 
    using things like `sys.executable` will not produce the expected result. Instead, 
    PyInstaller provides an environment variable that points to that temp directory, so all your
    paths should take this into account.
     
    PyCI itself relies on this, you can see how I implemented path resolution 
    [here](https://github.com/iliapolo/pyci/blob/release/pyci/api/utils.py#L214).

- Script entrypoint

    When you install a package via pip, it looks for the entry-points declared in your setup.py,
    and dynamically creates python scripts to be used as the command line entry-point. 
    PyInstaller packages obviously dont do this, this means that your entrypoint file must be 
    invokable as a script. If you are using a framework like [click](http://click.pocoo.org/6/), 
    this wont be the case.
    
    You see an example [here](./pyci/shell/main.py#L223) of how to deal with such a case.


Basically, the main point is: **Run your tests on the binary package as well as the wheel.**
<br> 
Do not assume that what runs in the wheel will work. Exactly as you should not assume that what 
runs in editable mode will work in a wheel.

### Remote Github Commits

###### Usage → pyci github commit-file --help
<details closed>
<summary>Show</summary>

```text
Usage: pyci github commit-file [OPTIONS]

  Commit a file remotely.

Options:
  --branch TEXT    The branch to commit to.  [required]
  --path TEXT      Path to the file, relative to the repository root.
                   [required]
  --contents TEXT  The new file contents.  [required]
  --message TEXT   The commit message.  [required]
  --help           Show this message and exit.
```
</details>
<br>

This feature is kind of esoteric, but you might find it useful.
As part of the release process, PyCI performs a version bump to the setup.py file. 
I try to avoid running command other command line tools, so I implemented remote commit 
functionality using Github's REST API. 

## Installation

```bash
pip install py-ci
```

Or, since PyCI itself uses PyCI for releases, you can simply download the executable from the [releases](https://github.com/iliapolo/pyci/releases) page.


### Credentials

There are several credentials used by PyCI. All credentials are passed via environment variables,
never via the command line. All credentials can be prompted interactively in case the appropriate
env variable is not defined.

Every supported CI provider has a way of securely injecting environment variables to a job.

#### GitHub

PyCI uses a [Github Authentication Token](https://github.com/settings/tokens) for authentication. 
It is passed via the `GITHUB_ACCESS_TOKEN` env variable.

You must create the token with the necessary scopes for full control over your repository.

#### PyPI

PyCI needs your PyPI account credentials in order to upload wheels to PyPI. These credentials are:

- `TWINE_USERNAME`
- `TWINE_PASSWORD`


## Not planning to use PyCI?

No hard feelings, but I would really love to know why :)

- Are you missing a feature?
- Does it not fit with your project workflow?

If you could spare a minute or two to simply explain your choice as a comment in 
[this](https://github.com/iliapolo/pyci/issues/30) issue, that would be great, if not, that's ok 
too.

**Currently only supported for projects hosted on Github and running CI on either 
[Travis](https://travis-ci.org/), and or [Circle](https://circleci.com/), 
and or [Appveyor](https://www.appveyor.com/)**

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

- Turn your CLI into self-contained, python embedded, binary executables (Linux, Mac and Windows).
- Semantically bump version numbers
- Generate changelogs
- Create GitHub releases
- Upload wheels to PyPI

All in a CI agnostic way, with a command line tool you can run locally.

Would that be something you might be interested in?

If your answer is yes, or if you just got the reference, carry on 😎

## Show me the money

PyCI integrates with your existing CI providers and enables continuous release of 
the project. All you have to do is invoke the `pyci release` at the end of your CI workflow. It will detect the CI 
provider and perform a release of the associated commit.
 
 **Currently only supported for projects hosted on Github and running CI on either 
 [Travis](https://travis-ci.org/), [Circle](https://circleci.com/), 
 or [Appveyor](https://www.appveyor.com/)**


```text
    ___    _  _    ___     ___
   | _ \  | || |  / __|   |_ _|
   |  _/   \_, | | (__     | |
  _|_|_   _|__/   \___|   |___|
_| """ |_| """"|_|"""""|_|"""""|
"`-0-0-'"`-0-0-'"`-0-0-'"`-0-0-'

* Detected CI Provider: Travis-CI
→ Validating build https://travis-ci.org/iliapolo/pyci/builds/554632781
  * Build is not a PR... ✓
  * Build is not a TAG... ✓
  * Build branch is 'release'... ✓
* Validation passed
→ Validating commit
  * Commit references an issue... ✓
  * Issue is labeled with a release label... ✓
* Validation passed
→ Releasing branch 'release'
  → Generating changelog
    * Collecting commits
    → Analyzing 1 commits
      * 38 windows installer packages (#39) ✓
  * Changelog generation completed
  * Creating a GitHub release
  * Release created: https://github.com/iliapolo/pyci/releases/tag/0.7.0
  * Uploading changelog... ✓
  * Uploaded changelog to release 0.7.0
  * Bumping version to 0.7.0
  * Updating release branch...Branch release is now at 7e7919864a6258e93b3772fae56a372b3d8e30f7  ✓
  * Updating master branch...Branch master is now at 7e7919864a6258e93b3772fae56a372b3d8e30f7  ✓  
  → Closing issues
    * Closing issue number 38... ✓
* Successfully released: https://github.com/iliapolo/pyci/releases/tag/0.7.0
→ Creating packages
  * Packaging binary... ✓
  * Binary package created: /home/travis/build/iliapolo/pyci/py-ci-x86_64-Linux
  * Packaging wheel... ✓
  * Wheel package created: /home/travis/build/iliapolo/pyci/py_ci-0.7.0-py2.py3-none-any.whl
→ Uploading packages
  * Uploading py-ci-x86_64-Linux to release 0.7.0... ✓
  * Asset uploaded: https://github.com/iliapolo/pyci/releases/download/0.7.0/py-ci-x86_64-Linux
  * Uploading py_ci-0.7.0-py2.py3-none-any.whl to release 0.7.0... ✓
  * Asset uploaded: https://github.com/iliapolo/pyci/releases/download/0.7.0/py_ci-0.7.0-py2.py3-none-any.whl
  * Uploading py_ci-0.7.0-py2.py3-none-any.whl to PyPI... ✓
  * Wheel uploaded: https://pypi.org/manage/project/py-ci/release/0.7.0/
→ Hip Hip, Hurray! :). Your new version is released and ready to go.
  * Github: https://github.com/iliapolo/pyci/releases/tag/0.7.0
```

Once the command completes, navigate to the release on GitHub. You should see something like this:

[![release](./assets/release.png)](./assets/release.png)

Notice the assets that the release contains:

#### Wheel

PyCI attempts to create a wheel and publish it to PyPI. You can choose to skip the PyPI publishing part by using the 
`--no-wheel-publish` option. Since the wheel is still uploaded to GitHub, you can inspect and test it before 
actually publishing it. 

You can also choose to skip creating wheels altogether by using the `--no-wheel` option.

#### Binary

PyCI creates and uploads a platform dependent binary executable file. In this case, since the CI was executed from all 
three platform - we see 3 different files. Under the hood, these files are created using the [PyInstaller](https://www.pyinstaller.org/) project.

Note that these binaries are only created if PyCI detects that your project can be invoked as a command line tool (i
.e, its not just a library). To understand how exactly it does that, see [CLI Detection](./docs/how-it-works.md#cli-detection).

However, you can forcefully have PyCI ignore binary creation by using the `--no-binary` option.

#### NSIS 

In addition to a binary **executable**, PyCI will also create a binary **installer** for windows. The installer is 
simply a graphical installation wizard, which is the common way of installing software in windows environments (go 
figure). Under the hood, it is created using the [NSIS](https://nsis.sourceforge.io/Main_Page) project.

You can skip the installer creation by using the `--no-installer` option.


*All of these packages can be created independently of the release process by using the `pyci pack` command.* 

## Installation

```bash
pip install py-ci
```

Or, since PyCI itself uses PyCI for releases, you can simply download the executable from the [releases](https://github.com/iliapolo/pyci/releases) page.

## Credentials

There are several credentials used by PyCI. All credentials are passed via environment variables,
never via the command line. All credentials can be prompted interactively in case the appropriate
env variable is not defined.

Every supported CI provider has a way of securely injecting environment variables to a job.

### GitHub

PyCI uses a [Github Authentication Token](https://github.com/settings/tokens) for authentication. 
It is passed via the `GITHUB_ACCESS_TOKEN` env variable.

You must create the token with the necessary scopes for full control over your repository.

### PyPI

PyCI needs your PyPI account credentials in order to upload wheels to PyPI. These credentials are:

- `TWINE_USERNAME`
- `TWINE_PASSWORD`

## Tell me more

Like I mentioned before, PyCI is an opinionated tool, and as such, you should know what those opinions are:

- [I am PyCI - Hear Me Roar](./docs/hear-me-roar.md)

Its also worth understanding some key concepts and how exactly PyCI implements them.

- [I am PyCI - Be Gentle](./docs/be-gentle.md)


## Not planning to use PyCI?

No hard feelings, but I would really love to know why :)

- Are you missing a feature?
- Does it not fit with your project workflow?

If you could spare a minute or two to simply explain your choice as a comment in 
[this](https://github.com/iliapolo/pyci/issues/30) issue, that would be great, if not, that's ok 
too.

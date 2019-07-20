## Key Concepts

Lets take a look at some key concepts PyCI uses that are worth understanding.

### Issue detection

Many features of PyCI heavily rely on identifying which issue relates to which commit. For 
example, it uses issues to determine changelogs and version numbers. 

Issue detection is based on commit messages. There are two possible ways to reference an issue 
from a commit message:

- Directly specify the issue number using [*#*](https://help.github.com/articles/autolinked-references-and-urls/).
- Specify a PR using [*#*](https://help.github.com/articles/autolinked-references-and-urls/), and
reference the issue number in the PR description. Notice that when you merge a PR in GitHub, it 
automatically suggests a reference to the PR in the commit message.

If a commit does not reference any issue, it is considered a **Dangling commit**

### CLI detection

As we have seen, when PyCI releases a commit, it also tries to create a binary executable file 
and upload it as a release asset. 

In my opinion, if your project can be invoked as a CLI, it is very important that users are able 
to easily install and run it. While wheels and PyPI are great, they do not solve two important 
issues:

1. Installation in offline environments.

2. Execution in environments that dont have Python installed.  

A binary executable solves both these issues. PyCI uses [PyInstaller](https://www.pyinstaller.org/) to build these binaries.

How does PyCI determine whether or not the project is a CLI? Well, it looks for one of two files:

    - <package-name>.spec (see https://pythonhosted.org/PyInstaller/spec-files.html)
    - <package-name>/shell/main.py

    <package-name> is the name that appears in your setup.py file.

If any of these files exist, PyCI will attempt to create the executable. 
Note that these executables are platform dependent, this means that the executable is created for
the OS the command is running from.

If your project is a CLI, but your entrypoint is not one of these files, you can specify a custom 
entrypoint path. see [Usage](https://github.com/iliapolo/pyci#usage--pyci-release---help) 

### Labels

PyCI uses labels to determine two things:

* Commit categories

    Currently, only two labels are used: *feature* and *bug*. These labels determine the commit 
    category, which is later displayed in the release changelog. These labels are not mandatory, but 
    if you don't use them, your changelog will be less clear.

* Version numbers

    These labels are: *patch*, *minor*, *major*. In correspondence to the semantic versioning 
    scheme. Each label determines a specific version bump. These labels are **mandatory** because 
    otherwise PyCI has no ability to determine what the release version number should be.  


#### Getting Started

Here is what you do if you want to start releasing your project using PyCI.

1. Create the following labels in your GitHub repo:


    - feature
    - bug
    - patch
    - minor
    - major


2. Create an issue for the feature/bug you want to implement and label it accordingly.
3. Checkout from master to a feature branch.
4. Implement and create a PR referencing the issue in the body.
5. Merge the PR via Github. The commit message will by default reference the PR, make sure you 
dont remove that reference.
6. Wait for the release to complete.
7. Go to 3.

#### Triggering a release

Ideally, every push you make to the main branch should trigger a release. 

However, sometimes you just want to push a README fix, or maybe some refactoring. It doesn't
really make sense to trigger a release on every single commit. Also, releases should only be 
triggered if you push to the main branch, and not any other branch. For this reason, PyCI does 
some validation on the commit before it actually attempts to release it:

* Build validation 

    The build branch must be the main branch. That is, builds for tags, pr's, or branches that 
    differ from the main branch, will not trigger the release process. Instead, you will see 
    something like this:
    
    ```text
    * Detected CI Provider: CircleCI
    → Releasing branch 'release'
      → Validating build https://circleci.com/gh/iliapolo/pyci/421
        * Build is not a PR... ✓
        * Build is not a TAG... ✓
        * Build branch is 'release'... ✗
    * Not releasing: Commit e2a88d94c322536a3fcfbaf26d0d1fb2a31bbbe4 does not reference any issue
    ```

* Commit validation

    The commit must be associated with an issue, and the issue must be labeled with one of the 
    release labels.
    
    Any other commit, will trigger your CI, but **wont** trigger a release. Instead, you will see 
    something like:
    
    ```text
    * Detected CI Provider: CircleCI
    → Releasing branch 'release'
      → Validating build https://circleci.com/gh/iliapolo/pyci/421
        * Build is not a PR... ✓
        * Build is not a TAG... ✓
        * Build branch is 'release'... ✓
      → Validating commit
        * Commit references an issue... ✗
    * Not releasing: Commit e2a88d94c322536a3fcfbaf26d0d1fb2a31bbbe4 does not reference any issue
    ```

Notice that in such cases, the command exists successfully, so as to not fail the build.

#### Versioning a release

PyCI uses the [Semantic Versioning](https://semver.org/) scheme along with Github issues to 
automatically determine the version of the next release. 

The release command [detects](https://github.com/iliapolo/pyci#issue-detection) the issue that was 
referenced by the commit (that triggered the release) and fetches the issue labels. 
If the issue is labeled with the *patch* label, a *patch* bump is performed, and so forth...

Sometimes though, you might wind up in a situation where you have multiple un-released commits 
that reference a release issue. In such a case, PyCI will apply all corresponding bumps in order 
of issue creation.

A version bump is a commit made to the setup.py file, replacing the current version with the new
one. To determine the current version, PyCI runs the `python setup.py --version` command. Setting 
the new version is done a regex to replace the `'version='` keyword argument. This means that you 
cannot do any fancy things for this arg, like calculate stuff or invoke functions. Keep it simple
and let PyCI manipulate and determine version numbers. 

#### Concurrency

Many projects run concurrent CI jobs. These can be when testing different versions of Python, or 
running on multiple CI providers to cover all operating systems 
([AppVeyor](https://www.appveyor.com/) basically). For this reason, the command needs to be 
safe for concurrent executions. 

Every step in the command follows the *skip-existing* paradigm, so you don't have to worry about it.

**However**, there is one scenario where concurrent executions may cause a failure, when the 
executions run with **different** commits. 
It can happen if for example a pull request is merged into the release branch before the previous
pull request execution completed. 

At this point you might be thinking: "Hold on, this is exactly how we work now! I cant use this 
tool!". Well, if this is your scenario, you are most likely still running conventional release 
processes. That is:

1. Developers branch out from the main branch.
2. Feature branches are merged to the main branch via Github.
3. Repeat 1-2 for like a week or two.
4. Arbitrarily release the main branch.

If you want to stick to this workflow, PyCI is probably not the tool for you at the moment.

In order to use PyCI for release, you have to accept the following statement: *Every merged pull 
request triggers a release*. This is the core mindset of continuous release, and works best with 
the following workflow:  

1. Developers branch out from master to feature branches.
2. Feature branches are merged to the main branch via Github (usually 'develop' or 'release').
3. PyCI releases the main branch and updates master branch to the latest release.
4. Go to 1.

Another popular flow is to simply have the 'master' branch be the main branch.

Now you see that merging two PR's at the same time would be like running the conventional 
release process concurrently (which is usually a big no no).

Since PyCI makes the release process automatic and fast, there really is no reason not to 
wait for one merge to complete before merging another branch. It shouldn't delay your development
cycle, and is really just a matter of discipline.

Having said that, mistakes do happen, especially when more than one person can approve pull 
requests. So lets take a look at what happens in this scenario.

There are two ways it can develop:

- Second pr is merged before **any** of the previous pr's jobs got a chance to create the release.

    As part of the release process, PyCI pushes a commit on top of the release branch to bump the 
    version of setup.py. The parent of this commit is **always** the commit that triggered the 
    build. This is to make sure no other commits wind up in the release.
    Now imagine the last commit of the branch is the second pr, what will happen? When PyCI will 
    attempt to push, it will fail because it wont be a fast-forward.
    
    In this case, merging the second pr will actually cause all prior executions to fail. Now, 
    this might be ok, because the second pr itself will be released and include the first pr as 
    well. The only affect is that you will have a "gap" in your releases.
    
- Second pr is merged after **one** of the previous pr's jobs had already created the release.
    
    In this case, everything will work as expected since all other executions will detect the 
    release was already created and simply use it. Allowing for two release processes to take 
    place at the same time.

Obviously you cant know which will happen, which is why its best to avoid this scenario altogether.
But even if you cant, you should still be good to go.


### Changelog Generation

Changelog is generated by analyzing the commits made to the branch **after** the **previous** 
(not **last**!) release. Basically, here is how it works:

1. Fetch all commits prior (including) mine in descending order. 
2. Iterate over them and stop when we find a commit that points to a release.
3. All commits before we stop, should be a part of the changelog.

Note that this guarantees that you can generate a changelog for every commit, always, regardless 
of which versions are released.

Each commit is then categorized into one of: (see [Issue detection](https://github.com/iliapolo/pyci#issue-detection))

    - Feature
    - Bug
    - Issue
    - Dangling Commit 

If a *feature* (or *bug*) label if found, the commit is categorized as a feature (or bug). 
If these labels are not found, the commit is categorized as a regular issue. If the commit 
does not reference any issue, the commit is left "Dangling".


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

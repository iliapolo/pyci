## Genesis

A while back I had an idea for a small [cli](https://github.com/iliapolo/fileconfig) I wanted to 
build. When I finished the code, I started to think about the release process. 

Obviously, I needed to create and upload a wheel to PyPI. However, I had 3 additional requirements:

1. **Continuous**

    Can't tell you how many times I waited for features just because of a complex release process or 
    an arbitrary release date. 
    
    Not in my house. 
    
    If features/bugfixes are not dependent on each other, there should be no reason for them to 
    wait in the oven.
    
    I wanted to release a new version each time I finish implementing a certain issue, that is, each 
    time a PR is merged to the main branch. 
    This process had to be completely automated, no human involvement what so ever. 
    
    I think this is the right way to release software, and if you are not in a position to do so, it 
    probably means you're doing something wrong. Obviously this only applies to software that does 
    not require human testing. 

2. **Changelog generation**

    The release should include the relevant changelog based on Github issues. Each Github issue that 
    makes it to a release, should specify which release was it.
    
    Also, the release version number should be derived from the issues that were included in the 
    release. Each issue will have a label specifying which semantic version bump it should perform.
    (e.g an issue labeled with the 'patch' label will cause a patch bump, and so forth)

3. **Binary executable**

    Since the tool is supposed to kind of replace the linux *sed* utility (in a specific use case), I 
    wanted a very easy install method, and an ability to use it on environments that don't 
    even have python installed. This binary file should be uploaded to the Github release as a 
    release asset.

So, how was I supposed to achieve this? Well, there were 3 options:

- Explore CI providers like [CodeShip](https://codeship.com/) and [GitLab](https://gitlab.com). 

Honestly, I quickly gave up on this option since I was pretty sure the 'Binary executable' feature 
does not exist in any of them. Also, I was already using [Travis-CI](https://travis-ci.org/) and 
[Appveyor](https://www.appveyor.com/) for my tests, and really wanted to avoid having to learn 
and configure another tool.

I knew I wanted the release process to execute immediately after the tests pass, so I was looking
for a small script I can invoke via [tox](https://tox.readthedocs.io/en/latest/).  

- Use existing open source tools. 

I couldn't find any tool to answer all of my requirements. There were however a few tools that 
might have been somewhat helpful:

[pyreleaser](https://github.com/pyrelease/pyrelease)
[github-release](https://github.com/aktau/github-release)
[semantic-release](https://github.com/semantic-release/semantic-release)
[github-changelog](https://github.com/github-changelog-generator/github-changelog-generator)

Though these tools are in the same domain, they weren't enough. 

- Write my own! 

When I reached this point, I started to realize that this might be a useful tool not just for my 
project, but for any Python project hosted on Github. I believe most open source projects on 
Github use either [Travis-CI](https://travis-ci.org/) and/or [CircleCI](https://circleci.com/) 
and/or [Appveyor](https://www.appveyor.com/) to run their tests, so what if they 
could add a single command line to perform all these release related tasks? pretty cool.


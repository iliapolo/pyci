#############################################################################
# Copyright (c) 2018 Eli Polonsky. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#   * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   * See the License for the specific language governing permissions and
#   * limitations under the License.
#
#############################################################################

import semver
from github import Github
from github.GithubException import UnknownObjectException

from pyrelease.api import exceptions
from pyrelease.api import logger
from pyrelease.api import utils


class GithubReleaser(object):

    repo = None
    _logger = None

    def __init__(self, repo, access_token):

        # create a github release
        hub = Github(access_token)

        self._logger = logger.get_logger('pyrelease.releaser.GithubReleaser')

        self._logger.info('Fetching repo...')
        self.repo = hub.get_repo(repo)
        self._logger.info('Fetched repo: {0}'.format(self.repo.name))

    # pylint: disable=too-many-locals
    def release(self, branch_name):

        # first fetch everything we need from github

        self._logger.info('Fetching branch...')
        branch = self.repo.get_branch(branch=branch_name)
        self._logger.info('Fetched branch: {0}'.format(branch.name))

        self._logger.info('Fetching commit...')
        commit = self.repo.get_commit(sha=branch.commit.sha)
        self._logger.info('Fetched commit: {0}'.format(commit.sha))

        self._logger.info('Fetching tags...')
        tags = list(self.repo.get_tags())

        self._logger.info('Fetching releases...')
        releases = list(self.repo.get_releases())

        self._logger.info('Extracting latest release')
        last_release = self._get_latest_release(releases)
        self._logger.info('Extracted latest release: {0}'.format(last_release))

        tag = [t for t in list(tags) if t.name == last_release][0]

        if commit.sha == tag.commit.sha:
            self._logger.info('The latest commit of this branch is already released: {0}'
                              .format(last_release))
            return

        self._logger.info('Fetching pull request')
        pull_request = self.repo.get_pull(
            number=utils.get_pull_request_number(commit.commit.message))
        self._logger.info('Fetched pull request: {0}'.format(pull_request.title))

        self._logger.info('Fetching issue...')
        issue = self.repo.get_issue(
            number=int(utils.get_issue_number(pull_request.body)))
        self._logger.info('Fetched issue: {0}'.format(issue.number))

        self._logger.info('Fetching issue labels...')
        labels = list(issue.get_labels())
        self._logger.info('Fetched labels: {0}'.format(','.join([label.name for label in labels])))

        semantic_version = self._get_next_release(last_release, labels)
        if semantic_version == last_release:
            self._logger.info('The latest commit corresponds to an issue that is not marked as a '
                              'release issue. Not releasing.')
            return
        self._logger.info('Next version will be: {0}'.format(semantic_version))

        self._logger.info('Fetching changelog...')
        changelog = self._get_changelog(releases=releases, tags=tags, branch=branch)

        self._logger.info('Fetching master ref...')
        master = self.repo.get_git_ref('heads/master')
        self._logger.info('Fetched ref: {0}'.format(master.ref))

        self._logger.info('Creating Github Release...')
        self.repo.create_git_release(
            tag=semantic_version,
            target_commitish=branch_name,
            name=semantic_version,
            message=changelog,
            draft=False,
            prerelease=False,
        )
        self._logger.info('Successfully created release: {0}'.format(semantic_version))

        self._logger.info('Updating master branch')
        master.edit(sha=branch.commit.sha, force=True)
        self._logger.info('Successfully updated master branch to: {0}'.format(branch.commit.sha))

        try:
            pull_request_ref = self.repo.get_git_ref('heads/{0}'.format(pull_request.head.ref))
            self._logger.info('Deleting ref: {0}'.format(pull_request_ref.ref))
            pull_request_ref.delete()
        except UnknownObjectException:
            # this is ok, the branch doesn't necessarily have to be there.
            # it might have been deleted when the pull request was merged
            pass

    def delete(self, release):

        releases = [r for r in list(self.repo.get_releases()) if r.title == release]

        if not releases:
            raise exceptions.ReleaseNotFoundException(release=release)
        if len(releases) > 1:
            raise exceptions.MultipleReleasesFoundException(release=release,
                                                            how_many=len(releases))

        release = releases[0]
        self._logger.info('Deleting release: {0}'.format(release.title))
        release.delete_release()

        refs = [ref for ref in list(self.repo.get_git_refs()) if ref.ref == release.title]

        if not refs:
            raise exceptions.RefNotFoundException(ref=release.title)
        if len(refs) > 1:
            raise exceptions.MultipleRefsFoundException(ref=release.title, how_many=len(refs))

        ref = refs[0]
        self._logger.info('Deleting ref: {0}'.format(ref.ref))
        ref.delete()

    @staticmethod
    def _get_latest_release(releases):

        if not releases:
            return None

        versions = [release.title for release in releases]

        return sorted(versions, cmp=lambda t1, t2: semver.compare(t2, t1))[0]

    def _get_issue_from_commit(self, commit):

        commit_message = commit.commit.message

        pull_request_number = int(utils.get_pull_request_number(commit_message))

        pull_request = self.repo.get_pull(number=pull_request_number)

        issue_number = utils.get_issue_number(pull_request.body)

        return self.repo.get_issue(number=int(issue_number))

    def _get_changelog(self, releases, tags, branch):

        last_release = self._get_latest_release(releases)

        release_tags = [t for t in list(tags) if t.name == last_release]
        if not release_tags:
            raise exceptions.TagNotFoundException(tag=last_release, release=last_release)

        # it cannot have multiple elements because there cannot be
        # to tags with the same name
        tag = release_tags[0]

        commits = list(self.repo.get_commits(sha=branch.name,
                                             since=tag.commit.commit.committer.date))

        commits = [com for com in commits if com.sha != tag.commit.sha]

        features = []
        bug_fixes = []

        for commit in commits:
            issue = self._get_issue_from_commit(commit)

            labels = [label.name for label in list(issue.get_labels())]

            if 'feature' in labels:
                features.append('- {0} ([Issue]({1}))'.format(issue.title, issue.html_url))

            if 'bug' in labels:
                bug_fixes.append('- {0} ([Issue]({1}))'.format(issue.title, issue.html_url))

        features_string = '\n'.join(features)
        bug_fixes_string = '\n'.join(bug_fixes)

        return '''*Changes*

**New Features:**

{0}

**Bug Fixes:**

{1}        
        '''.format(features_string, bug_fixes_string)

    @staticmethod
    def _get_next_release(last_release, labels):

        if last_release is None:
            return '1.0.0'

        label_names = [label.name for label in labels]

        semantic_version = last_release.split('.')

        micro = int(semantic_version[2])
        minor = int(semantic_version[1])
        major = int(semantic_version[0])

        if 'micro' in label_names:
            micro = micro + 1

        if 'minor' in label_names:
            micro = 0
            minor = minor + 1

        if 'major' in label_names:
            micro = 0
            minor = 0
            major = major + 1

        return '{0}.{1}.{2}'.format(major, minor, micro)

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
import os

import semver
from github import Github
from github.GithubException import UnknownObjectException

from pyci.api import exceptions
from pyci.api import logger
from pyci.api import utils


class GithubReleaser(object):

    repo = None
    _logger = None

    def __init__(self, repo, access_token):

        # create a github release
        hub = Github(access_token)

        self._logger = logger.get_logger('api.releaser.GithubReleaser')

        self._logger.debug('Fetching repo...')
        self.repo = hub.get_repo(repo)
        self._logger.debug('Fetched repo: {0}'.format(self.repo.name))

    # pylint: disable=too-many-locals,too-many-statements
    def release(self, branch_name):

        # first fetch everything we need from github

        self._logger.debug('Fetching branch...')
        branch = self.repo.get_branch(branch=branch_name)
        self._logger.debug('Fetched branch: {0}'.format(branch.name))

        self._logger.debug('Fetching commit...')
        commit = self.repo.get_commit(sha=branch.commit.sha)
        self._logger.debug('Fetched commit: {0}'.format(commit.sha))

        self._logger.debug('Fetching tags...')
        tags = list(self.repo.get_tags())

        self._logger.debug('Fetching releases...')
        releases = list(self.repo.get_releases())

        self._logger.debug('Extracting latest release')
        last_release = self._get_latest_release(releases)
        self._logger.debug('Extracted latest release: {0}'.format(last_release))

        if last_release:
            tag = [t for t in list(tags) if t.name == last_release][0]
            # figure out if we really need to release
            if commit.sha == tag.commit.sha:
                self._logger.debug('The latest commit of this branch is already released: {0}'
                                   .format(last_release))
                return None

        self._logger.debug('Fetching pull request')
        pull_request = self._get_pull_request(commit)
        if pull_request is None:
            self._logger.debug('Commit is not related to any pull request, not releasing...')
            return None
        self._logger.debug('Fetched pull request: {0}'.format(pull_request.title))

        self._logger.debug('Fetching issue...')
        issue = self._get_issue_from_pull_request(pull_request)
        if issue is None:
            self._logger.debug('Pull request {0} is not related to any issue, '
                               'not releasing...'.format(pull_request.number))
            return None
        self._logger.debug('Fetched issue: {0}'.format(issue.number))

        self._logger.debug('Fetching issue labels...')
        labels = list(issue.get_labels())
        self._logger.debug('Fetched labels: {0}'.format(','.join([label.name for label in labels])))

        semantic_version = self._get_next_release(last_release, labels)
        if semantic_version == last_release:
            self._logger.debug('The latest commit corresponds to an issue that is not marked as a '
                               'release issue. not releasing....')
            return None
        self._logger.debug('Next version will be: {0}'.format(semantic_version))

        self._logger.debug('Fetching changelog...')
        changelog = self._get_changelog(releases=releases, tags=tags, branch=branch)

        self._logger.debug('Fetching master ref...')
        master = self.repo.get_git_ref('heads/master')
        self._logger.debug('Fetched ref: {0}'.format(master.ref))

        self._logger.debug('Creating Github Release...')
        self.repo.create_git_release(
            tag=semantic_version,
            target_commitish=branch_name,
            name=semantic_version,
            message=changelog,
            draft=False,
            prerelease=False
        )
        self._logger.debug('Successfully created release: {0}'.format(semantic_version))

        self._logger.debug('Updating master branch')
        master.edit(sha=branch.commit.sha, force=True)
        self._logger.debug('Successfully updated master branch to: {0}'.format(branch.commit.sha))

        try:
            pull_request_ref = self.repo.get_git_ref('heads/{0}'.format(pull_request.head.ref))
            self._logger.debug('Deleting ref: {0}'.format(pull_request_ref.ref))
            pull_request_ref.delete()
        except UnknownObjectException:
            # this is ok, the branch doesn't necessarily have to be there.
            # it might have been deleted when the pull request was merged
            pass

        return semantic_version

    def upload(self, asset, release):

        release = self.repo.get_release(id=release)
        release.upload_asset(path=asset, content_type='application/octet-stream')

        return 'https://github.com/{0}/releases/download/{1}/{2}'\
            .format(self.repo.name, release.title, os.path.basename(asset))

    def delete(self, version):

        releases = [r for r in list(self.repo.get_releases()) if r.title == version]

        if len(releases) > 1:
            raise exceptions.MultipleReleasesFoundException(release=version,
                                                            how_many=len(releases))

        if releases:
            release = releases[0]
            self._logger.debug('Deleting release: {0}'.format(version))
            release.delete_release()
        else:
            self._logger.debug('Release {0} not found, skipping...'.format(version))

        refs = [ref for ref in list(self.repo.get_git_refs()) if ref.ref == 'refs/tags/{0}'
                .format(version)]

        if len(refs) > 1:
            raise exceptions.MultipleRefsFoundException(ref=version, how_many=len(refs))

        if refs:
            ref = refs[0]
            self._logger.debug('Deleting ref: {0}'.format(ref.ref))
            ref.delete()
        else:
            self._logger.debug('Tag {0} not found, skipping...'.format(version))

    @staticmethod
    def _get_latest_release(releases):

        if not releases:
            return None

        versions = [release.title for release in releases]

        return sorted(versions, cmp=lambda t1, t2: semver.compare(t2, t1))[0]

    def _get_issue_from_commit(self, commit):

        pull_request = self._get_pull_request(commit)
        if pull_request is None:
            return None

        return self._get_issue_from_pull_request(pull_request)

    def _get_issue_from_pull_request(self, pull_request):

        issue_number = utils.get_issue_number(pull_request.body)
        if issue_number is None:
            return None
        return self.repo.get_issue(number=int(issue_number))

    def _get_pull_request(self, commit):

        pr_number = utils.get_pull_request_number(commit.commit.message)
        if pr_number is None:
            return None

        return self.repo.get_pull(number=pr_number)

    def _get_changelog(self, releases, tags, branch):

        last_release = self._get_latest_release(releases)

        since = None
        tag = None
        if last_release:
            release_tags = [t for t in list(tags) if t.name == last_release]
            if not release_tags:
                raise exceptions.TagNotFoundException(tag=last_release, release=last_release)

            # it cannot have multiple elements because there cannot be
            # to tags with the same name
            tag = release_tags[0]
            since = tag.commit.commit.committer.date

        if since:
            commits = list(self.repo.get_commits(sha=branch.name, since=since))
        else:
            commits = list(self.repo.get_commits(sha=branch.name))

        commits = [com for com in commits if tag is None or com.sha != tag.commit.sha]

        features = set()
        bug_fixes = set()

        for commit in commits:

            self._logger.debug('Fetching issue for commit: {0}'.format(commit.commit.message))
            issue = self._get_issue_from_commit(commit)

            if issue is None:
                continue

            labels = [label.name for label in list(issue.get_labels())]

            if 'feature' in labels:
                features.add('- {0} ([Issue]({1}))'.format(issue.title, issue.html_url))

            if 'bug' in labels:
                bug_fixes.add('- {0} ([Issue]({1}))'.format(issue.title, issue.html_url))

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
            return '0.0.1'

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

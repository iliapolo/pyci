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

import re

import semver
from github import Github
from github.GithubException import UnknownObjectException

from pyrelease.api import exceptions
from pyrelease.api import logger


class GithubReleaser(object):

    repo = None
    _logger = None

    def __init__(self, repo, access_token):

        # create a github release
        hub = Github(access_token)

        self.repo = hub.get_repo(repo)
        self._logger = logger.get_logger('pyrelease.releaser.GithubReleaser')

    def release(self, branch):

        self._logger.info('Fetching latest version...')
        last_release = self._get_latest_release()
        self._logger.info('Fetched latest version: {0}'.format(last_release))

        self._logger.info('Fetching issue...')
        issue = self._get_issue(branch)
        self._logger.info('Fetched issue associated with latest commit on branch {0}: '
                          'Issue number {1}'.format(branch, issue.number))

        labels = map(lambda label: label.name, list(issue.get_labels()))

        semantic_version = self._get_next_release(last_release, labels)
        if semantic_version == last_release:
            self._logger.info('The latest commit corresponds to an issue that is not marked as a '
                              'release issue. Not releasing.')
            return
        self._logger.info('Next version will be: {0}'.format(semantic_version))

        message = '*Changes*'

        if 'feature' in labels:
            message = message + '\n\n' + '**New Feature:**\n\n- {0} ([Issue]({1}))'\
                .format(issue.title, issue.html_url)

        if 'bug' in labels:
            message = message + '\n\n' + '**Bug Fix:**\n\n- {0} ([Issue]({1}))' \
                .format(issue.title, issue.html_url)

        self._logger.info('Creating Github Release...')
        self.repo.create_git_release(
            tag=semantic_version,
            target_commitish=branch,
            name=semantic_version,
            message=message,
            draft=False,
            prerelease=False,
        )
        self._logger.info('Successfully created release: {0}'.format(semantic_version))

        self._logger.info('Updating master branch')
        master = self.repo.get_git_ref('heads/master')
        sha = self.repo.get_branch(branch=branch).commit.sha
        master.edit(sha=sha)
        self._logger.info('Successfully updated master branch to: {0}'.format(sha))

        pull_request = self._get_pull_request(branch)
        try:
            pull_request_ref = self.repo.get_git_ref('heads/{0}'.format(pull_request.head.ref))
            self._logger.info('Deleting ref: {0}'.format(pull_request_ref.ref))
            pull_request_ref.delete()
        except UnknownObjectException:
            # this is ok, the branch doesn't necessarily have to be there.
            # it might have been deleted when the pull request was merged
            pass

    def delete(self, release):

        releases = filter(lambda r: r.title == release, list(self.repo.get_releases()))
        if not releases:
            raise exceptions.ReleaseNotFoundException(release=release)
        if len(releases) > 1:
            raise exceptions.MultipleReleasesFoundException(release=release,
                                                            how_many=len(releases))

        release = releases[0]
        self._logger.info('Deleting release: {0}'.format(release.title))
        release.delete_release()

        refs = filter(lambda r: release.title in r.ref, list(self.repo.get_git_refs()))

        if not refs:
            raise exceptions.RefNotFoundException(ref=release.title)
        if len(refs) > 1:
            raise exceptions.MultipleRefsFoundException(ref=release.title, how_many=len(refs))

        ref = refs[0]
        self._logger.info('Deleting ref: {0}'.format(ref.ref))
        ref.delete()

    def _get_latest_release(self):

        releases = [release.title for release in list(self.repo.get_releases())]

        if not releases:
            return None
        return sorted(releases, cmp=lambda t1, t2: semver.compare(t2, t1))[0]

    def _get_issue(self, branch):

        pull_request = self._get_pull_request(branch)

        issue_number = self._get_issue_number(pull_request.body)

        return self.repo.get_issue(number=int(issue_number))

    def _get_pull_request(self, branch):

        sha = self.repo.get_branch(branch=branch).commit.sha

        commit_message = self.repo.get_commit(sha=sha).commit.message

        pr = int(self._get_pull_request_number(commit_message))

        return self.repo.get_pull(number=pr)

    def _get_issue_from_commit(self, commit):

        commit_message = commit.commit.message

        pull_request_number = int(self._get_pull_request_number(commit_message))

        pull_request = self.repo.get_pull(number=pull_request_number)

        issue_number = self._get_issue_number(pull_request.body)

        return self.repo.get_issue(number=int(issue_number))

    def _get_changelog(self, branch):

        last_release = self._get_latest_release()

        # TODO add validations, the tag might not exists...?
        tag = filter(lambda t: last_release == t.name, list(self.repo.get_tags()))[0]

        last_commit_sha = self.repo.get_branch(branch=branch).commit.sha

        commits = list(self.repo.get_commits(sha=branch, since=tag.commit.commit.committer.date))

        if len(commits) == 1 and commits[0].commit.sha == last_commit_sha:
            self._logger.info('The last commit of this branch was already released. no change log')
            return None
        for commit in commits[1:]:
            issue = self._get_issue_from_commit(commit)

            labels = map(lambda label: label.name, list(issue.get_labels()))

            message = '*Changes*'

            if 'feature' in labels:
                message = message + '\n\n' + '**New Feature:**\n\n- {0} ([Issue]({1}))' \
                    .format(issue.title, issue.html_url)

            if 'bug' in labels:
                message = message + '\n\n' + '**Bug Fix:**\n\n- {0} ([Issue]({1}))' \
                    .format(issue.title, issue.html_url)

            print message

    @staticmethod
    def _get_next_release(last_release, labels):

        if last_release is None:
            return '1.0.0'

        semantic_version = last_release.split('.')

        micro = int(semantic_version[2])
        minor = int(semantic_version[1])
        major = int(semantic_version[0])

        if 'micro' in labels:
            micro = micro + 1

        if 'minor' in labels:
            micro = 0
            minor = minor + 1

        if 'major' in labels:
            micro = 0
            minor = 0
            major = major + 1

        return '{0}.{1}.{2}'.format(major, minor, micro)

    @staticmethod
    def _get_issue_number(pr_body):

        p = re.compile('.* ?resolve #(\d+) ')
        match = p.match(pr_body)

        if match:
            return match.group(1)
        else:
            raise exceptions.InvalidPullRequestBody(body=pr_body)

    @staticmethod
    def _get_pull_request_number(commit_message):

        p = re.compile('.* ?\(#(\d+)\)')
        match = p.match(commit_message)
        if match:
            return match.group(1)
        else:
            raise exceptions.InvalidCommitMessage(commit_message=commit_message)

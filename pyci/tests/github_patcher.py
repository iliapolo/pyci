# -*- coding: utf-8 -*-

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

import copy
import json
import os
import sys
import types

import six
from github import Requester

python2 = sys.hexversion < 0x03000000
at_least_python3 = sys.hexversion >= 0x03000000


class FakeHttpResponse(object):
    def __init__(self, status, headers, output):
        self.status = status
        self._headers = headers
        self._output = output

    def getheaders(self):
        return self._headers

    def read(self):
        return self._output


class RecordingConnection(object):  # pragma no cover

    _real_connection = None

    def __init__(self, protocol, host, port, *args, **kwargs):
        self._recorder = None
        self._protocol = protocol
        self._host = host
        self._port = str(port)
        # pylint: disable=not-callable
        self._cnx = self._real_connection(host, port, *args, **kwargs)

    def set_recorder(self, recorder):
        self._recorder = recorder

    def request(self, verb, url, inp, headers):
        self._cnx.request(verb, url, inp, headers)

        sanitized_headers = copy.deepcopy(headers)
        sanitized_headers['Authorization'] = 'token private_token_removed'

        self._record(self._protocol)
        self._record(verb)
        self._record(self._host)
        self._record(self._port)
        self._record(url)
        self._record(str(sanitized_headers))
        self._record(str(inp).replace('\n', '').replace('\r', ''))

    def getresponse(self):

        try:
            res = self._cnx.getresponse()
            status = res.status
            headers = res.getheaders()
            if isinstance(headers, types.GeneratorType):
                headers = list(headers)
            output = res.read()

            self._record(str(status))
            self._record(str(headers))
            self._record(str(output))

            return FakeHttpResponse(status, headers, output)

        except BaseException as e:
            self._record(str(e))
            raise

    def close(self):
        self._record("")
        return self._cnx.close()

    def _record(self, line):
        self._recorder.record(line)


class ReplayingConnection(object):

    def __init__(self, protocol, host, port, token, *_, **__):
        self._replayer = None
        self._protocol = protocol
        self._host = host
        self._port = str(port)
        self._token = token

    def set_replayer(self, replayer):
        self._replayer = replayer

    def request(self, verb, url, inp, headers):

        assert self._protocol == self._replay()
        assert verb == self._replay()
        assert self._host == self._replay()
        assert self._port == self._replay()
        assert self._split_url(url) == self._split_url(self._replay())

        # pylint: disable=eval-used
        desanitized_headers = eval(self._replay())
        desanitized_headers['Authorization'] = 'token {}'.format(self._token)
        if 'Content-Length' in desanitized_headers:
            # the content-length during the recording does not necessarily
            # match it during replay, this is ok.
            desanitized_headers['Content-Length'] = headers['Content-Length']

        assert headers == desanitized_headers
        expected_input = self._replay()
        if isinstance(inp, six.string_types):
            if inp.startswith("{"):
                actual = json.loads(inp.replace('\n', '').replace('\r', ''))
                expected = json.loads(expected_input)
                assert actual == expected
            elif python2:
                # pylint: disable=fixme
                # TODO Test in all cases, including Python 3.4+
                # In Python 3.4+, dicts are not output in the same order as in Python 2.7.
                # So, form-data encoding is not deterministic and is difficult to test.
                assert inp.replace('\n', '').replace('\r', '') == expected_input
        else:
            # for non-string input (e.g. upload asset), let it pass.
            pass

    @staticmethod
    def _split_url(url):
        splited_url = url.split("?")
        if len(splited_url) == 1:
            return splited_url
        expected_number_of_parts = 2
        assert expected_number_of_parts == len(splited_url)
        base, qs = splited_url
        return base, sorted(qs.split("&"))

    def getresponse(self):
        status = int(self._replay())
        # pylint: disable=eval-used
        headers = eval(self._replay())
        output = self._replay()

        return FakeHttpResponse(status, headers, output)

    def close(self):
        self._replay()

    def _replay(self):
        replayed = self._replayer.replay()
        if 'Connection aborted' in replayed:
            raise IOError()
        return replayed


class RecordingHttpConnection(RecordingConnection):  # pragma no cover

    _real_connection = Requester.HTTPRequestsConnectionClass

    def __init__(self, *args, **kwargs):
        RecordingConnection.__init__(self, "http", *args, **kwargs)


class RecordingHttpsConnection(RecordingConnection):  # pragma no cover

    _real_connection = Requester.HTTPSRequestsConnectionClass

    def __init__(self, *args, **kwargs):
        RecordingConnection.__init__(self, "https", *args, **kwargs)


class ReplayingHttpConnection(ReplayingConnection):

    def __init__(self, *args, **kwargs):
        ReplayingConnection.__init__(self, "http", *args, **kwargs)


class ReplayingHttpsConnection(ReplayingConnection):

    def __init__(self, *args, **kwargs):
        ReplayingConnection.__init__(self, "https", *args, **kwargs)


class Recorder(object):

    def __init__(self):
        self._file = None

    def update_file(self, f):
        if os.path.exists(f):
            # override the previous recording
            os.remove(f)
        self._file = f

    def record(self, line):

        with open(self._file, 'ab') as stream:
            stream.write(line + os.linesep)


class Replayer(object):

    def __init__(self):
        self._file_name = None
        self._file = None

    def update_file(self, f):
        self._file_name = f
        if self._file and not self._file.closed:
            self._file.close()
            self._file = None

        if os.path.exists(f):
            self._file = open(f, mode='rb')

    def replay(self):

        if self._file is None:
            raise RuntimeError('{} does not exist'.format(self._file_name))

        if at_least_python3:
            return self._file.readline().decode("utf-8").strip()
        return self._file.readline().strip()


class GithubConnectionPatcher(object):

    def __init__(self, record=False, token=None):
        self.file = None
        self.record_mode = record
        self.token = token
        self.recorder = Recorder()
        self.replayer = Replayer()

    def patch(self):

        recorder = self.recorder
        replayer = self.replayer

        if self.record_mode:  # pragma no cover

            def _for_protocol(protocol):

                def _connection(_, *args, **kwargs):

                    if protocol == 'http':
                        connection = RecordingHttpConnection(*args, **kwargs)
                    else:
                        connection = RecordingHttpsConnection(*args, **kwargs)

                    connection.set_recorder(recorder)
                    return connection

                return _connection

            Requester.Requester.injectConnectionClasses(_for_protocol('http'),
                                                        _for_protocol('https'))

        else:

            def _for_protocol(protocol):

                def _connection(_, *args, **kwargs):

                    kwargs['token'] = self.token

                    if protocol == 'http':
                        connection = ReplayingHttpConnection(*args, **kwargs)
                    else:
                        connection = ReplayingHttpsConnection(*args, **kwargs)

                    connection.set_replayer(replayer)
                    return connection

                return _connection

            Requester.Requester.injectConnectionClasses(_for_protocol('http'),
                                                        _for_protocol('https'))

    def update(self, data_file_path):

        if self.record_mode:
            self.recorder.update_file(data_file_path)
        else:
            self.replayer.update_file(data_file_path)

    @staticmethod
    def reset():
        Requester.Requester.resetConnectionClasses()

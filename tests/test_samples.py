"""
Smoke test using the samples.
"""

import unittest
import os
import six
import sys
import time
import subprocess

from requests import post

import flask_ask


launch = {
  "version": "1.0",
  "session": {
    "new": True,
    "sessionId": "amzn1.echo-api.session.0000000-0000-0000-0000-00000000000",
    "application": {
      "applicationId": "fake-application-id"
    },
    "attributes": {},
    "user": {
      "userId": "amzn1.account.AM3B00000000000000000000000"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "fake-application-id"
      },
      "user": {
        "userId": "amzn1.account.AM3B00000000000000000000000"
      },
      "device": {
        "supportedInterfaces": {
          "AudioPlayer": {}
        }
      }
    },
    "AudioPlayer": {
      "offsetInMilliseconds": 0,
      "playerActivity": "IDLE"
    }
  },
  "request": {
    "type": "LaunchRequest",
    "requestId": "string",
    "timestamp": "string",
    "locale": "string",
    "intent": {
      "name": "TestPlay",
      "slots": {
        }
      }
    }
}


project_root = os.path.abspath(os.path.join(flask_ask.__file__, '../..'))


@unittest.skipIf(six.PY2, "Not yet supported on Python 2.x")
class SmokeTestUsingSamples(unittest.TestCase):
    """ Try launching each sample and sending some requests to them. """

    def setUp(self):
        self.python = sys.executable
        self.env = {'PYTHONPATH': project_root,
                    'ASK_VERIFY_REQUESTS': 'false'}
        if os.name == 'nt':
            self.env['SYSTEMROOT'] = os.getenv('SYSTEMROOT')
            self.env['PATH'] = os.getenv('PATH')

    def _launch(self, sample):
        prefix = os.path.join(project_root, 'samples/')
        path = prefix + sample
        process = subprocess.Popen([self.python, path], env=self.env)
        time.sleep(1)
        self.assertIsNone(process.poll(),
                          msg='Poll should work,'
                          'otherwise we failed to launch')
        self.process = process

    def _post(self, route='/', data={}):
        url = 'http://127.0.0.1:5000' + str(route)
        print('POSTing to %s' % url)
        response = post(url, json=data)
        self.assertEqual(200, response.status_code)
        return response

    @staticmethod
    def _get_text(http_response):
        data = http_response.json()
        return data.get('response', {})\
                   .get('outputSpeech', {})\
                   .get('text', None)

    @staticmethod
    def _get_reprompt(http_response):
        data = http_response.json()
        return data.get('response', {})\
                   .get('reprompt', {})\
                   .get('outputSpeech', {})\
                   .get('text', None)

    def tearDown(self):
        try:
            self.process.terminate()
            self.process.communicate(timeout=1)
        except Exception as e:
            try:
                print('[%s]...trying to kill.' % str(e))
                self.process.kill()
                self.process.communicate(timeout=1)
            except Exception as e:
                print('Error killing test python process: %s' % str(e))
                print('*** it is recommended you manually kill with PID %s',
                      self.process.pid)

    def test_helloworld(self):
        """ Test the HelloWorld sample project """
        self._launch('helloworld/helloworld.py')
        response = self._post(data=launch)
        self.assertTrue('hello' in self._get_text(response))

    def test_session_sample(self):
        """ Test the Session sample project """
        self._launch('session/session.py')
        response = self._post(data=launch)
        self.assertTrue('favorite color' in self._get_text(response))

    def test_audio_simple_demo(self):
        """ Test the SimpleDemo Audio sample project """
        self._launch('audio/simple_demo/ask_audio.py')
        response = self._post(data=launch)
        self.assertTrue('audio example' in self._get_text(response))

    def test_audio_playlist_demo(self):
        """ Test the Playlist Audio sample project """
        self._launch('audio/playlist_demo/playlist.py')
        response = self._post(data=launch)
        self.assertTrue('playlist' in self._get_text(response))

    def test_blueprints_demo(self):
        """ Test the sample project using Flask Blueprints """
        self._launch('blueprint_demo/demo.py')
        response = self._post(route='/ask', data=launch)
        self.assertTrue('hello' in self._get_text(response))

    def test_history_buff(self):
        """ Test the History Buff sample """
        self._launch('historybuff/historybuff.py')
        response = self._post(data=launch)
        self.assertTrue('History buff' in self._get_text(response))

    def test_spacegeek(self):
        """ Test the Spacegeek sample """
        self._launch('spacegeek/spacegeek.py')
        response = self._post(data=launch)
        # response is random
        self.assertTrue(len(self._get_text(response)) > 1)

    def test_tidepooler(self):
        """ Test the Tide Pooler sample """
        self._launch('tidepooler/tidepooler.py')
        response = self._post(data=launch)
        self.assertTrue('Which city' in self._get_reprompt(response))

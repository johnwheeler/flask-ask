"""
Smoke test using the samples.
"""

import unittest
import os
import sys
import time
import subprocess
from signal import SIGINT
from requests import post


samples = {
    'helloworld/helloworld.py': ['HelloWorldIntent', 'AMAZON.HelpIntent'],
}

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



flask_ask_path = os.path.abspath(os.path.join(__file__, '../..'))


class SmokeTestUsingSamples(unittest.TestCase):
    """
    Try launching each sample and sending some requests to them.
    """

    def setUp(self):
        self.python = sys.executable
        self.env = {'PYTHONPATH': flask_ask_path, 'ASK_VERIFY_REQUESTS': 'false'}

    def _launch(self, path):
        return subprocess.Popen([self.python, path], env=self.env)

    def test_helloworld(self):
        try:
            process = self._launch('/Users/dave/src/vpr/flask-ask/samples/helloworld/helloworld.py')
            self.assertIsNone(process.poll())
            time.sleep(3)
            response = post('http://127.0.0.1:5000', json=launch)
            print('response: %s' % str(response))
            process.send_signal(SIGINT)
            process.wait(timeout=5)
            self.assertIsNotNone(process.returncode)

            
        finally:
            try:
                process.kill()
            except Exception as e:
                pass

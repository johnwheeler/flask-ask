import unittest
import json
from flask_ask import Ask, audio
from flask import Flask


play_request = {
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
    "type": "IntentRequest",
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


class AudioIntegrationTests(unittest.TestCase):
    """ Integration tests of the Audio Directives """

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['ASK_VERIFY_REQUESTS'] = False
        self.ask = Ask(app=self.app, route='/ask')
        self.client = self.app.test_client()
        self.stream_url = 'https://fakestream'

        @self.ask.intent('TestPlay')
        def play():
            return audio('playing').play(self.stream_url)

    def tearDown(self):
        pass

    def test_play_intent(self):
        """ Test to see if we can properly play a stream """
        response = self.client.post('/ask', data=json.dumps(play_request))
        self.assertEqual(200, response.status_code)

        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual('playing',
                         data['response']['outputSpeech']['text'])

        directive = data['response']['directives'][0]
        self.assertEqual('AudioPlayer.Play', directive['type'])

        stream = directive['audioItem']['stream']
        self.assertIsNotNone(stream['token'])
        self.assertEqual(self.stream_url, stream['url'])
        self.assertEqual(0, stream['offsetInMilliseconds'])


if __name__ == '__main__':
    unittest.main()

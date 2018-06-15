import unittest
import json
import uuid

from flask_ask import Ask, statement
from flask import Flask


play_request = {
  "version": "1.0",
  "session": {
    "new": False,
    "sessionId": "amzn1.echo-api.session.f6ebc0ba-9d7a-4c3f-b056-b6c3f9da0713",
    "application": {
      "applicationId": "amzn1.ask.skill.26338c44-65da-4d58-aa75-c86b21271eb7"
    },
    "user": {
      "userId": "amzn1.ask.account.AHR7KBC3MFCX7LYT6HJBGDLIGQUU3FLANWCZ",
    }
  },
  "context": {
    "AudioPlayer": {
      "playerActivity": "IDLE"
    },
    "Display": {
      "token": ""
    },
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.26338c44-65da-4d58-aa75-c86b21271eb7"
      },
      "user": {
        "userId": "amzn1.ask.account.AHR7KBC3MFCX7LYT6HJBGDLIGQUU3FLANWCZ",
      },
      "device": {
        "deviceId": "amzn1.ask.device.AELNXV4JQJMF5QALYUQXHOZJ",
        "supportedInterfaces": {
          "AudioPlayer": {},
          "Display": {
            "templateVersion": "1.0",
            "markupVersion": "1.0"
          }
        }
      },
      "apiEndpoint": "https://api.amazonalexa.com",
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.4859a7e3-1960-4ed9-ac7b-854309346916",
    "timestamp": "2018-04-04T06:28:23Z",
    "locale": "en-US",
    "intent": {
      "name": "TestCustomSlotTypeIntents",
      "confirmationStatus": "NONE",
      "slots": {
        "child_info": {
          "name": "child_info",
          "value": "friends info",
          "resolutions": {
            "resolutionsPerAuthority": [
              {
                "authority": "amzn1.er-authority.echo-sdk.amzn1.ask.skill.26338c44-65da-4d58-aa75-c86b21271eb7.child_info_type",
                "status": {
                  "code": "ER_SUCCESS_MATCH"
                },
                "values": [
                  {
                    "value": {
                      "name": "friend_info",
                      "id": "FRIEND_INFO"
                    }
                  }
                ]
              }
            ]
          },
          "confirmationStatus": "NONE"
        }
      }
    },
    "dialogState": "STARTED"
  }
}


class CustomSlotTypeIntegrationTests(unittest.TestCase):
    """ Integration tests of the custom slot type """

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['ASK_VERIFY_REQUESTS'] = False
        self.ask = Ask(app=self.app, route='/ask')
        self.client = self.app.test_client()

        @self.ask.intent('TestCustomSlotTypeIntents')
        def custom_slot_type_intents(child_info):
            return statement(child_info)

    def tearDown(self):
        pass

    def test_custom_slot_type_intent(self):
        """ Test to see if custom slot type value is correct """
        response = self.client.post('/ask', data=json.dumps(play_request))
        self.assertEqual(200, response.status_code)

        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual('friend_info',
                         data['response']['outputSpeech']['text'])


if __name__ == '__main__':
    unittest.main()

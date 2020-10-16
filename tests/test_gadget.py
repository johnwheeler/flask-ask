import unittest
import json
import uuid

from datetime import datetime
from flask_ask import Ask, gadget, animation, animation_step, question, session
from flask import Flask
from mock import patch, MagicMock


class GadgetUnitTests(unittest.TestCase):

    def setUp(self):
        self.ask_patcher = patch('flask_ask.core.find_ask', return_value=Ask())
        self.ask_patcher.start()
        self.context_patcher = patch('flask_ask.models.context', return_value=MagicMock())
        self.context_patcher.start()

    def tearDown(self):
        self.ask_patcher.stop()
        self.context_patcher.stop()

    def test_animation_step(self):
        step = animation_step()
        self.assertEqual(step, {'durationMs': 500, 'color': 'FFFFFF', 'blend': False})

    def test_animation(self):
        a = animation()
        self.assertEqual(a, {'repeat': 1, 'targetLights': ['1'], 'sequence': []})

    def test_animation_sequence(self):
        a = animation()
        a.fade_in(duration=2000, color='0000FF').off(duration=500)
        a.crossfade(duration=1000, colors=['FF0000', 'FFFF00']).fade_out(duration=1000)
        sequence = [
            {'durationMs': 1, 'color': '000000', 'blend': True},
            {'durationMs': 2000, 'color': '0000FF', 'blend': True},
            {'durationMs': 500, 'color': '000000', 'blend': False},
            {'durationMs': 1000, 'color': 'FF0000', 'blend': True},
            {'durationMs': 1000, 'color': 'FFFF00', 'blend': True},
            {'durationMs': 1, 'color': 'FFFFFF', 'blend': True},
            {'durationMs': 1000, 'color': '000000', 'blend': True}
        ]
        self.assertEqual(a['sequence'], sequence)

    def test_start_input_handler(self):
        g = gadget('foo')._start_input_handler(timeout=5000)
        self.assertEqual(g._response['outputSpeech'], {'type': 'PlainText', 'text': 'foo'})
        self.assertEqual(g._response['shouldEndSession'], False)
        self.assertEqual(g._response['directives'][0]['type'], 'GameEngine.StartInputHandler')
        self.assertEqual(g._response['directives'][0]['timeout'], 5000)
        self.assertEqual(g._response['directives'][0]['proxies'], [])
        self.assertEqual(g._response['directives'][0]['recognizers'], {})
        self.assertEqual(g._response['directives'][0]['events'], {})

    def test_stop_input_handler(self):
        g = gadget().stop('1234567890')
        self.assertEqual(g._response['outputSpeech'], {'type': 'PlainText', 'text': ''})
        self.assertEqual(g._response['shouldEndSession'], False)
        self.assertEqual(g._response['directives'][0]['type'], 'GameEngine.StopInputHandler')
        self.assertEqual(g._response['directives'][0]['originatingRequestId'], '1234567890')

    def test_roll_call(self):
        g = gadget('Starting roll call').roll_call(timeout=10000, max_buttons=2)
        self.assertEqual(g._response['outputSpeech']['text'], 'Starting roll call')
        self.assertEqual(g._response['shouldEndSession'], False)
        self.assertEqual(len(g._response['directives']), 1)
        directive = g._response['directives'][0]
        self.assertEqual(directive['type'], 'GameEngine.StartInputHandler')
        self.assertEqual(directive['timeout'], 10000)
        self.assertEqual(directive['proxies'], ['btn1', 'btn2'])
        recognizers = {
            'roll_call_recognizer_btn1': {
                'type': 'match',
                'fuzzy': True,
                'anchor': 'end',
                'pattern': [{'gadgetIds': ['btn1'], 'action': 'down'}]
            },
            'roll_call_recognizer_btn2': {
                'type': 'match',
                'fuzzy': True,
                'anchor': 'end',
                'pattern': [{'gadgetIds': ['btn2'], 'action': 'down'}]
            }
        }
        self.assertEqual(directive['recognizers'], recognizers)
        events = {
            'roll_call_event_btn1': {
                'meets': ['roll_call_recognizer_btn1'],
                'reports': 'matches',
                'shouldEndInputHandler': False,
                'maximumInvocations': 1
            },
            'roll_call_event_btn2': {
                'meets': ['roll_call_recognizer_btn2'],
                'reports': 'matches',
                'shouldEndInputHandler': True,
                'maximumInvocations': 1
            },
            'timeout': {
                'meets': ['timed out'],
                'reports': 'history',
                'shouldEndInputHandler': True
            }
        }
        self.assertEqual(directive['events'], events)

    def test_first_button(self):
        g = gadget('Press your buttons').first_button(timeout=5000)
        self.assertEqual(g._response['outputSpeech']['text'], 'Press your buttons')
        self.assertEqual(g._response['shouldEndSession'], False)
        self.assertEqual(len(g._response['directives']), 1)
        directive = g._response['directives'][0]
        self.assertEqual(directive['type'], 'GameEngine.StartInputHandler')
        self.assertEqual(directive['timeout'], 5000)
        self.assertEqual(directive['proxies'], [])
        recognizers = {
            'button_down_recognizer': {
                'type': 'match',
                'fuzzy': False,
                'anchor': 'end',
                'pattern': [{'action': 'down'}]
            }
        }
        events = {
            'timeout': {
                'meets': ['timed out'],
                'reports': 'nothing',
                'shouldEndInputHandler': True
            },
            'button_down_event': {
                'meets': ['button_down_recognizer'],
                'reports': 'matches',
                'shouldEndInputHandler': True
            }
        }
        self.assertEqual(directive['recognizers'], recognizers)
        self.assertEqual(directive['events'], events)


basic_request = {
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
                    "GadgetController": {},
                    "GameEngine": {}
                }
            }
        }
    },
    "request": {}
}


class GadgetIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['ASK_VERIFY_REQUESTS'] = False
        self.ask = Ask(app=self.app, route='/ask')
        self.client = self.app.test_client()

        # @self.ask.intent('RollCallIntent')
        # def start_roll_call():
        #     speech = 'Players, press your buttons now.'
        #     return gadget(speech).roll_call(timeout=10000, max_buttons=2)

        @self.ask.on_input_handler_event()
        def event_received(type, requestId, originatingRequestId, events):
            for event in events:
                for input_event in event['inputEvents']:
                    if session.attributes['activity'] == 'roll call':
                        return register_player(event['name'], input_event)
                    elif session.attributes['activity'] == 'new round':
                        return buzz_in(input_event)

        def register_player(event_name, input_event):
            """Adds a player's button to the list of known buttons and makes the button pulse yellow."""
            if input_event['action'] == 'down':
                button_number = event_name[-1]
                gid = input_event['gadgetId']
                session.attributes['players'].append({'pid': button_number, 'gid': gid})
                speech = ""
                if event_name.endswith('2'):
                    session.attributes['activity'] = 'roll call complete'
                    speech = 'I found {} buttons. Ready to start the round?'.format(2)
                return gadget(speech).set_light(
                    targets=[gid],
                    animations=[animation().on(color='FFFF00')]
                )

        def buzz_in(input_event):
            """Acknowledges the first button that was pressed with speech and a 'breathing' animation."""
            gid = input_event['gadgetId']
            try:
                pid = [p['pid'] for p in session.attributes['players'] if p['gid'] == gid][0]
            except LookupError:
                return question("I couldn't find the player associated with that button.")
            return gadget("Player {}, you buzzed in first.".format(pid)).set_light(
                targets=[gid],
                animations=[animation(repeat=3).breathe(duration=500, color='00FF00')]
            )

    def tearDown(self):
        pass

    def test_response_to_roll_call(self):
        for button in range(1, 3):
            event = {
                'type': 'GameEngine.InputHandlerEvent',
                'requestId': 'amzn1.echo-api.request.{}'.format(str(uuid.uuid4())),
                'events': [{
                    'name': 'roll_call_event_btn{}'.format(button),
                    'inputEvents': [{
                        'gadgetId': 'amzn1.ask.gadget.{}'.format(button),
                        'timestamp': datetime.now().isoformat(),
                        'color': '000000',
                        'feature': 'press',
                        'action': 'down'
                    }]
                }]
            }
            basic_request['request'] = event
            basic_request['session']['attributes']['activity'] = 'roll call'
            basic_request['session']['attributes']['players'] = []
            response = self.client.post('/ask', data=json.dumps(basic_request))
            self.assertEqual(200, response.status_code)
            response_data = json.loads(response.data.decode('utf-8'))
            self.assertEqual(response_data['sessionAttributes']['players'][0]['gid'], 'amzn1.ask.gadget.{}'.format(button))
            self.assertEqual(response_data['sessionAttributes']['players'][0]['pid'], str(button))
            self.assertEqual(len(response_data['response']['directives']), 1)
            directive = response_data['response']['directives'][0]
            sequence = directive['parameters']['animations'][0]['sequence']
            self.assertEqual(sequence[0]['color'], 'FFFF00')

    def test_first_button(self):
        event = {
            'type': 'GameEngine.InputHandlerEvent',
            'requestId': 'amzn1.echo-api.request.{}'.format(str(uuid.uuid4())),
            'events': [{
                'name': 'button_down_event',
                'inputEvents': [{
                    'gadgetId': 'amzn1.ask.gadget.1',
                    'timestamp': datetime.now().isoformat(),
                    'color': '000000',
                    'feature': 'press',
                    'action': 'down'
                }]
            }]
        }
        basic_request['request'] = event
        basic_request['session']['attributes']['activity'] = 'new round'
        basic_request['session']['attributes']['players'] = [
            {"gid": "amzn1.ask.gadget.1", "pid": "1"},
            {"gid": "amzn1.ask.gadget.2", "pid": "2"}
        ]
        response = self.client.post('/ask', data=json.dumps(basic_request))
        self.assertEqual(200, response.status_code)
        response_data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(response_data['response']['outputSpeech']['text'], 'Player 1, you buzzed in first.')


if __name__ == '__main__':
    unittest.main()

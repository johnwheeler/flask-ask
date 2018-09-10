import unittest
import json
import uuid

from flask_ask import Ask, gadget, animation, animation_step
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
        g = gadget()._stop_input_handler('1234567890')
        self.assertEqual(g._response['outputSpeech'], {'type': 'PlainText', 'text': ''})
        self.assertEqual(g._response['shouldEndSession'], False)
        self.assertEqual(g._response['directives'][0]['type'], 'GameEngine.StopInputHandler')
        self.assertEqual(g._response['directives'][0]['originatingRequestId'], '1234567890')

    def test_roll_call(self):
        g = gadget('Starting roll call').roll_call(timeout=10000, max_buttons=2)
        self.assertEqual(g._response['outputSpeech']['text'], 'Starting roll call')
        self.assertEqual(g._response['shouldEndSession'], False)
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


if __name__ == '__main__':
    unittest.main()

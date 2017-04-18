import unittest
from mock import patch, MagicMock
from flask import Flask
from flask_ask import Ask, audio
from flask_ask.models import _Field


class AudioUnitTests(unittest.TestCase):

    def setUp(self):
        self.ask_patcher = patch('flask_ask.core.find_ask', return_value=Ask())
        self.ask_patcher.start()
        self.context_patcher = patch('flask_ask.models.context', return_value=MagicMock())
        self.context_patcher.start()

    def tearDown(self):
        self.ask_patcher.stop()
        self.context_patcher.stop()

    def test_token_generation(self):
        """ Confirm we get a new token when setting a stream url """
        audio_item = audio()._audio_item(stream_url='https://fakestream', offset=123)
        self.assertEqual(36, len(audio_item['stream']['token']))
        self.assertEqual(123, audio_item['stream']['offsetInMilliseconds'])


class AskStreamHandlingTests(unittest.TestCase):

    def setUp(self):
        fake_context = {'System': {'user': {'userId': 'dave'}}}
        self.context_patcher = patch.object(Ask, 'context', return_value=fake_context)
        self.context_patcher.start()
        self.request_patcher = patch.object(Ask, 'request', return_value=MagicMock())
        self.request_patcher.start()

    def tearDown(self):
        self.context_patcher.stop()
        self.request_patcher.stop()

    def test_setting_and_getting_current_stream(self):
        ask = Ask()
        with patch('flask_ask.core.find_ask', return_value=ask):
            self.assertEqual(_Field(), ask.current_stream)
        
            stream = _Field()
            stream.__dict__.update({'token': 'asdf', 'offsetInMilliseconds': 123, 'url': 'junk'})
            with patch('flask_ask.core.top_stream', return_value=stream):
                self.assertEqual(stream, ask.current_stream)

    def test_from_directive_call(self):
        ask = Ask()
        fake_stream = _Field()
        fake_stream.__dict__.update({'token':'fake'})
        with patch('flask_ask.core.top_stream', return_value=fake_stream):
            from_buffer = ask._from_directive()
            self.assertEqual(fake_stream, from_buffer)


if __name__ == '__main__':
    unittest.main()

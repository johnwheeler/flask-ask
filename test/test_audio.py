import unittest
from flask_ask import audio


class AudioSessionTests(unittest.TestCase):

    def test_token_generation(self):
        """ Confirm we get a new token when setting a stream url """
        audio_item = audio()._audio_item(stream_url='https://fakestream', offset=123)
        self.assertEqual(36, len(audio_item['stream']['token']))
        self.assertEqual(123, audio_item['stream']['offsetInMilliseconds'])


if __name__ == '__main__':
    unittest.main()

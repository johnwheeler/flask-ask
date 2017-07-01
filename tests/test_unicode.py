# -*- coding: utf-8 -*-
import unittest
from flask_ask import statement, question


class UnicodeTests(unittest.TestCase):
    """ Test using Unicode in responses. (Issue #147) """

    unicode_string = u"Was kann ich für dich tun?"

    def test_unicode_statements(self):
        """ Test unicode statement responses """
        stmt = statement(self.unicode_string)
        speech = stmt._response['outputSpeech']['text']
        print(speech)
        self.assertTrue(self.unicode_string in speech)

    def test_unicode_questions(self):
        """ Test unicode in question responses """
        q = question(self.unicode_string)
        speech = q._response['outputSpeech']['text']
        self.assertTrue(self.unicode_string in speech)

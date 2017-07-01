# -*- coding: utf-8 -*-
import unittest
from flask_ask import statement, question


class UnicodeTests(unittest.TestCase):
    """ Test using Unicode in responses. (Issue #147) """

    def test_unicode_statements(self):
        """ Test unicode statement responses """
        stmt = statement(u"Was kann ich für dich tun?")
        self.assertIsNotNone(stmt)

    def test_unicode_questions(self):
        """ Test unicode in question responses """
        q = question(u"Was kann ich für dich tun?")
        self.assertIsNotNone(q)

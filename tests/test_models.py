# -*- coding: utf-8 -*-

from flask_ask import statement

def test_statement_handles_unicode_input():
    non_ascii_statement = statement(u'ÜÖÄ')

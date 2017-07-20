# -*- coding: utf-8 -*-
import unittest
from aniso8601.timezone import UTCOffset, build_utcoffset
from flask_ask.core import Ask

from datetime import datetime, timedelta
from mock import patch, MagicMock
import json


class FakeRequest(object):
    """ Fake out a Flask request for testing purposes for now """

    headers = {'Signaturecertchainurl': None, 'Signature': None}

    def __init__(self, data):
        self.data = json.dumps(data)


class TestCoreRoutines(unittest.TestCase):
    """ Tests for core Flask Ask functionality """


    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.debug = True
        self.mock_app.config = {'ASK_VERIFY_TIMESTAMP_DEBUG': False}

        # XXX: this mess implies we should think about tidying up Ask._alexa_request 
        self.patch_current_app = patch('flask_ask.core.current_app', new=self.mock_app)
        self.patch_load_cert = patch('flask_ask.core.verifier.load_certificate')
        self.patch_verify_sig = patch('flask_ask.core.verifier.verify_signature')
        self.patch_current_app.start()
        self.patch_load_cert.start()
        self.patch_verify_sig.start()

    @patch('flask_ask.core.flask_request',
           new=FakeRequest({'request': {'timestamp': 1234},
                            'session': {'application': {'applicationId': 1}}}))
    def test_alexa_request_parsing(self):
        ask = Ask()
        ask._alexa_request()


    def test_parse_timestamp(self):
        utc = build_utcoffset('UTC', timedelta(hours=0))
        result = Ask._parse_timestamp('2017-07-08T07:38:00Z')
        self.assertEqual(datetime(2017, 7, 8, 7, 38, 0, 0, utc), result)

        result = Ask._parse_timestamp(1234567890)
        self.assertEqual(datetime(2009, 2, 13, 23, 31, 30), result)

        with self.assertRaises(ValueError):
            Ask._parse_timestamp(None)

    def test_tries_parsing_on_valueerror(self):
        max_timestamp = 253402300800

        # should cause a ValueError normally
        with self.assertRaises(ValueError):
            datetime.utcfromtimestamp(max_timestamp)

        # should safely parse, assuming scale change needed
        # note: this assert looks odd, but Py2 handles the parsing
        #       differently, resulting in a differing timestamp
        #       due to more granularity of microseconds
        result = Ask._parse_timestamp(max_timestamp)
        self.assertEqual(datetime(1978, 1, 11, 21, 31, 40).timetuple()[0:6],
                         result.timetuple()[0:6])

        with self.assertRaises(ValueError):
            # still raise an error if too large
            Ask._parse_timestamp(max_timestamp * 1000)

    def tearDown(self):
        self.patch_current_app.stop()
        self.patch_load_cert.stop()
        self.patch_verify_sig.stop()

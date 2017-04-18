import unittest
from mock import patch
from flask_ask.core import Ask, push_stream, pop_stream, top_stream


class CacheTests(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('flask_ask.core.find_ask', return_value=Ask())
        self.ask = self.patcher.start()
        self.user_id = 'dave'
        self.token = '123-abc'

    def tearDown(self):
        self.patcher.stop()

    def test_adding_removing_stream(self):
        self.assertTrue(push_stream(self.user_id, self.token))

        # peak at the top
        self.assertEqual(self.token, top_stream(self.user_id))
        self.assertIsNone(top_stream('not dave'))

        # pop it off
        self.assertEqual(self.token, pop_stream(self.user_id))
        self.assertIsNone(top_stream(self.user_id))

    def test_pushing_works_like_a_stack(self):
        push_stream(self.user_id, 'junk')
        push_stream(self.user_id, self.token)

        self.assertEqual(self.token, pop_stream(self.user_id))
        self.assertEqual('junk', pop_stream(self.user_id))
        self.assertIsNone(pop_stream(self.user_id))

    def test_cannot_push_nones_into_stack(self):
        self.assertIsNone(push_stream(self.user_id, None))


if __name__ == '__main__':
    unittest.main()

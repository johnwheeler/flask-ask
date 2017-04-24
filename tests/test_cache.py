import unittest
from mock import patch, Mock
from werkzeug.contrib.cache import SimpleCache
from flask_ask.core import Ask
from flask_ask.cache import push_stream, pop_stream, top_stream, set_stream


class CacheTests(unittest.TestCase):

    def setUp(self):
        self.patcher = patch('flask_ask.core.find_ask', return_value=Ask())
        self.ask = self.patcher.start()
        self.user_id = 'dave'
        self.token = '123-abc'
        self.cache = SimpleCache()

    def tearDown(self):
        self.patcher.stop()

    def test_adding_removing_stream(self):
        self.assertTrue(push_stream(self.cache, self.user_id, self.token))

        # peak at the top
        self.assertEqual(self.token, top_stream(self.cache, self.user_id))
        self.assertIsNone(top_stream(self.cache, 'not dave'))

        # pop it off
        self.assertEqual(self.token, pop_stream(self.cache, self.user_id))
        self.assertIsNone(top_stream(self.cache, self.user_id))

    def test_pushing_works_like_a_stack(self):
        push_stream(self.cache, self.user_id, 'junk')
        push_stream(self.cache, self.user_id, self.token)

        self.assertEqual(self.token, pop_stream(self.cache, self.user_id))
        self.assertEqual('junk', pop_stream(self.cache, self.user_id))
        self.assertIsNone(pop_stream(self.cache, self.user_id))

    def test_cannot_push_nones_into_stack(self):
        self.assertIsNone(push_stream(self.cache, self.user_id, None))

    def test_set_overrides_stack(self):
        push_stream(self.cache, self.user_id, '1')
        push_stream(self.cache, self.user_id, '2')
        self.assertEqual('2', top_stream(self.cache, self.user_id))

        set_stream(self.cache, self.user_id, '3')
        self.assertEqual('3', pop_stream(self.cache, self.user_id))
        self.assertIsNone(pop_stream(self.cache, self.user_id))

    def test_calls_to_top_with_no_user_return_none(self):
        """ RedisCache implementation doesn't like None key values. """
        mock = Mock()
        result = top_stream(mock, None)
        self.assertFalse(mock.get.called)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()

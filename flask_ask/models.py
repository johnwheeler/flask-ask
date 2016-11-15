import inspect
from flask import json
from xml.etree import ElementTree
from .core import current_stream, _stream_buffer
import random


class _Field():
    """Holds the request/response field as an object with attributes."""

    def __init__(self, request_param={}):

        for key, value in request_param.items():
            # turn attributes' value from a dict into another object
            # allows all attributes of each parameter to be accessed with dot notation
            if isinstance(value, dict):
                value = _Field(value)
            setattr(self, key, value)

class _Request():
    def __init__(self, request_body_json):
        self._parse_request_body(request_body_json)

    def _parse_request_body(self, request_body_json):
        # private attributes hold the json of the request field
        self._body = request_body_json
        self._version = self._body.get('version', {})
        self._request = self._body.get('request', {})
        self._context = self._body.get('context', {})
        self._session = self._body.get('session', {})

    @property
    def body(self):
        return self._body

    @property
    def version(self):
        return self._version

    @property
    def context(self):
        return _Field(self._context)

    @property
    def request(self):
        return _Field(self._request)

    @property
    def session(self):
        return _Field(self._session)


class _Response(object):

    def __init__(self, speech):
        self._json_default = None
        self._response = {
            'outputSpeech': _output_speech(speech)
        }

    def simple_card(self, title=None, content=None):
        card = {
            'type': 'Simple',
            'title': title,
            'content': content
        }
        self._response['card'] = card
        return self

    def standard_card(self, title=None, text=None, small_image_url=None, large_image_url=None):
        card = {
            'type': 'Standard',
            'title': title,
            'text': text
        }

        if any((small_image_url, large_image_url)):
            card['image'] = {}
        if small_image_url is not None:
            card['image']['smallImageUrl'] = small_image_url
        if large_image_url is not None:
            card['image']['largeImageUrl'] = large_image_url

        self._response['card'] = card
        return self

    def link_account_card(self):
        card = {'type': 'LinkAccount'}
        self._response['card'] = card
        return self

    def render_response(self):
        response_wrapper = {
            'version': '1.0',
            'response': self._response,
            'sessionAttributes': getattr(core.session, 'attributes', {})
        }
        kw = {}
        if hasattr(core.session, 'attributes_encoder'):
            json_encoder = core.session.attributes_encoder
            kwargname = 'cls' if inspect.isclass(json_encoder) else 'default'
            kw[kwargname] = json_encoder
        core._dbgdump(response_wrapper, **kw)

        return json.dumps(response_wrapper, **kw)


class statement(_Response):

    def __init__(self, speech):
        super(statement, self).__init__(speech)
        self._response['shouldEndSession'] = True


class question(_Response):

    def __init__(self, speech):
        super(question, self).__init__(speech)
        self._response['shouldEndSession'] = False

    def reprompt(self, reprompt):
        reprompt = {'outputSpeech': _output_speech(reprompt)}
        self._response['reprompt'] = reprompt
        return self


class audio(_Response):
    """Returns a response object with an Amazon AudioPlayer Directive.

    Responses for LaunchRequests and IntentRequests may include outputSpeech in addition to an audio directive

    Note that responses to AudioPlayer requests do not allow outputSpeech.
    These must only include AudioPlayer Directives.

    @ask.intent('PlayFooAudioIntent')
    def play_foo_audio():
        speech = 'playing from foo'
        stream_url = www.foo.com
        return audio(speech).play(stream_url)


    @ask.intent('AMAZON.PauseIntent')
    def stop_audio():
        return audio('Ok, stopping the audio').stop()
    """

    def __init__(self, speech=''):
        super(audio, self).__init__(speech)
        self._response['directives'] = []


    def play(self, stream_url, offset=0):
        """Sends a Play Directive to begin playback and replace current and enqueued streams."""

        self._response['shouldEndSession'] = True
        directive = self._play_directive('REPLACE_ALL')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset)
        self._response['directives'].append(directive)
        return self


    def enqueue(self, stream_url, offset=0):
        """Adds stream to the queue. Does not impact the currently playing stream."""
        directive = self._play_directive('ENQUEUE')
        audio_item = self._audio_item(stream_url=stream_url, offset=offset)
        audio_item['stream']['expectedPreviousToken'] = current_stream.token

        directive['audioItem'] = audio_item
        self._response['directives'].append(directive)
        return self

    def play_next(self, stream_url=None, offset=0):
        """Replace all streams in the queue but does not impact the currently playing stream."""

        directive = self._play_directive('REPLACE_ENQUEUED')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset)
        self._response['directives'].append(directive)
        return self

    def resume(self):
        """Sends Play Directive to resume playback at the paused offset"""
        directive = self._play_directive('REPLACE_ALL')
        directive['audioItem'] = self._audio_item()
        self._response['directives'].append(directive)
        return self

    def _play_directive(self, behavior):
        directive = {}
        directive['type'] = 'AudioPlayer.Play'
        directive['playBehavior'] = behavior
        return directive

    def _audio_item(self, stream_url=None, offset=0):
        """Builds an AudioPlayer Directive's audioItem and updates current_stream"""
        audio_item = {'stream': {}}
        stream = audio_item['stream']

        # existing stream
        if not stream_url:
            # stream.update(current_stream.__dict__)
            stream['url'] = current_stream.url
            stream['token'] = current_stream.token
            stream['offsetInMilliseconds'] = current_stream.offsetInMilliseconds

        # new stream
        else:
            stream['url'] = stream_url
            stream['token'] = str(random.randint(10000, 100000))
            stream['offsetInMilliseconds'] = offset

        _stream_buffer.push(stream)
        return audio_item

    def stop(self):
        """Sends AudioPlayer.Stop Directive to stop the current stream playback"""
        self._response['directives'].append({'type': 'AudioPlayer.Stop'})
        return self

    def clear_queue(self, stop=False):
        """Clears queued streams and optionally stops current stream.

        Keyword Arguments:
            stop {bool}  set True to stop current current stream and clear queued streams.
                           set False to clear queued streams and allow current stream to finish
                           default: {False}
        """

        directive = {}
        directive['type'] = 'AudioPlayer.ClearQueue'
        if stop:
            directive['clearBehavior'] = 'CLEAR_ALL'
        else:
            directive['clearBehavior'] = 'CLEAR_ENQUEUED'

        self._response['directives'].append(directive)
        return self

def _copyattr(src, dest, attr, convert=None):
    if attr in src:
        value = src[attr]
        if convert is not None:
            value = convert(value)
        setattr(dest, attr, value)


def _output_speech(speech):
    try:
        xmldoc = ElementTree.fromstring(speech)
        if xmldoc.tag == 'speak':
            return {'type': 'SSML', 'ssml': speech}
    except ElementTree.ParseError as e:
        pass
    return {'type': 'PlainText', 'text': speech}

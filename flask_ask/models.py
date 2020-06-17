import inspect
from flask import json
from xml.etree import ElementTree
import aniso8601
from .core import session, context, current_stream, stream_cache, dbgdump
from .cache import push_stream
import uuid


class _Field(dict):
    """Container to represent Alexa Request Data.

    Initialized with request_json and creates a dict object with attributes
    to be accessed via dot notation or as a dict key-value.

    Parameters within the request_json that contain their data as a json object
    are also represented as a _Field object.

    Example:

    payload_object = _Field(alexa_json_payload)

    request_type_from_keys = payload_object['request']['type']
    request_type_from_attrs = payload_object.request.type

    assert request_type_from_keys == request_type_from_attrs
    """

    def __init__(self, request_json={}):
        super(_Field, self).__init__(request_json)
        for key, value in request_json.items():
            if isinstance(value, dict):
                value = _Field(value)
            self[key] = value

    def __getattr__(self, attr):
        # converts timestamp str to datetime.datetime object
        if 'timestamp' in attr:
            return aniso8601.parse_datetime(self.get(attr))
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)


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
    
    def list_display_render(self, template=None, title=None, backButton='HIDDEN', token=None, background_image_url=None, image=None, listItems=None, hintText=None):
        directive = [
            {
                'type': 'Display.RenderTemplate',
                'template': {
                    'type': template,
                    'backButton': backButton,
                    'title': title,
                    'listItems': listItems
                }
            }
        ]
        
        if background_image_url is not None:
            directive[0]['template']['backgroundImage'] = {
               'sources': [
                   {'url': background_image_url}
               ]
            }

        if hintText is not None:
            hint = {
                'type':'Hint',
                'hint': {
                    'type':"PlainText",
                    'text': hintText
                }
            }
            directive.append(hint)
        self._response['directives'] = directive
        return self

    def display_render(self, template=None, title=None, backButton='HIDDEN', token=None, background_image_url=None, image=None, text=None, hintText=None):
        directive = [
            {
                'type': 'Display.RenderTemplate',
                'template': {
                    'type': template,
                    'backButton': backButton,
                    'title': title,
                    'textContent': text
                }
            }
        ]
        
        if background_image_url is not None:
            directive[0]['template']['backgroundImage'] = {
               'sources': [
                   {'url': background_image_url}
               ]
            }
        
        if image is not None:
            directive[0]['template']['image'] = {
                'sources': [
                    {'url': image}
                ]
            }
            
        if token is not None:
            directive[0]['template']['token'] = token
            
        if hintText is not None:
            hint = {
                'type':'Hint',
                'hint': {
                    'type':"PlainText",
                    'text': hintText
                }
            }
            directive.append(hint)

        self._response['directives'] = directive
        return self

    def link_account_card(self):
        card = {'type': 'LinkAccount'}
        self._response['card'] = card
        return self

    def consent_card(self, permissions):
        card = {
            'type': 'AskForPermissionsConsent',
            'permissions': [permissions]
        }
        self._response['card'] = card
        return self

    def render_response(self):
        response_wrapper = {
            'version': '1.0',
            'response': self._response,
            'sessionAttributes': session.attributes
        }
        
        kw = {}
        if hasattr(session, 'attributes_encoder'):
            json_encoder = session.attributes_encoder
            kwargname = 'cls' if inspect.isclass(json_encoder) else 'default'
            kw[kwargname] = json_encoder
        dbgdump(response_wrapper, **kw)

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


class buy(_Response):

    def __init__(self, productId=None):
        self._response = {
            'shouldEndSession': True,
            'directives': [{
              'type': 'Connections.SendRequest',
              'name': 'Buy',          
              'payload': {
                         'InSkillProduct': {
                             'productId': productId
                         }
               },
              'token': 'correlationToken'              
            }]
        }


class refund(_Response):

    def __init__(self, productId=None):
        self._response = {
            'shouldEndSession': True,
            'directives': [{
              'type': 'Connections.SendRequest',
              'name': 'Cancel',          
              'payload': {
                         'InSkillProduct': {
                             'productId': productId
                         }
               },
              'token': 'correlationToken'              
            }]
        }

class upsell(_Response):

    def __init__(self, productId=None, msg=None):
        self._response = {
            'shouldEndSession': True,
            'directives': [{
              'type': 'Connections.SendRequest',
              'name': 'Upsell',          
              'payload': {
                         'InSkillProduct': {
                             'productId': productId
                         },
                         'upsellMessage': msg
               },
              'token': 'correlationToken'              
            }]
        }

class delegate(_Response):

    def __init__(self, updated_intent=None):
        self._response = {
            'shouldEndSession': False,
            'directives': [{'type': 'Dialog.Delegate'}]
        }

        if updated_intent:
            self._response['directives'][0]['updatedIntent'] = updated_intent


class elicit_slot(_Response):
    """
    Sends an ElicitSlot directive.
    slot - The slot name to elicit
    speech - The output speech
    updated_intent - Optional updated intent
    """

    def __init__(self, slot, speech, updated_intent=None):
        self._response = {
            'shouldEndSession': False,
            'directives': [{
                'type': 'Dialog.ElicitSlot',
                'slotToElicit': slot,
            }],
            'outputSpeech': _output_speech(speech),
        }

        if updated_intent:
            self._response['directives'][0]['updatedIntent'] = updated_intent

class confirm_slot(_Response):
    """
    Sends a ConfirmSlot directive.
    slot - The slot name to confirm
    speech - The output speech
    updated_intent - Optional updated intent
    """

    def __init__(self, slot, speech, updated_intent=None):
        self._response = {
            'shouldEndSession': False,
            'directives': [{
                'type': 'Dialog.ConfirmSlot',
                'slotToConfirm': slot,
            }],
            'outputSpeech': _output_speech(speech),
        }

        if updated_intent:
            self._response['directives'][0]['updatedIntent'] = updated_intent

class confirm_intent(_Response):
    """
    Sends a ConfirmIntent directive.
    
    """
    def __init__(self, speech, updated_intent=None):
        self._response = {
            'shouldEndSession': False,
            'directives': [{
                'type': 'Dialog.ConfirmIntent',
            }],
            'outputSpeech': _output_speech(speech),
        }

        if updated_intent:
            self._response['directives'][0]['updatedIntent'] = updated_intent


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
        if not speech:
            self._response = {}
        self._response['directives'] = []

    def play(self, stream_url, offset=0, opaque_token=None):
        """Sends a Play Directive to begin playback and replace current and enqueued streams."""

        self._response['shouldEndSession'] = True
        directive = self._play_directive('REPLACE_ALL')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset, opaque_token=opaque_token)
        self._response['directives'].append(directive)
        return self

    def enqueue(self, stream_url, offset=0, opaque_token=None):
        """Adds stream to the queue. Does not impact the currently playing stream."""
        directive = self._play_directive('ENQUEUE')
        audio_item = self._audio_item(stream_url=stream_url,
                                      offset=offset,
                                      push_buffer=False,
                                      opaque_token=opaque_token)
        audio_item['stream']['expectedPreviousToken'] = current_stream.token

        directive['audioItem'] = audio_item
        self._response['directives'].append(directive)
        return self

    def play_next(self, stream_url=None, offset=0, opaque_token=None):
        """Replace all streams in the queue but does not impact the currently playing stream."""

        directive = self._play_directive('REPLACE_ENQUEUED')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset, opaque_token=opaque_token)
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

    def _audio_item(self, stream_url=None, offset=0, push_buffer=True, opaque_token=None):
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
            stream['token'] = opaque_token or str(uuid.uuid4())
            stream['offsetInMilliseconds'] = offset

        if push_buffer:  # prevents enqueued streams from becoming current_stream
            push_stream(stream_cache, context['System']['user']['userId'], stream)
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
    except (UnicodeEncodeError, ElementTree.ParseError) as e:
        pass
    return {'type': 'PlainText', 'text': speech}

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


class gadget(_Response):
    """Returns a response object with one or more GameEngine/GadgetController directives.

    Responses may include outputSpeech in addition to these directives.  All timeout
    parameters below are in milliseconds.
    """

    def __init__(self, speech=''):
        super(gadget, self).__init__(speech)
        self._response['directives'] = []
        self._response['shouldEndSession'] = False

    def reprompt(self, reprompt):
        reprompt = {'outputSpeech': _output_speech(reprompt)}
        self._response['reprompt'] = reprompt
        return self

    def _start_input_handler(self, timeout=0, proxies=[], recognizers={}, events={}):
        """Returns an Input Handler which will wait for gadget events."""
        directive = {}
        directive['type'] = 'GameEngine.StartInputHandler'
        directive['timeout'] = timeout
        directive['proxies'] = proxies
        directive['recognizers'] = recognizers
        directive['events'] = events
        return directive

    def _stop_input_handler(self, request_id):
        """Cancels the current Input Handler."""
        directive = {}
        directive['type'] = 'GameEngine.StopInputHandler'
        directive['originatingRequestId'] = request_id
        return directive

    def roll_call(self, timeout=0, max_buttons=1):
        """Waits for all available Echo Buttons to connect to the Echo device."""
        directive = self._start_input_handler(timeout=timeout)
        for i in range(1, max_buttons + 1):
            button = "btn{}".format(i)
            recognizer = 'roll_call_recognizer_{}'.format(button)
            event = 'roll_call_event_{}'.format(button)
            directive['proxies'].append(button)
            directive['recognizers'][recognizer] = {
                'type': 'match',
                'fuzzy': True,
                'anchor': 'end',
                'pattern': [{
                    'gadgetIds': [button],
                    'action': 'down'
                }]
            }
            directive['events'][event] = {
                'meets': [recognizer],
                'reports': 'matches',
                'shouldEndInputHandler': i == max_buttons,
                'maximumInvocations': 1
            }
        directive['events']['timeout'] = {
            'meets': ['timed out'],
            'reports': 'history',
            'shouldEndInputHandler': True
        }
        self._response['directives'].append(directive)
        return self

    def first_button(self, timeout=0, gadget_ids=[], animations=[]):
        """Waits for the first Echo Button to be pressed."""
        directive = self._start_input_handler(timeout=timeout)
        directive['recognizers'] = {
            'button_down_recognizer': {
                'type': 'match',
                'fuzzy': False,
                'anchor': 'end',
                'pattern': [{
                    'action': 'down'
                }]
            }
        }
        directive['events'] = {
            'timeout': {
                'meets': ['timed out'],
                'reports': 'nothing',
                'shouldEndInputHandler': True
            },
            'button_down_event': {
                'meets': ['button_down_recognizer'],
                'reports': 'matches',
                'shouldEndInputHandler': True
            }
        }
        self._response['directives'].append(directive)
        self.set_light(targets=gadget_ids, animations=animations)
        return self

    def set_light(self, targets=[], trigger='none', delay=0, animations=[]):
        """Sends a command to modify the behavior of connected Echo Buttons."""
        directive = {}
        directive['type'] = 'GadgetController.SetLight'
        directive['version'] = 1
        directive['targetGadgets'] = targets
        if trigger not in ['buttonDown', 'buttonUp', 'none']:
            trigger = None
        if delay < 0 or delay > 65535:
            delay = 0
        directive['parameters'] = {
            'triggerEvent': trigger,
            'triggerEventTimeMs': delay,
            'animations': animations
        }
        self._response['directives'].append(directive)
        return self


class animation(dict):
    """Returns a dictionary of animation parameters to be passed to the GadgetController.SetLight directive.

    Multiple animation steps can be added in a sequence by calling the class methods below.
    """

    def __init__(self, repeat=1, lights=['1'], sequence=[]):
        attributes = {'repeat': repeat, 'targetLights': lights, 'sequence': sequence}
        super(animation, self).__init__(attributes)
        if not sequence:
            print('clearing sequence')
            self['sequence'] = []

    def on(self, duration=1, color='FFFFFF'):
        self['sequence'].append(animation_step(duration=duration, color=color))
        return self

    def off(self, duration=1):
        self['sequence'].append(animation_step(duration=duration, color='000000'))
        return self

    def fade_in(self, duration=3000, color='FFFFFF', repeat=1):
        for i in range(repeat):
            self['sequence'].append(animation_step(duration=1, color='000000', blend=True))
            self['sequence'].append(animation_step(duration=duration, color=color, blend=True))
        return self

    def fade_out(self, duration=3000, color='FFFFFF', repeat=1):
        for i in range(repeat):
            self['sequence'].append(animation_step(duration=1, color=color, blend=True))
            self['sequence'].append(animation_step(duration=duration, color='000000', blend=True))
        return self

    def crossfade(self, duration=2000, colors=['0000FF', 'FF0000'], repeat=1):
        for i in range(repeat):
            for color in colors:
                self['sequence'].append(animation_step(duration=duration, color=color, blend=True))
        return self

    def breathe(self, duration=1000, color='FFFFFF', repeat=1):
        for i in range(repeat):
            self['sequence'].append(animation_step(duration=1, color='000000', blend=True))
            self['sequence'].append(animation_step(duration=duration, color='FFFFFF', blend=True))
            self['sequence'].append(animation_step(duration=int(duration * 0.3), color='000000', blend=True))
        return self

    def blink(self, duration=500, color='FFFFFF', repeat=1):
        for i in range(repeat):
            self['sequence'].append(animation_step(duration=duration, color=color))
            self['sequence'].append(animation_step(duration=duration, color='000000'))
        return self

    def flip(self, duration=500, colors=['0000FF', 'FF0000'], repeat=1):
        for i in range(repeat):
            for color in colors:
                self['sequence'].append(animation_step(duration=duration, color=color))
        return self

    def pulse(self, duration=500, color='FFFFFF', repeat=1):
        for i in range(repeat):
            self['sequence'].append(animation_step(duration=duration, color=color, blend=True))
            self['sequence'].append(animation_step(duration=duration*2, color='000000', blend=True))
        return self


class animation_step(dict):
    """Returns a single animation step, which can be chained in a sequence."""

    def __init__(self, duration=500, color='FFFFFF', blend=False):
        attributes = {'durationMs': duration, 'color': color, 'blend': blend}
        super(animation_step, self).__init__(attributes)


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

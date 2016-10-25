import os
import yaml
import inspect
from functools import wraps, partial
from xml.etree import ElementTree

import aniso8601
from werkzeug.local import LocalProxy
from jinja2 import BaseLoader, ChoiceLoader, TemplateNotFound
from flask import current_app, json, request as flask_request, _app_ctx_stack

from . import verifier
from . import logger
from .convert import to_date, to_time, to_timedelta
import collections
import random


request = LocalProxy(lambda: current_app.ask.request)
session = LocalProxy(lambda: current_app.ask.session)
version = LocalProxy(lambda: current_app.ask.version)
context = LocalProxy(lambda: current_app.ask.context)
convert_errors = LocalProxy(lambda: current_app.ask.convert_errors)

_converters = {'date': to_date, 'time': to_time, 'timedelta': to_timedelta}


class Ask(object):

    def __init__(self, app=None, route=None):
        self.app = app
        self._route = route
        self._intent_view_funcs = {}
        self._intent_converts = {}
        self._intent_defaults = {}
        self._intent_mappings = {}
        self._launch_view_func = None
        self._session_ended_view_func = None
        self._on_session_started_callback = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        if self._route is None:
            raise TypeError("route is a required argument when app is not None")

        app.ask = self

        self.ask_verify_requests = app.config.get('ASK_VERIFY_REQUESTS', True)
        self.ask_verify_timestamp_debug = app.config.get('ASK_VERIFY_TIMESTAMP_DEBUG', False)
        self.ask_application_id = app.config.get('ASK_APPLICATION_ID', None)

        if self.ask_verify_requests and self.ask_application_id is None:
            logger.warning("The ASK_APPLICATION_ID has not been set. Application ID verification disabled.")

        app.add_url_rule(self._route, view_func=self._flask_view_func, methods=['POST'])
        app.jinja_loader = ChoiceLoader([app.jinja_loader, YamlLoader(app)])

    def on_session_started(self, f):
        self._on_session_started_callback = f

    def launch(self, f):
        self._launch_view_func = f

        @wraps(f)
        def wrapper(*args, **kw):
            self._flask_view_func(*args, **kw)
        return f

    def session_ended(self, f):
        self._session_ended_view_func = f

        @wraps(f)
        def wrapper(*args, **kw):
            self._flask_view_func(*args, **kw)
        return f

    def intent(self, intent_name, mapping={}, convert={}, default={}):
        def decorator(f):
            self._intent_view_funcs[intent_name] = f
            self._intent_mappings[intent_name] = mapping
            self._intent_converts[intent_name] = convert
            self._intent_defaults[intent_name] = default

            @wraps(f)
            def wrapper(*args, **kw):
                self._flask_view_func(*args, **kw)
            return f
        return decorator

    @property
    def request(self):
        return getattr(_app_ctx_stack.top, '_ask_request', None)

    @request.setter
    def request(self, value):
        _app_ctx_stack.top._ask_request = value

    @property
    def session(self):
        return getattr(_app_ctx_stack.top, '_ask_session', None)

    @session.setter
    def session(self, value):
        _app_ctx_stack.top._ask_session = value

    @property
    def version(self):
        return getattr(_app_ctx_stack.top, '_ask_version', None)

    @version.setter
    def version(self, value):
        _app_ctx_stack.top._ask_version = value

    @property
    def context(self):
        return getattr(_app_ctx_stack.top, '_ask_context', None)

    @context.setter
    def context(self, value):
        _app_ctx_stack.top._ask_context = value

    @property
    def convert_errors(self):
        return getattr(_app_ctx_stack.top, '_ask_convert_errors', None)

    @convert_errors.setter
    def convert_errors(self, value):
        _app_ctx_stack.top._ask_convert_errors = value

    def _alexa_request(self, verify=True):
        raw_body = flask_request.data
        alexa_request_payload = json.loads(raw_body)

        if verify:
            cert_url = flask_request.headers['Signaturecertchainurl']
            signature = flask_request.headers['Signature']

            # load certificate - this verifies a the certificate url and format under the hood
            cert = verifier.load_certificate(cert_url)
            # verify signature
            verifier.verify_signature(cert, signature, raw_body)
            # verify timestamp
            timestamp = aniso8601.parse_datetime(alexa_request_payload['request']['timestamp'])
            if not current_app.debug or self.ask_verify_timestamp_debug:
                verifier.verify_timestamp(timestamp)
            # verify application id
            application_id = alexa_request_payload['session']['application']['applicationId']
            if self.ask_application_id is not None:
                verifier.verify_application_id(application_id, self.ask_application_id)

        return alexa_request_payload

    def _flask_view_func(self, *args, **kwargs):
        ask_payload = self._alexa_request(verify=self.ask_verify_requests)
        _dbgdump(ask_payload)
        request_body = _parse_request_body(ask_payload)
        self.request = request_body.request
        self.session = request_body.session
        self.version = request_body.version
        self.context = request_body.context
        if self.session.new and self._on_session_started_callback is not None:
            self._on_session_started_callback()
        result = None
        request_type = self.request.type
        if request_type == 'LaunchRequest' and self._launch_view_func:
            result = self._launch_view_func()
        elif request_type == 'SessionEndedRequest' and self._session_ended_view_func:
            result = self._session_ended_view_func()
        elif request_type == 'IntentRequest' and self._intent_view_funcs:
            result = self._map_intent_to_view_func(self.request.intent)()
        if result is not None:
            if isinstance(result, _Response):
                return result.render_response()
            return result
        return "", 400

    def _map_intent_to_view_func(self, intent):
        view_func = self._intent_view_funcs[intent.name]
        arg_values = []
        if hasattr(intent, 'slots'):
            slot_data = {}
            for slot in intent.slots:
                slot_data[slot.name] = getattr(slot, 'value', None)
            convert = self._intent_converts[intent.name]
            default = self._intent_defaults[intent.name]
            mapping = self._intent_mappings[intent.name]
            argspec = inspect.getargspec(view_func)
            arg_names = argspec.args
            convert_errors = {}
            for arg_name in arg_names:
                slot_key = mapping.get(arg_name, arg_name)
                arg_value = slot_data.get(slot_key)
                if arg_value is None or arg_value == "":
                    if arg_name in default:
                        default_value = default[arg_name]
                        if isinstance(default_value, collections.Callable):
                            default_value = default_value()
                        arg_value = default_value
                elif arg_name in convert:
                    shorthand_or_function = convert[arg_name]
                    if shorthand_or_function in _converters:
                        shorthand = shorthand_or_function
                        convert_func = _converters[shorthand]
                    else:
                        convert_func = shorthand_or_function
                    try:
                        arg_value = convert_func(arg_value)
                    except Exception as e:
                        convert_errors[arg_name] = e
                arg_values.append(arg_value)
            self.convert_errors = convert_errors
        return partial(view_func, *arg_values)


class YamlLoader(BaseLoader):

    def __init__(self, app, path='templates.yaml'):
        self.path = app.root_path + os.path.sep + path
        self.mapping = {}
        self._reload_mapping()

    def _reload_mapping(self):
        if os.path.isfile(self.path):
            self.last_mtime = os.path.getmtime(self.path)
            with open(self.path) as f:
                self.mapping = yaml.safe_load(f.read())

    def get_source(self, environment, template):
        if not os.path.isfile(self.path):
            return None, None, None
        if self.last_mtime != os.path.getmtime(self.path):
            self._reload_mapping()
        if template in self.mapping:
            source = self.mapping[template]
            return source, None, lambda: source == self.mapping.get(template)
        return TemplateNotFound(template)


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
        if small_image_url is not None:
            card['smallImageUrl'] = small_image_url
        if large_image_url is not None:
            card['largeImageUrl'] = large_image_url
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
            'sessionAttributes': session.attributes
        }
        kw = {}
        if hasattr(session, 'attributes_encoder'):
            json_encoder = session.attributes_encoder
            kwargname = 'cls' if inspect.isclass(json_encoder) else 'default'
            kw[kwargname] = json_encoder
        _dbgdump(response_wrapper, **kw)
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
    """Returns a response object with the appropiate Amazon AudioPlayer Directive.

    The response may include a normal speech attribute in addition to the execution of an AudioPlayer Directive.
    When including a directive in your response, set the type property to the directive you want to send.
    
    @ask.intent('SomeAudioIntent')
    def some_audio_intent():
        stream_url = www.example.com
        return audio(speech).play(stream_url)


    Include directives in the directives array in your response:
    """

    _previous_stream_token = None

    def __init__(self, speech):
        super(audio, self).__init__(speech)
        self._response['directives'] = []
        # self._directive = {}
    
    def play(self, stream_url, behavior='REPLACE_ALL'):
        """Sends a response containing the AudioPlayer.Play Directive to the Alexa Service to stream the audio file.
      
        Arguments:
            stream_url {str} -- url to stream audio from
        
        Keyword Arguments:
            behavior {str} -- Determines whether the stream begins playing immediately, or is added to the queue.
                            options:

                        'REPLACE_ALL': Immediately begin playback of the specified stream
                                     and replace current and enqueued streams.

                        'ENQUEUE': Add the specified stream to the end of the current queue.
                                   This does not impact the currently playing stream.

                        'REPLACE_ENQUEUED': Replace all streams in the queue.
                                            This does not impact the currently playing stream.

                        default: 'REPLACE_ALL'
        """
        directive = {}
        directive['type'] = "AudioPlayer.Play"
        directive['playBehavior'] = behavior
        directive['audioItem'] = self._audio_item(stream_url, behavior)
        self._response['directives'].append(directive)
        return self

    def stop(self):
        """Stops the current audio playback by including the Audio.Player Directive in the response"""
        self._response['directives'].append({'type': 'AudioPlayer.Stop'})
        return self

    def clear_queue(self, stop=False):
        """Clears the audio playback queue.

        You can set this directive to clear the queue without stopping the currently playing stream
        or clear the queue and stop any currently playing stream.
        """

        directive = {}
        directive['type'] = 'AudioPlayer.ClearQueue'
        if stop:
            directive['clearBehavior'] = 'CLEAR_ALL'
        else:
            directive['clearBehavior'] = 'CLEAR_ENQUEUED'

        self._response.append(directive)
        return self








    def _audio_item(self, stream_url, behavior, offset=0):
        audio_item = {'stream': {}}
        stream = audio_item['stream']
        stream['url'] = stream_url
        stream['token'] = str(random.randint(10000, 100000))
        if behavior == 'ENQUEUE':
            stream['expectedPreviousToken'] = audio._previous_stream_token
        stream['offsetInMilliseconds'] = offset
        audio._previous_stream_token = stream['token']
        return audio_item



        





def _directives():
    pass

def _output_speech(speech):
    try:
        xmldoc = ElementTree.fromstring(speech)
        if xmldoc.tag == 'speak':
            return {'type': 'SSML', 'ssml': speech}
    except ElementTree.ParseError as e:
        pass
    return {'type': 'PlainText', 'text': speech}


class _Application(object): pass
class _Intent(object): pass
class _Request(object): pass
class _RequestBody(object): pass
class _Session(object): pass
class _Slot(object): pass
class _User(object): pass
class _Context(object): pass
class _System(object): pass
class _AudioPlayer(object): pass
class _Device(object): pass
class _SupportedInterfaces(object): pass


def _copyattr(src, dest, attr, convert=None):
    if attr in src:
        value = src[attr]
        if convert is not None:
            value = convert(value)
        setattr(dest, attr, value)


def _parse_request_body(request_body_json):
    request_body = _RequestBody()
    request = _parse_request(request_body_json['request'])
    setattr(request_body, 'request', request)
    session = _parse_session(request_body_json['session'])
    setattr(request_body, 'session', session)
    context = _parse_context(request_body_json['context'])
    setattr(request_body, 'context', context)
    setattr(request_body, 'version', request_body_json['version'])
    return request_body


def _parse_context(context_json):
    context = _Context()
    if 'System' in context_json:
        setattr(context, 'System', _parse_system(context_json['System']))
    if 'AudioPlayer' in context_json:
        setattr(context, 'AudioPlayer', _parse_system(context_json['AudioPlayer']))
    return context


def _parse_request(request_json):
    request = _Request()
    _copyattr(request_json, request, 'requestId')
    _copyattr(request_json, request, 'type')
    _copyattr(request_json, request, 'reason')
    _copyattr(request_json, request, 'timestamp', aniso8601.parse_datetime)
    if 'intent' in request_json:
        intent_json = request_json['intent']
        intent = _Intent()
        _copyattr(intent_json, intent, 'name')
        setattr(request, 'intent', intent)
        if 'slots' in intent_json:
            slots = []
            slots_json = intent_json['slots']
            if hasattr(slots_json, 'values') and isinstance(slots_json.values, collections.Callable):
                slot_jsons = list(slots_json.values())
                for slot_json in slot_jsons:
                    slot = _Slot()
                    _copyattr(slot_json, slot, 'name')
                    _copyattr(slot_json, slot, 'value')
                    slots.append(slot)
            setattr(intent, 'slots', slots)
    return request


def _parse_session(session_json):
    session = _Session()
    _copyattr(session_json, session, 'sessionId')
    _copyattr(session_json, session, 'new')
    setattr(session, 'attributes', session_json.get('attributes', {}))
    if 'application' in session_json:
        setattr(session, 'application', _parse_application(session_json['application']))
    if 'user' in session_json:
        setattr(session, 'user', _parse_user(session_json['user']))
    return session


def _parse_application(application_json):
    application = _Application()
    _copyattr(application_json, application, 'applicationId')
    return application


def _parse_audio_player(audio_player_json):
    audio_player = _AudioPlayer()
    _copyattr(audio_player_json, audio_player, 'token')
    _copyattr(audio_player_json, audio_player, 'offsetInMilliseconds')
    _copyattr(audio_player_json, audio_player, 'playerActivity')
    return audio_player


def _parse_device(device_json):
    device = _Device()
    supported_interface_list = device_json['supportedInterfaces'] if 'supportedInterfaces' in device_json else []
    setattr(device, 'supportedInterfaces', _parse_supported_interfaces(supported_interface_list))
    return device


def _parse_supported_interfaces(supported_interface_json):
    interfaces = _SupportedInterfaces()
    for device in supported_interface_json:
        setattr(interfaces, device, True)
    return interfaces


def _parse_system(system_json):
    system = _System()
    if 'application' in system_json:
        setattr(system, 'application', _parse_application(system_json['application']))
    if 'user' in system_json:
        setattr(system, 'user', _parse_user(system_json['user']))
    if 'device' in system_json:
        setattr(system, 'device', _parse_device(system_json['device']))
    return system


def _parse_user(user_json):
    user = _User()
    _copyattr(user_json, user, 'userId')
    _copyattr(user_json, user, 'accessToken')
    return user


def _dbgdump(obj, indent=2, default=None, cls=None):
    msg = json.dumps(obj, indent=indent, default=default, cls=cls)
    logger.debug(msg)

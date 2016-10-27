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
stream_state = LocalProxy(lambda: current_app.ask.stream_state)

_converters = {'date': to_date, 'time': to_time, 'timedelta': to_timedelta}

_streams_to_queue = {}


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
        self._player_request_view_funcs = {}
        self._player_mappings = {}
        self._player_converts = {}
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


    def on_playback_started(self, mapping={'offset': 'offsetInMilliseconds'}):
        """Decorator routes an AudioPlayer.PlaybackStarted Request to the wrapped function.

        Request sent when Alexa begins playing the audio stream previously sent in a Play directive.
        This lets your skill verify that playback began successfully.
        This request is also sent when Alexa resumes playback after pausing it for a voice request.

        @ask.on_playback_started()
        def on_playback_start(url, token, offset):
            log.info('stream from {} started'.format(url))
            log.info('stream has token {}'.format(token))
            log.info('Current position within the stream is {} ms'.format(offset))
        """
        def decorator(f):
            self._player_request_view_funcs['AudioPlayer.PlaybackStarted'] = f
            self._player_mappings['AudioPlayer.PlaybackStarted'] = mapping

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_finished(self, mapping={'offset': 'offsetInMilliseconds'}):
        """Decorator routes an AudioPlayer.PlaybackFinished Request to the wrapped function.

        This type of request is sent when the stream Alexa is playing comes to an end on its own.
        Note: If your skill explicitly stops the playback with the Stop directive,
        Alexa sends PlaybackStopped instead of PlaybackFinished.
        """
        def decorator(f):
            self._player_request_view_funcs['AudioPlayer.PlaybackFinished'] = f
            self._player_mappings['AudioPlayer.PlaybackFinished'] = mapping

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_stopped(self, mapping={'offset': 'offsetInMilliseconds'}, convert={'offset': int}):
        """Decorator routes an AudioPlayer.PlaybackStopped Request to the wrapped function.

        Sent when Alexa stops playing an audio stream in response to one of the following:
            -AudioPlayer.Stop
            -AudioPlayer.Play with a playBehavior of REPLACE_ALL.
            -AudioPlayer.ClearQueue with a clearBehavior of CLEAR_ALL.

        This request is also sent if the user makes a voice request to Alexa, since this temporarily pauses the playback.
        In this case, the playback begins automatically once the voice interaction is complete.

        Note: If playback stops because the audio stream comes to an end on its own,
        Alexa sends PlaybackFinished instead of PlaybackStopped.
        """
        def decorator(f):
            self._player_request_view_funcs['AudioPlayer.PlaybackFinished'] = f
            self._player_mappings['AudioPlayer.PlaybackFinished'] = mapping


            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
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

    @property
    def stream_state(self):
        return getattr(_app_ctx_stack.top, '_ask_stream_state', None)

    @stream_state.setter
    def stream_state(self, value):
        _app_ctx_stack.top._ask_stream_state = value


    def _alexa_request(self, verify=True):
        """Returns the Alexa Request payload sent to the skill.
        
        All requests include the version, context, and request objects at the top level.
        The session object is included for all standard requests,
        but it is not included for AudioPlayer or PlaybackController requests.
        
        Returns:
            request {dict} -- Alxa Request payload
        """
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
        elif 'AudioPlayer' in request_type:
            result = self._map_player_request_to_func(self.request.AudioPlayer)()


        # Not mapped to view func explicitly bc not a request.
        # Intent funcs may be created for amazon intents which invoke the stream update.
        # Therefore, user can implicitly form a response to any event dealing with Audio streams.
        if context.Audioplayer:
            self._sync_stream(context.AudioPlayer)

        if result is not None:
            if isinstance(result, _Response):
                return result.render_response()
            return result
        return "", 400

    def _sync_stream(self, audio_player_object):
        """Syncs stream with Alexa AudioPlayer contained in either the request or context body."""
        stream = _Stream(audio_player_object)
        self.stream_state = stream

    def _map_player_request_to_func(self, audio_player_request):
        """Provides appropiate parameters to the on_playback functions.

        Request values are mapped to on_playback_<request type> functions
        Parameters can recieve the values of the following details:

            url (str) - URL from which audio is being streamed
            token (str) - token belonging to the stream as an identifier
            offset - tracks offset in milliseconds when the PlaybackStarted request is sent.
        """
        self._sync_stream(audio_player_object)
        func = self._player_request_funcs[audio_player_request.type]
        mapping = self._player_mappings[audio_player_request.type]
        convert = self._player_converts[audio_player_request.type]
        argspec = inspect.getargspec(func)
        arg_names = argspec.args
        arg_values = []
        convert_errors = {}
        for arg_name in arg_names:
            request_param = mapping.get(arg_name, arg_name)
            arg_value = getattr(audio_player_request, request_param)

            if arg_name in convert:
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

        return partial(func, *arg_values)

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


class _Stream(object):
    def __init__(self, audio_player_request):
        for attr in audio_player_request:
            _copyattr(audio_player_request, self, attr)

        @property
        def status(self):
            if self.playerActivity and not self.type:
                return self.playerActivity.lower()
            else:
                return self._map_type_to_status()

        def _map_type_to_status(self):
            status = self.type.replace('AudioPlayer.Playback', '')
            return status.lower()

        @property
        def paused(self):
            return self._paused

        def __repr__(self):
            return self.token

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


    LaunchRequest and IntentRequest responses may include outputSpeech in addition to the execution of an AudioPlayer Directive.
    When provoking an audio response, set the directive type with the respective method.

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

    def __init__(self, speech):
        super(audio, self).__init__(speech)
        self._response['directives'] = []
        self._response['shouldEndSession'] = True
        self._directive = {}

        
    def play(self, stream_url, offset=0):
        """Sends a Play Directive to begin playback and replace current and enqueued streams."""

        directive = self._play_directive('REPLACE_ALL')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset)
        self._response['directives'].append(directive)
        return self

    def enqueue(self, stream_url, offset=0):
        """Adds stream to the end of current queue. Does not impact the currently playing stream."""
        directive = self._play_directive('ENQUEUE')
        audio_item = self._audio_item(stream_url=stream_url, offset=offset)
        audio_item['stream']['expectedPreviousToken'] = stream_state.token

        directive['audioItem'] = audio_item
        self._response['directives'].append(directive)
        return self

    def play_next(self, stream_url, offset=0):
        """Replace all streams in the queue but does not impact the currently playing stream."""

        directive = self._play_directive('REPLACE_ENQUEUED')
        directive['audioItem'] = self._audio_item(stream_url=stream_url, offset=offset)
        self._response['directives'].append(directive)
        return self

    def resume(self):
        """Sends Play Directive to resume playback at the paused offset"""
        directive = self._play_directive('REPLACE_ALL')
        directive['audioItem'] = self._audio_item(token=stream_state.token)
        self._response['directives'].append(directive)
        return self

    def _play_directive(self, behavior):
        directive = {}
        directive['type'] = 'AudioPlayer.Play'
        directive['playBehavior'] = behavior
        return directive

    def _audio_item(self, stream_url=None, offset=0, token=None):
        """Builds audioitem to send within an AudioPlayer Directive."""
        audio_item = {'stream': {}}
        stream = audio_item['stream']

        #existing stream
        if token and stream_state.token == token: 
            stream['url'] = stream_state.url
            stream['token'] = stream_state.token
            stream['offsetInMilliseconds'] = stream_state.offsetInMilliseconds

        # new stream
        else:
            stream['url'] = stream_url
            stream['token'] = str(random.randint(10000, 100000))
            stream['offsetInMilliseconds'] = offset

        return audio_item

    def stop(self):
        """Sends AudioPlayer.Stop Directive to stop the current stream playback"""
        self._response['directives'].append({'type': 'AudioPlayer.Stop'})
        return self

    def clear_queue(self, stop=False):
        """Clears queued streams and optionally stops current stream.

        Keyword Arguments:
            stop {bool} -- set True to stop current current stream and clear queued streams.
                           set False to clear queued streams and allow current stream to finish
                           default: {False}
        """

        directive = {}
        directive['type'] = 'AudioPlayer.ClearQueue'
        if stop:
            directive['clearBehavior'] = 'CLEAR_ALL'
        else:
            directive['clearBehavior'] = 'CLEAR_ENQUEUED'

        self._response.append(directive)
        return self


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
    setattr(request_body, 'version', request_body_json['version'])
    try:
        context = _parse_context(request_body_json['context'])
        setattr(request_body, 'context', context)
    except KeyError:
        setattr(request_body, 'context', _Context())

    return request_body


def _parse_context(context_json):
    context = _Context()
    if 'System' in context_json:
        setattr(context, 'System', _parse_system(context_json['System']))
    if 'AudioPlayer' in context_json:  # Audioplayer only within context when it is user-initiated
        setattr(context, 'AudioPlayer', _parse_audio_player(context_json['AudioPlayer']))
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

    # For non user-initiated audioplayer requests,
    # details are not provided under an Context.AudioPlayer object
    # but instead under the request object
    elif 'AudioPlayer.Playback' in request_json['type']:  
        setattr(request, 'AudioPlayer', _parse_audio_player(request_json))
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
    """AudioPlayer details parsed from context or request"""
    audio_player = _AudioPlayer()
    _copyattr(audio_player_json, audio_player, 'token')
    _copyattr(audio_player_json, audio_player, 'offsetInMilliseconds')
    _copyattr(audio_player_json, audio_player, 'playerActivity')

    #audio_player_json will have a type when sent under request object
    _copyattr(audio_player_json, audio_player, 'type')
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

import os
import yaml
import inspect
from functools import wraps, partial

import aniso8601
from werkzeug.contrib.cache import SimpleCache
from werkzeug.local import LocalProxy, LocalStack
from jinja2 import BaseLoader, ChoiceLoader, TemplateNotFound
from flask import current_app, json, request as flask_request, _app_ctx_stack

from . import verifier, logger
from .convert import to_date, to_time, to_timedelta
from .cache import top_stream, set_stream
import collections


def find_ask():
    """
    Find our instance of Ask, navigating Local's and possible blueprints.

    Note: This only supports returning a reference to the first instance
    of Ask found.
    """
    if hasattr(current_app, 'ask'):
        return getattr(current_app, 'ask')
    else:
        if hasattr(current_app, 'blueprints'):
            blueprints = getattr(current_app, 'blueprints')
            for blueprint_name in blueprints:
                if hasattr(blueprints[blueprint_name], 'ask'):
                    return getattr(blueprints[blueprint_name], 'ask')



request = LocalProxy(lambda: find_ask().request)
session = LocalProxy(lambda: find_ask().session)
version = LocalProxy(lambda: find_ask().version)
context = LocalProxy(lambda: find_ask().context)
convert_errors = LocalProxy(lambda: find_ask().convert_errors)
current_stream = LocalProxy(lambda: find_ask().current_stream)
stream_cache = LocalProxy(lambda: find_ask().stream_cache)

from . import models


_converters = {'date': to_date, 'time': to_time, 'timedelta': to_timedelta}


class Ask(object):
    """The Ask object provides the central interface for interacting with the Alexa service.

    Ask object maps Alexa Requests to flask view functions and handles Alexa sessions.
    The constructor is passed a Flask App instance, and URL endpoint.
    The Flask instance allows the convienient API of endpoints and their view functions,
    so that Alexa requests may be mapped with syntax similar to a typical Flask server.
    Route provides the entry point for the skill, and must be provided if an app is given.

    Keyword Arguments:
        app {Flask object} -- App instance - created with Flask(__name__) (default: {None})
        route {str} -- entry point to which initial Alexa Requests are forwarded (default: {None})
        blueprint {Flask blueprint} -- Flask Blueprint instance to use instead of Flask App (default: {None})
        stream_cache {Werkzeug BasicCache} -- BasicCache-like object for storing Audio stream data (default: {SimpleCache})
        path {str} -- path to templates yaml file for VUI dialog (default: {'templates.yaml'})
    """

    def __init__(self, app=None, route=None, blueprint=None, stream_cache=None, path='templates.yaml'):
        self.app = app
        self._route = route
        self._intent_view_funcs = {}
        self._intent_converts = {}
        self._intent_defaults = {}
        self._intent_mappings = {}
        self._launch_view_func = None
        self._session_ended_view_func = None
        self._on_session_started_callback = None
        self._default_intent_view_func = None
        self._player_request_view_funcs = {}
        self._player_mappings = {}
        self._player_converts = {}
        if app is not None:
            self.init_app(app, path)
        elif blueprint is not None:
            self.init_blueprint(blueprint, path)
        if stream_cache is None:
            self.stream_cache = SimpleCache()
        else:
            self.stream_cache = stream_cache

    def init_app(self, app, path='templates.yaml'):
        """Initializes Ask app by setting configuration variables, loading templates, and maps Ask route to a flask view.

        The Ask instance is given the following configuration variables by calling on Flask's configuration:

        `ASK_APPLICATION_ID`:

            Turn on application ID verification by setting this variable to an application ID or a
            list of allowed application IDs. By default, application ID verification is disabled and a
            warning is logged. This variable should be set in production to ensure
            requests are being sent by the applications you specify.
            Default: None

        `ASK_VERIFY_REQUESTS`:

            Enables or disables Alexa request verification, which ensures requests sent to your skill
            are from Amazon's Alexa service. This setting should not be disabled in production.
            It is useful for mocking JSON requests in automated tests.
            Default: True

        ASK_VERIFY_TIMESTAMP_DEBUG:

            Turn on request timestamp verification while debugging by setting this to True.
            Timestamp verification helps mitigate against replay attacks. It relies on the system clock
            being synchronized with an NTP server. This setting should not be enabled in production.
            Default: False
        """
        if self._route is None:
            raise TypeError("route is a required argument when app is not None")

        app.ask = self

        app.add_url_rule(self._route, view_func=self._flask_view_func, methods=['POST'])
        app.jinja_loader = ChoiceLoader([app.jinja_loader, YamlLoader(app, path)])

    def init_blueprint(self, blueprint, path='templates.yaml'):
        """Initialize a Flask Blueprint, similar to init_app, but without the access
        to the application config.

        Keyword Arguments:
            blueprint {Flask Blueprint} -- Flask Blueprint instance to initialize (Default: {None})
            path {str} -- path to templates yaml file, relative to Blueprint (Default: {'templates.yaml'})
        """
        if self._route is not None:
            raise TypeError("route cannot be set when using blueprints!")

        # we need to tuck our reference to this Ask instance into the blueprint object and find it later!
        blueprint.ask = self

        # BlueprintSetupState.add_url_rule gets called underneath the covers and
        # concats the rule string, so we should set to an empty string to allow
        # Blueprint('blueprint_api', __name__, url_prefix="/ask") to result in
        # exposing the rule at "/ask" and not "/ask/".
        blueprint.add_url_rule("", view_func=self._flask_view_func, methods=['POST'])
        blueprint.jinja_loader = ChoiceLoader([YamlLoader(blueprint, path)])

    @property
    def ask_verify_requests(self):
        return current_app.config.get('ASK_VERIFY_REQUESTS', True)

    @property
    def ask_verify_timestamp_debug(self):
        return current_app.config.get('ASK_VERIFY_TIMESTAMP_DEBUG', False)

    @property
    def ask_application_id(self):
        return current_app.config.get('ASK_APPLICATION_ID', None)

    def on_session_started(self, f):
        """Decorator to call wrapped function upon starting a session.

        @ask.on_session_started
        def new_session():
            log.info('new session started')

        Because both launch and intent requests may begin a session, this decorator is used call
        a function regardless of how the session began.

        Arguments:
            f {function} -- function to be called when session is started.
        """
        self._on_session_started_callback = f

    def launch(self, f):
        """Decorator maps a view function as the endpoint for an Alexa LaunchRequest and starts the skill.

        @ask.launch
        def launched():
            return question('Welcome to Foo')

        The wrapped function is registered as the launch view function and renders the response
        for requests to the Launch URL.
        A request to the launch URL is verified with the Alexa server before the payload is
        passed to the view function.

        Arguments:
            f {function} -- Launch view function
        """
        self._launch_view_func = f

        @wraps(f)
        def wrapper(*args, **kw):
            self._flask_view_func(*args, **kw)
        return f

    def session_ended(self, f):
        """Decorator routes Alexa SessionEndedRequest to the wrapped view function to end the skill.

        @ask.session_ended
        def session_ended():
            return "{}", 200

        The wrapped function is registered as the session_ended view function
        and renders the response for requests to the end of the session.

        Arguments:
            f {function} -- session_ended view function
        """
        self._session_ended_view_func = f

        @wraps(f)
        def wrapper(*args, **kw):
            self._flask_view_func(*args, **kw)
        return f

    def intent(self, intent_name, mapping={}, convert={}, default={}):
        """Decorator routes an Alexa IntentRequest and provides the slot parameters to the wrapped function.

        Functions decorated as an intent are registered as the view function for the Intent's URL,
        and provide the backend responses to give your Skill its functionality.

        @ask.intent('WeatherIntent', mapping={'city': 'City'})
        def weather(city):
            return statement('I predict great weather for {}'.format(city))

        Arguments:
            intent_name {str} -- Name of the intent request to be mapped to the decorated function

        Keyword Arguments:
            mapping {dict} -- Maps parameters to intent slots of a different name
                default: {}

            convert {dict} -- Converts slot values to data types before assignment to parameters
                default: {}

            default {dict} --  Provides default values for Intent slots if Alexa reuqest
                returns no corresponding slot, or a slot with an empty value
                default: {}
        """
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

    def default_intent(self, f):
        """Decorator routes any Alexa IntentRequest that is not matched by any existing @ask.intent routing."""
        self._default_intent_view_func = f

        @wraps(f)
        def wrapper(*args, **kw):
            self._flask_view_func(*args, **kw)
        return f

    def on_playback_started(self, mapping={'offset': 'offsetInMilliseconds'}, convert={}, default={}):
        """Decorator routes an AudioPlayer.PlaybackStarted Request to the wrapped function.

        Request sent when Alexa begins playing the audio stream previously sent in a Play directive.
        This lets your skill verify that playback began successfully.
        This request is also sent when Alexa resumes playback after pausing it for a voice request.

        The wrapped view function may accept parameters from the AudioPlayer Request.
        In addition to locale, requestId, timestamp, and type
        AudioPlayer Requests include:
            offsetInMilliseconds - Position in stream when request was sent.
                Not end of stream, often few ms after Play Directive offset.
                This parameter is automatically mapped to 'offset' by default

            token - token of the stream that is nearly finished.

        @ask.on_playback_started()
        def on_playback_start(token, offset):
            logger.info('stream has token {}'.format(token))
            logger.info('Current position within the stream is {} ms'.format(offset))
        """
        def decorator(f):
            self._intent_view_funcs['AudioPlayer.PlaybackStarted'] = f
            self._intent_mappings['AudioPlayer.PlaybackStarted'] = mapping
            self._intent_converts['AudioPlayer.PlaybackStarted'] = convert
            self._intent_defaults['AudioPlayer.PlaybackStarted'] = default

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_finished(self, mapping={'offset': 'offsetInMilliseconds'}, convert={}, default={}):
        """Decorator routes an AudioPlayer.PlaybackFinished Request to the wrapped function.

        This type of request is sent when the stream Alexa is playing comes to an end on its own.

        Note: If your skill explicitly stops the playback with the Stop directive,
        Alexa sends PlaybackStopped instead of PlaybackFinished.

        The wrapped view function may accept parameters from the AudioPlayer Request.
        In addition to locale, requestId, timestamp, and type
        AudioPlayer Requests include:
            offsetInMilliseconds - Position in stream when request was sent.
                Not end of stream, often few ms after Play Directive offset.
                This parameter is automatically mapped to 'offset' by default.

                token - token of the stream that is nearly finished.

        Audioplayer Requests do not include the stream URL, it must be accessed from current_stream.url
        """
        def decorator(f):
            self._intent_view_funcs['AudioPlayer.PlaybackFinished'] = f
            self._intent_mappings['AudioPlayer.PlaybackFinished'] = mapping
            self._intent_converts['AudioPlayer.PlaybackFinished'] = convert
            self._intent_defaults['AudioPlayer.PlaybackFinished'] = default

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_stopped(self, mapping={'offset': 'offsetInMilliseconds'}, convert={}, default={}):
        """Decorator routes an AudioPlayer.PlaybackStopped Request to the wrapped function.

        Sent when Alexa stops playing an audio stream in response to one of the following:
            -AudioPlayer.Stop
            -AudioPlayer.Play with a playBehavior of REPLACE_ALL.
            -AudioPlayer.ClearQueue with a clearBehavior of CLEAR_ALL.

        This request is also sent if the user makes a voice request to Alexa,
        since this temporarily pauses the playback.
        In this case, the playback begins automatically once the voice interaction is complete.

        Note: If playback stops because the audio stream comes to an end on its own,
        Alexa sends PlaybackFinished instead of PlaybackStopped.

        The wrapped view function may accept parameters from the AudioPlayer Request.
        In addition to locale, requestId, timestamp, and type
        AudioPlayer Requests include:
            offsetInMilliseconds - Position in stream when request was sent.
                Not end of stream, often few ms after Play Directive offset.
                This parameter is automatically mapped to 'offset' by default.

                token - token of the stream that is nearly finished.

        Audioplayer Requests do not include the stream URL, it must be accessed from current_stream.url
        """
        def decorator(f):
            self._intent_view_funcs['AudioPlayer.PlaybackStopped'] = f
            self._intent_mappings['AudioPlayer.PlaybackStopped'] = mapping
            self._intent_converts['AudioPlayer.PlaybackStopped'] = convert
            self._intent_defaults['AudioPlayer.PlaybackStopped'] = default

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_nearly_finished(self, mapping={'offset': 'offsetInMilliseconds'}, convert={}, default={}):
        """Decorator routes an AudioPlayer.PlaybackNearlyFinished Request to the wrapped function.

        This AudioPlayer Request sent when the device is ready to receive a new stream.
        To progress through a playlist, respond to this request with an enqueue or play_next audio response.

        **Note** that this request is sent when Alexa is ready to receive a new stream to enqueue, and not
        necessarily when the stream's offset is near the end.
        The request may be sent by Alexa immediately after your skill sends a Play Directive.

        The wrapped view function may accept parameters from the AudioPlayer Request.
        In addition to locale, requestId, timestamp, and type
        This AudioPlayer Request includes:
        AudioPlayer Requests include:
            offsetInMilliseconds - Position in stream when request was sent.
                Not end of stream, often few ms after Play Directive offset.
                This parameter is automatically mapped to 'offset' by default.

                token - token of the stream that is nearly finished.

        Audioplayer Requests do not include the stream URL, and must be accessed from current_stream

        Example usage:

        @ask.on_playback_nearly_finished()
        def play_next_stream():
            audio().enqueue(my_next_song)

        # offsetInMilliseconds is mapped to offset by default for convenience
        @ask.on_playback_nearly_finished()
        def show_request_feedback(offset, token):
            logging.info('Nearly Finished')
            logging.info('Stream at {} ms when Playback Request sent'.format(offset))
            logging.info('Stream holds the token {}'.format(token))
            logging.info('Streaming from {}'.format(current_stream.url))

        # example of changing the default parameter mapping
        @ask.on_playback_nearly_finished(mapping={'pos': 'offsetInMilliseconds', 'stream_token': 'token'})
        def show_request_feedback(pos, stream_token):
            _infodump('Nearly Finished')
            _infodump('Stream at {} ms when Playback Request sent'.format(pos))
            _infodump('Stream holds the token {}'.format(stream_token))
        """
        def decorator(f):
            self._intent_view_funcs['AudioPlayer.PlaybackNearlyFinished'] = f
            self._intent_mappings['AudioPlayer.PlaybackNearlyFinished'] = mapping
            self._intent_converts['AudioPlayer.PlaybackNearlyFinished'] = convert
            self._intent_defaults['AudioPlayer.PlaybackNearlyFinished'] = default

            @wraps(f)
            def wrapper(*args, **kwargs):
                self._flask_view_func(*args, **kwargs)
            return f
        return decorator

    def on_playback_failed(self, mapping={}, convert={}, default={}):
        """Decorator routes an AudioPlayer.PlaybackFailed Request to the wrapped function.

        This AudioPlayer Request sent when Alexa encounters an error when attempting to play a stream.

        The wrapped view function may accept parameters from the AudioPlayer Request.
        In addition to locale, requestId, timestamp, and type

        PlayBackFailed Requests include:
            error - Contains error info under parameters type and message

            token - represents the stream that failed to play.

            currentPlaybackState - Details about the playback activity occurring at the time of the error
                Contains the following parameters:

                    token - represents the audio stream currently playing when the error occurred.
                        Note that this may be different from the value of the request.token property.

                    offsetInMilliseconds - Position in stream when request was sent.
                        Not end of stream, often few ms after Play Directive offset.
                        This parameter is automatically mapped to 'offset' by default.

                    playerActivity - player state when the error occurred
        """
        def decorator(f):
            self._intent_view_funcs['AudioPlayer.PlaybackFailed'] = f
            self._intent_mappings['AudioPlayer.PlaybackFailed'] = mapping
            self._intent_converts['AudioPlayer.PlaybackFailed'] = convert
            self._intent_defaults['AudioPlayer.PlaybackFailed'] = default

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
        return getattr(_app_ctx_stack.top, '_ask_session', models._Field())

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
    def current_stream(self):
        #return getattr(_app_ctx_stack.top, '_ask_current_stream', models._Field())
        user = self._get_user()
        if user:
            stream = top_stream(self.stream_cache, user)
            if stream:
                current = models._Field()
                current.__dict__.update(stream)
                return current
        return models._Field()

    @current_stream.setter
    def current_stream(self, value):
        # assumption 1 is we get a models._Field as value
        # assumption 2 is if someone sets a value, it's resetting the stack
        user = self._get_user()
        if user:
            set_stream(self.stream_cache, user, value.__dict__)

    def _get_user(self):
        if self.context:
            return self.context.get('System', {}).get('user', {}).get('userId')
        return None
                

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
            try:
                application_id = alexa_request_payload['session']['application']['applicationId']
            except KeyError:
                application_id = alexa_request_payload['context'][
                    'System']['application']['applicationId']
            if self.ask_application_id is not None:
                verifier.verify_application_id(application_id, self.ask_application_id)

        return alexa_request_payload

    def _update_stream(self):
        fresh_stream = models._Field()
        fresh_stream.__dict__.update(self.current_stream.__dict__)  # keeps url attribute after stopping stream
        fresh_stream.__dict__.update(self._from_directive())

        context_info = self._from_context()
        if context_info != None:
            fresh_stream.__dict__.update(context_info)

        self.current_stream = fresh_stream
        _dbgdump(current_stream.__dict__)

    def _from_context(self):
        return getattr(self.context, 'AudioPlayer', {})

    def _from_directive(self):
        from_buffer = top_stream(self.stream_cache, self._get_user())
        if from_buffer:
            if self.request.intent and 'PauseIntent' in self.request.intent.name:
                return {}
            return from_buffer
        return {}

    def _flask_view_func(self, *args, **kwargs):
        ask_payload = self._alexa_request(verify=self.ask_verify_requests)
        _dbgdump(ask_payload)
        request_body = models._Field(ask_payload)

        self.request = request_body.request
        self.version = request_body.version
        self.context = getattr(request_body, 'context', models._Field())
        self.session = getattr(request_body, 'session', self.session) # to keep old session.attributes through AudioRequests

        if not self.session:
            self.session = models._Field()
        if not self.session.attributes:
            self.session.attributes = models._Field()

        self._update_stream()

        try:
            if self.session.new and self._on_session_started_callback is not None:
                self._on_session_started_callback()
        except AttributeError:
            pass

        result = None
        request_type = self.request.type

        if request_type == 'LaunchRequest' and self._launch_view_func:
            result = self._launch_view_func()
        elif request_type == 'SessionEndedRequest':
            if self._session_ended_view_func:
                result = self._session_ended_view_func()
            else:
                result = "{}", 200
        elif request_type == 'IntentRequest' and self._intent_view_funcs:
            result = self._map_intent_to_view_func(self.request.intent)()
        elif 'AudioPlayer' in request_type:
            result = self._map_player_request_to_func(self.request.type)()
            # routes to on_playback funcs
            # user can also access state of content.AudioPlayer with current_stream

        if result is not None:
            if isinstance(result, models._Response):
                return result.render_response()
            return result
        return "", 400

    def _map_intent_to_view_func(self, intent):
        """Provides appropiate parameters to the intent functions."""
        if intent.name in self._intent_view_funcs:
            view_func = self._intent_view_funcs[intent.name]
        elif self._default_intent_view_func is not None:
            view_func = self._default_intent_view_func
        else:
            raise NotImplementedError('Intent "{}" not found and no default intent specified.'.format(intent.name))

        argspec = inspect.getargspec(view_func)
        arg_names = argspec.args
        arg_values = self._map_params_to_view_args(intent.name, arg_names)

        return partial(view_func, *arg_values)

    def _map_player_request_to_func(self, player_request_type):
        """Provides appropriate parameters to the on_playback functions."""
        # calbacks for on_playback requests are optional
        view_func = self._intent_view_funcs.get(player_request_type, lambda: None)

        argspec = inspect.getargspec(view_func)
        arg_names = argspec.args
        arg_values = self._map_params_to_view_args(player_request_type, arg_names)

        return partial(view_func, *arg_values)

    def _map_params_to_view_args(self, view_name, arg_names):

        arg_values = []
        convert = self._intent_converts.get(view_name)
        default = self._intent_defaults.get(view_name)
        mapping = self._intent_mappings.get(view_name)

        convert_errors = {}

        request_data = {}
        intent = getattr(self.request, 'intent', None)
        if intent is not None:
            if intent.slots is not None:
                for slot_key in intent.slots.keys():
                    slot_object = getattr(intent.slots, slot_key)
                    request_data[slot_object.name] = getattr(slot_object, 'value', None)

        else:
            for param_name in self.request:
                request_data[param_name] = getattr(self.request, param_name, None)

        for arg_name in arg_names:
            param_or_slot = mapping.get(arg_name, arg_name)
            arg_value = request_data.get(param_or_slot)
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
        return arg_values


class YamlLoader(BaseLoader):

    def __init__(self, app, path):
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


def _dbgdump(obj, indent=2, default=None, cls=None):
    msg = json.dumps(obj, indent=indent, default=default, cls=cls)
    logger.debug(msg)

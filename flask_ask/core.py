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


request = LocalProxy(lambda: current_app.ask.request)
session = LocalProxy(lambda: current_app.ask.session)
version = LocalProxy(lambda: current_app.ask.version)
convert_errors = LocalProxy(lambda: current_app.ask.convert_errors)

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

    """

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
        """Initializes Ask app by setting configuration variables, loading templates, and maps Ask route to a flask view.

        The Ask instance is given the following configuration varables by calling on Flask's configuration:

        `ASK_APPLICATION_ID`:

             Turn on application ID verification by setting this variable to an application ID or a
             list of allowed application IDs. By default, application ID verification is disabled and a
             warning is logged. This variable should be set in production to ensure
             requests are being sent by the applications you specify. 
             Default: None


        `ASK_VERIFY_REQUESTS`:

            Enables or disables Alexa request verification, which ensures requests sent to your skill
            are from Amazon’s Alexa service. This setting should not be disabled in production.
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

        self.ask_verify_requests = app.config.get('ASK_VERIFY_REQUESTS', True)
        self.ask_verify_timestamp_debug = app.config.get('ASK_VERIFY_TIMESTAMP_DEBUG', False)
        self.ask_application_id = app.config.get('ASK_APPLICATION_ID', None)

        app.add_url_rule(self._route, view_func=self._flask_view_func, methods=['POST'])
        app.jinja_loader = ChoiceLoader([app.jinja_loader, YamlLoader(app)])

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
        """Decorator maps a view fucntion as the endpoint for an Alexa LaunchRequest and starts the skill.

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
        """Decorator routes Alexa SessionEndedRequest to the wrapped view fucntion to end the skill.

        @ask.session_ended
        def session_ended():
            return "", 200

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


def _output_speech(speech):
    try:
        xmldoc = ElementTree.fromstring(speech)
        if xmldoc.tag == 'speak':
            return {'type': 'SSML', 'ssml': speech}
    except ElementTree.ParseError as e:
        pass
    return {'type': 'PlainText', 'text': speech}


class _Application(object):
    pass


class _Intent(object):
    pass


class _Request(object):
    pass


class _RequestBody(object):
    pass


class _Session(object):
    pass


class _Slot(object):
    pass


class _User(object):
    pass


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
    return request_body


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
        application_json = session_json['application']
        application = _Application()
        _copyattr(application_json, application, 'applicationId')
        setattr(session, 'application', application)
    if 'user' in session_json:
        user_json = session_json['user']
        user = _User()
        _copyattr(user_json, user, 'userId')
        _copyattr(user_json, user, 'accessToken')
        setattr(session, 'user', user)
    return session


def _dbgdump(obj, indent=2, default=None, cls=None):
    msg = json.dumps(obj, indent=indent, default=default, cls=cls)
    logger.debug(msg)

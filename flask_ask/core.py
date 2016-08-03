import os
import yaml
import inspect
import collections
from functools import wraps, partial
from xml.etree import ElementTree

import aniso8601
from werkzeug.local import LocalProxy
from jinja2 import BaseLoader, ChoiceLoader, TemplateNotFound
from flask import current_app, json, request as flask_request, _app_ctx_stack

import verifier
from . import logger, log_json
from .convert import to_date, to_time, to_timedelta
from .models import Response, parse_request_body

request = LocalProxy(lambda: current_app.ask.request)
session = LocalProxy(lambda: current_app.ask.session)
version = LocalProxy(lambda: current_app.ask.version)
state = LocalProxy(lambda: current_app.ask.state)
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
        self.ask_verify_timestamp_debug = app.config.get('ASK_VERIFY_TIMESTAMP_DEBUG', False)
        self.ask_application_id = app.config.get('ASK_APPLICATION_ID', None)
        if self.ask_application_id is None:
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

    def intent(self, intent_name, state=None, mapping={}, convert={}, default={}):
        def decorator(f):
            intent_id = intent_name, state
            self._intent_view_funcs[intent_id] = f
            self._intent_mappings[intent_id] = mapping
            self._intent_converts[intent_id] = convert
            self._intent_defaults[intent_id] = default

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
    def convert_errors(self):
        return getattr(_app_ctx_stack.top, '_ask_convert_errors', None)

    @convert_errors.setter
    def convert_errors(self, value):
        _app_ctx_stack.top._ask_convert_errors = value

    @property
    def state(self):
        return getattr(_app_ctx_stack.top, '_ask_state', None)

    @state.setter
    def state(self, value):
        _app_ctx_stack.top._ask_state = value

    def _verified_request(self):
        raw_body = flask_request.data
        cert_url = flask_request.headers['Signaturecertchainurl']
        signature = flask_request.headers['Signature']
        # load certificate - this verifies a the certificate url and format under the hood
        cert = verifier.load_certificate(cert_url)
        # verify signature
        verifier.verify_signature(cert, signature, raw_body)
        # verify timestamp
        ask_payload = json.loads(raw_body)
        timestamp = aniso8601.parse_datetime(ask_payload['request']['timestamp'])
        if not current_app.debug or self.ask_verify_timestamp_debug:
            verifier.verify_timestamp(timestamp)
        # verify application id
        application_id = ask_payload['session']['application']['applicationId']
        if self.ask_application_id is not None:
            verifier.verify_application_id(application_id, self.ask_application_id)
        return ask_payload

    def _flask_view_func(self, *args, **kwargs):
        ask_payload = self._verified_request()
        log_json(ask_payload)
        request_body = parse_request_body(ask_payload)
        self.request = request_body.request
        self.session = request_body.session
        self.version = request_body.version
        self.state = State(self.session)
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
            if isinstance(result, Response):
                return result.render_response()
            return result
        return "", 400

    def _map_intent_to_view_func(self, intent):
        intent_id = intent.name, self.state.current
        view_func = self._intent_view_funcs[intent_id]
        view_params = []
        if hasattr(intent, 'slots'):
            view_params = self._map_slots_to_view_params(intent_id, intent.slots, view_func)

        return partial(view_func, *view_params)

    def _map_slots_to_view_params(self, intent_id, slots, view_func):
        convert = self._intent_converts[intent_id]
        default = self._intent_defaults[intent_id]
        mapping = self._intent_mappings[intent_id]
        argspec = inspect.getargspec(view_func)
        arg_names = argspec.args
        
        slot_data = {}
        for slot in slots:
            slot_data[slot.name] = getattr(slot, 'value', None)

        view_params = []
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
            view_params.append(arg_value)
        self.convert_errors = convert_errors
        return view_params


class State(object):
    SESSION_KEY = '_ask_state_id'

    def __init__(self, session):
        self._session = session
        self.current = session.attributes.get(State.SESSION_KEY)

    def transition(self, state_id):
        self.current = state_id
        self._session.attributes[State.SESSION_KEY] = self.current


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

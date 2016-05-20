import os
import yaml
import inspect
from functools import wraps, partial
from xml.etree import ElementTree

import aniso8601
from werkzeug.local import LocalProxy
from jinja2 import BaseLoader, ChoiceLoader, TemplateNotFound
from flask import current_app, json, request as flask_request, _app_ctx_stack

import verifier
from . import logger
from .convert import to_date, to_time, to_timedelta


# config defaults
ASK_ROUTE = '/_ask'
ASK_APPLICATION_ID = None
ASK_APPLICATION_IDS = []
ASK_VERIFY_TIMESTAMP_DEBUG = False

request = LocalProxy(lambda: current_app.ask._request)
session = LocalProxy(lambda: current_app.ask._session)

_converters = {'date': to_date, 'time': to_time, 'timedelta': to_timedelta}


class Ask(object):

    def __init__(self, app=None):
        self.app = app
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
        app.ask = self
        self.ask_route = app.config.get('ASK_ROUTE', ASK_ROUTE)
        self.ask_application_id = app.config.get('ASK_APPLICATION_ID', ASK_APPLICATION_ID)
        self.ask_application_ids = app.config.get('ASK_APPLICATION_IDS', ASK_APPLICATION_IDS)
        self.ask_verify_timestamp_debug = app.config.get('ASK_VERIFY_TIMESTAMP_DEBUG', ASK_VERIFY_TIMESTAMP_DEBUG)
        if self.ask_application_id is None and not self.ask_application_ids:
            logger.warning("Neither the ASK_APPLICATION_ID or ASK_APPLICATION_IDS " +
                "configuration parameters have been set. Application ID will not be verified.")
        app.add_url_rule(self.ask_route, view_func=self._flask_view_func, methods=['POST'])
        app.jinja_loader = ChoiceLoader([app.jinja_loader, YamlLoader(app)])

    def on_session_started(self, f):
        self._on_session_started_callback = f

    def launch(self, f):
        self._launch_view_func = f
        wraps(f, self._flask_view_func)
        return f

    def session_ended(self, f):
        self._session_ended_view_func = f
        wraps(f, self._flask_view_func)
        return f

    def intent(self, intent_name, mapping={}, convert={}, default={}):
        def decorator(f):
            self._intent_view_funcs[intent_name] = f
            self._intent_mappings[intent_name] = mapping
            self._intent_converts[intent_name] = convert
            self._intent_defaults[intent_name] = default
            wraps(f, self._flask_view_func)
            return f
        return decorator

    def _flask_view_func(self, *args, **kwargs):
        ask_payload = self._verified_request()
        _dbgdump(ask_payload)
        self._request = _parse_request(ask_payload['request'])
        self._session = _parse_session(ask_payload['session'])
        if self._session is not None and self._session.new and self._on_session_started_callback is not None:
            self._on_session_started_callback()
        if self._request is not None:
            result = None
            request_type = self._request.type
            if request_type == 'LaunchRequest' and self._launch_view_func:
                result = self._launch_view_func()
            elif request_type == 'SessionEndedRequest' and self._session_ended_view_func:
                result = self._session_ended_view_func()
            elif request_type == 'IntentRequest' and self._intent_view_funcs:
                result = self._map_intent_to_view_func(self._request.intent)()
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
            for arg_name in arg_names:
                slot_key = mapping.get(arg_name, arg_name)
                arg_value = slot_data.get(slot_key)
                if arg_value is None or arg_value == "":
                    if arg_name in default:
                        default_value = default[arg_name]
                        if callable(default_value):
                            default_value = default_value()
                        arg_value = default_value
                elif arg_name in convert:
                    shorthand_or_function = convert[arg_name]
                    if shorthand_or_function in _converters:
                        shorthand = shorthand_or_function
                        convert_func = _converters[shorthand]
                    else:
                        convert_func = shorthand_or_function
                    arg_value = convert_func(arg_value)
                arg_values.append(arg_value)
        return partial(view_func, *arg_values)

    def _verified_request(self):
        raw_body = flask_request.data
        cert_url = flask_request.headers['Signaturecertchainurl']
        signature = flask_request.headers['Signature']

        cert = verifier.load_certificate(cert_url)
        verifier.verify_signature(cert, signature, raw_body)

        ask_payload = json.loads(raw_body)
        timestamp = aniso8601.parse_datetime(ask_payload['request']['timestamp'])
        if not current_app.debug or self.ask_verify_timestamp_debug:
            verifier.verify_timestamp(timestamp)

        application_id = ask_payload['session']['application']['applicationId']
        if self.ask_application_id is not None or self.ask_application_ids:
            verifier.verify_application_id(application_id, self.ask_application_id, self.ask_application_ids)

        return ask_payload

    @property
    def _request(self):
        return getattr(_app_ctx_stack.top, '_ask_request', None)

    @_request.setter
    def _request(self, value):
        _app_ctx_stack.top._ask_request = value

    @property
    def _session(self):
        return getattr(_app_ctx_stack.top, '_ask_session', None)

    @_session.setter
    def _session(self, value):
        _app_ctx_stack.top._ask_session = value


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
        if card_small_image_url is not None:
            card['smallImageUrl'] = card_small_image_url
        if card_large_image_url is not None:
            card['largeImageUrl'] = card_large_image_url
        self._response['card'] = card
        return self

    def render_response(self):
        response_wrapper = {
            'version': '1.0',
            'response': self._response,
            'sessionAttributes': session.attributes
        }
        kw = {}
        if hasattr(session, 'json_encoder'):
            json_encoder = session.json_encoder
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
        reprompt = { 'outputSpeech': _output_speech(reprompt) }
        self._response['reprompt'] = reprompt
        return self


class _Application(object): pass
class _User(object): pass
class _Session(object): pass
class _Request(object): pass
class _Intent(object): pass
class _Slot(object): pass


def _output_speech(speech):
    try:
        xmldoc = ElementTree.fromstring(speech)
        if xmldoc.tag == 'speak':
            return { 'type': 'SSML', 'ssml': speech }
    except ElementTree.ParseError, e:
        pass
    return { 'type': 'PlainText', 'text': speech }


def _parse_session(obj):
    session = _Session()
    session.new = obj['new']
    session.sessionId = obj['sessionId']
    session.application = _Application()
    session.application.applicationId = obj['application']['applicationId']
    session.attributes = obj.get('attributes', {})
    session.user = _User()
    session.user.userId = obj['user']['userId']
    if 'accessToken' in obj['user']:
        session.user.accessToken = obj['user']['accessToken']
    return session


def _parse_request(obj):
    request = _Request()
    request.requestId = obj['requestId']
    request.timestamp = aniso8601.parse_datetime(obj['timestamp'])
    request.type = obj['type']
    if 'intent' in obj:
        intent_obj = obj['intent']
        intent = _Intent()
        intent.name = intent_obj['name']
        intent.slots = []
        request.intent = intent
        if 'slots' in intent_obj:
            for slot_obj in intent_obj['slots'].values():
                slot = _Slot()
                slot.name = slot_obj['name']
                slot.value = slot_obj.get('value')
                intent.slots.append(slot)
    return request


def _dbgdump(obj, indent=2, default=None, cls=None):
    msg = json.dumps(obj, indent=indent, default=default, cls=cls)
    logger.warn(msg)

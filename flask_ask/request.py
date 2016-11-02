

from pprint import pprint


def _copyattr(src, dest, attr, convert=None):
    if attr in src:
        value = src[attr]
        if convert is not None:
            value = convert(value)
        setattr(dest, attr, value)


class _RequestField():
    """Holds the request field as an aobject with attributes."""
    def __init__(self, request_json={}):
        # if request_json is not None:
        for key in request_json:
            setattr(self, key, request_json[key])

            # self.__dict__.update(request_json)

        for attr in self.__dict__:
            attr_val = getattr(self, attr)
            if type(attr_val) is dict:
                # print(attr)
                setattr(self, attr, _RequestField(attr_val))


class Request():
    def __init__(self, request_body_json):
        self._parse_request_body(request_body_json)
        pprint(self)
        # print(self.request.__dict__)
        # print(self.session.__dict__)
        # print('\n'*3)

    def __repr__(self):
        rep = {}
        for attr in self.__dict__:
            rep[attr] = getattr(self, attr)
        return str(rep)

    def _parse_request_body(self, request_body_json):
        # private attributes hold the json of the request field
        self._body = request_body_json
        self._version = self._body.get('version')
        self._request = self._body.get('request')
        self._context = self._body.get('context')
        self._session = self._body.get('session')
        print(self._session)
        print('\n'*3)

    @property
    def body(self):
        return self._body
    @property
    def version(self):
        return self._version

    @property
    def context(self):
        return _RequestField(self._context)

    @property
    def request(self):
        return _RequestField(self._request)

    @property
    def session(self):
        return _RequestField(self._session)

#     @property
#     def intent(self):
#         intent_json = getattr(self.request, 'intent', None)
#         intent = _RequestField(intent_json)
#         if getattr(intent_json, 'slots', None):





    
    
    
    
#     @property
#     def application(self):
#         return self._application
    
#     @property
#     def audio_player(self):
#         return self._audio_player

#     @property
#     def system(self):
#         return self._system

#     @property
#     def user(self):
#         return self._user

#     @property
#     def device(self):
#         return self._device

    


#     def _parse_request(self):
#         return _RequestField(self._request)

        
        

#     def _parse_request(self):
#         _copyattr(self._body, self.request, 'requestId')
#         _copyattr(request_json, request, 'type')
#         _copyattr(request_json, request, 'reason')
#         _copyattr(request_json, request, 'timestamp', aniso8601.parse_datetime)

#         if 'intent' in request_json:
#             intent_json = request_json['intent']
#             intent = _Intent()
#             _copyattr(intent_json, intent, 'name')
#             setattr(request, 'intent', intent)
#             if 'slots' in intent_json:
#                 slots = []
#                 slots_json = intent_json['slots']
#                 if hasattr(slots_json, 'values') and isinstance(slots_json.values, collections.Callable):
#                     slot_jsons = list(slots_json.values())
#                     for slot_json in slot_jsons:
#                         slot = _Slot()
#                         _copyattr(slot_json, slot, 'name')
#                         _copyattr(slot_json, slot, 'value')
#                         slots.append(slot)
#                 setattr(intent, 'slots', slots)

#         # For non user-initiated audioplayer requests,
#         # details are provided under the Request object, not the Context.AudioPlayer object
#         if 'AudioPlayer.Playback' in request_json['type']:
#             _copyattr(request_json, request, 'token')
#             _copyattr(request_json, request, 'offsetInMilliseconds')
#             _copyattr(request_json, request, 'currentPlaybackState')

#         return request
    

    










# def _parse_request_body(request_body_json):
#     request_body = _RequestBody()
#     setattr(request_body, 'version', request_body_json['version'])

#     request = _parse_request(request_body_json['request'])
#     setattr(request_body, 'request', request)

#     try:
#         context = _parse_context(request_body_json['context'])
#         setattr(request_body, 'context', context)
#     except KeyError:
#         setattr(request_body, 'context', _Context())

#     # session object not included in AudioPlayer or Playback requests
#     try:
#         session = _parse_session(request_body_json['session'])
#         setattr(request_body, 'session', session)
#     except KeyError:
#         setattr(request_body, 'session', _Session())

#     return request_body


# def _parse_context(context_json):
#     context = _Context()
#     if 'System' in context_json:
#         setattr(context, 'System', _parse_system(context_json['System']))
#     if 'AudioPlayer' in context_json:  # AudioPlayer only within context when it is user-initiated
#         setattr(context, 'AudioPlayer', _parse_audio_player(context_json['AudioPlayer']))

#     return context


# def _parse_request(request_json):
#     request = _Request()
#     _copyattr(request_json, request, 'requestId')
#     _copyattr(request_json, request, 'type')
#     _copyattr(request_json, request, 'reason')
#     _copyattr(request_json, request, 'timestamp', aniso8601.parse_datetime)
#     if 'intent' in request_json:
#         intent_json = request_json['intent']
#         intent = _Intent()
#         _copyattr(intent_json, intent, 'name')
#         setattr(request, 'intent', intent)
#         if 'slots' in intent_json:
#             slots = []
#             slots_json = intent_json['slots']
#             if hasattr(slots_json, 'values') and isinstance(slots_json.values, collections.Callable):
#                 slot_jsons = list(slots_json.values())
#                 for slot_json in slot_jsons:
#                     slot = _Slot()
#                     _copyattr(slot_json, slot, 'name')
#                     _copyattr(slot_json, slot, 'value')
#                     slots.append(slot)
#             setattr(intent, 'slots', slots)

#     # For non user-initiated audioplayer requests,
#     # details are provided under the Request object, not the Context.AudioPlayer object
#     if 'AudioPlayer.Playback' in request_json['type']:
#         _copyattr(request_json, request, 'token')
#         _copyattr(request_json, request, 'offsetInMilliseconds')
#         _copyattr(request_json, request, 'currentPlaybackState')

#     return request


# def _parse_session(session_json):
#     session = _Session()
#     _copyattr(session_json, session, 'sessionId')
#     _copyattr(session_json, session, 'new')
#     setattr(session, 'attributes', session_json.get('attributes', {}))
#     if 'application' in session_json:
#         setattr(session, 'application', _parse_application(session_json['application']))
#     if 'user' in session_json:
#         setattr(session, 'user', _parse_user(session_json['user']))
#     return session


# def _parse_application(application_json):
#     application = _Application()
#     _copyattr(application_json, application, 'applicationId')
#     return application


# def _parse_audio_player(audio_player_json):
#     """AudioPlayer details parsed from context."""
#     audio_player = _AudioPlayer()

#     _copyattr(audio_player_json, audio_player, 'token')
#     _copyattr(audio_player_json, audio_player, 'offsetInMilliseconds')
#     _copyattr(audio_player_json, audio_player, 'playerActivity')

#     return audio_player


# def _parse_device(device_json):
#     device = _Device()
#     supported_interface_list = device_json[
#         'supportedInterfaces'] if 'supportedInterfaces' in device_json else []
#     setattr(device, 'supportedInterfaces', _parse_supported_interfaces(supported_interface_list))
#     return device


# def _parse_supported_interfaces(supported_interface_json):
#     interfaces = _SupportedInterfaces()
#     for device in supported_interface_json:
#         setattr(interfaces, device, True)
#     return interfaces


# def _parse_system(system_json):
#     system = _System()
#     if 'application' in system_json:
#         setattr(system, 'application', _parse_application(system_json['application']))
#     if 'user' in system_json:
#         setattr(system, 'user', _parse_user(system_json['user']))
#     if 'device' in system_json:
#         setattr(system, 'device', _parse_device(system_json['device']))
#     return system


# def _parse_user(user_json):
#     user = _User()
#     _copyattr(user_json, user, 'userId')
#     _copyattr(user_json, user, 'accessToken')
#     return user
Handling Requests
=================

With the Alexa Skills Kit, spoken phrases are mapped to actions executed on a server. Alexa converts
speech into JSON and delivers the JSON to your application.
For example, the phrase:

    "Alexa, Tell HelloApp to say hi to John"

produces JSON like the following:

.. code-block:: javascript

    "request": {
      "intent": {
        "name": "HelloIntent",
        "slots": {
          "firstname": {
            "name": "firstname",
            "value": "John"
          }
        }
      }
      ...
    }

Parameters called 'slots' are defined and parsed out of speech at runtime.
For example, the spoken word 'John' above is parsed into the slot named ``firstname`` with the ``AMAZON.US_FIRST_NAME``
data type.

For detailed information, see
`Handling Requests Sent by Alexa <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/handling-requests-sent-by-alexa>`_
on the Amazon developer website.

This section shows how to process Alexa requests with Flask-Ask. It contains the following subsections:

.. contents::
   :local:
   :backlinks: none

Mapping Alexa Requests to View Functions
----------------------------------------
Flask-Ask ships with decorators to map Alexa requests to view functions.

The ``launch`` decorator handles launch requests::

    @ask.launch
    def launched():
        return question('Welcome to Foo')

The ``intent`` decorator handles intent requests::

    @ask.intent('HelloWorldIntent')
    def hello():
        return statement('Hello, world')

The ``session_ended`` decorator is for the session ended request::

    @ask.session_ended
    def session_ended():
        return "", 200

Launch and intent requests can both start sessions. Avoid duplicate code with the ``on_session_started`` callback::

    @ask.on_session_started
    def new_session():
        log.info('new session started')


Mapping Intent Slots to View Function Parameters
------------------------------------------------
Tell Flask-Ask when slot and view function parameter names differ with ``mapping``::

    @ask.intent('WeatherIntent', mapping={'city': 'City'})
    def weather(city):
        return statement('I predict great weather for {}'.format(city))

Above, the parameter ``city`` is mapped to the slot ``City``.

Parameters are assigned a value of ``None`` if the Alexa service:

* Does not return a corresponding slot in the request
* Includes a corresponding slot without its ``value`` attribute
* Includes a corresponding slot with an empty ``value`` attribute (e.g. ``""``)

Use the ``default`` parameter for default values instead of ``None``. The default itself should be a
literal or a callable that resolves to a value. The next example shows the literal ``'World'``::

    @ask.intent('HelloIntent', default={'name': 'World'})
    def hello(name):
        return statement('Hello, {}'.format(name))

When slot values are available, they're always assigned to parameters as strings. Convert to other Python
data types with ``convert``. ``convert`` is a ``dict`` that maps parameter names to callables::

    @ask.intent('AddIntent', convert={'x': int, 'y': int})
    def add(x, y):
        z = x + y
        return statement('{} plus {} equals {}'.format(x, y, z))


Above, ``x`` and ``y`` will both be passed to ``int()`` and thus converted to ``int`` instances.

Flask-Ask provides convenient API constants for Amazon ``AMAZON.DATE``, ``AMAZON.TIME``, and ``AMAZON.DURATION``
types exist since those are harder to build callables against. Instead of trying to define functions that work with
inputs like those in Amazon's
`documentation <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interaction-model-reference#Slot%20Types>`_,
just pass the strings in the second column below:

=================== =============== ======================
Amazon Data Type    String          Python Data Type
=================== =============== ======================
``AMAZON.DATE``     ``'date'``      ``datetime.date``
``AMAZON.TIME``     ``'time'``      ``datetime.time``
``AMAZON.DURATION`` ``'timedelta'`` ``datetime.timedelta``
=================== =============== ======================

For example::

    convert={'date': 'date'}

will convert a ``date`` string such as ``'2015-11-24'``, ``'2015-W48-WE'``, or ``'201X'`` into an appropriate
Python ``datetime.date``.


``request``, ``session``, and ``version`` Context Locals
--------------------------------------------------------
An Alexa
`request payload <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference#Request%20Format>`_
has three top-level elements: ``request``, ``session``, and ``version``. Like Flask, Flask-Ask provides `context
locals <http://werkzeug.pocoo.org/docs/0.11/local/>`_ that spare you from having to add these as extra parameters to
your functions. However, the ``request`` and ``session`` objects are distinct from Flask's ``request`` and ``session``.
Flask-Ask's ``request`` and ``session`` correspond to the Alexa request payload components while Flask's correspond
to lower-level HTTP constructs.

To use Flask-Ask's context locals, just import them::

    from flask import App
    from flask.ext.ask import Ask, request, session, version

    app = Flask(__name__)
    ask = Ask(app)
    log = logging.getLogger()

    @ask.intent('ExampleIntent')
    def example():
        log.info("Request ID: {}".format(request.requestId))
        log.info("Request Type: {}".format(request.type))
        log.info("Request Timestamp: {}".format(request.timestamp))
        log.info("Session New?: {}".format(session.new))
        log.info("User ID: {}".format(session.user.userId))
        log.info("Alexa Version: {}".format(version))
        ...

If you want to use both Flask and Flask-Ask context locals in the same module, use ``import as``::

    from flask import App, request, session
    from flask.ext.ask import (
        Ask,
        request as ask_request,
        session as ask_session,
        version
    )

For a complete reference on ``request`` and ``session`` fields, see the
`JSON Interface Reference for Custom Skills <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference>`_
in the Alexa Skills Kit documentation.

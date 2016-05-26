====================
Flask-Ask
====================
Flask-Ask makes it easy to write Amazon Echo apps with `Flask <http://flask.pocoo.org>`_ and the
`Alexa Skills Kit <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit>`_.

Flask-Ask:

* Verifies Alexa request signatures
* Provides decorators that map ASK requests to view functions
* Helps construct ask and tell responses, reprompts and cards
* Makes session management easy
* Allows for the separation of code and speech through Jinja templates

.. contents::
   :local:
   :backlinks: none

Installation
============
To install Flask-Ask::

  pip install flask-ask


A Minimal Voice User Interface
==============================
A Flask-Ask application looks like this:

.. code-block:: python

  from flask import Flask, render_template
  from flask.ext.ask import Ask, statement

  app = Flask(__name__)
  ask = Ask(app)

  @ask.intent('HelloIntent')
  def hello(firstname):
      text = render_template('hello', firstname=firstname)
      return statement(text).simple_card('Hello', text)

  if __name__ == '__main__':
      app.run(debug=True)

In the code above:

* The ``intent`` decorator maps an
  `intent request <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/handling-requests-sent-by-alexa#Types of Requests Sent by Alexa>`_
  named ``HelloIntent`` to a view function ``hello``.
* The intent's ``firstname`` slot is implicitly mapped to ``hello``'s ``firstname`` parameter.
* Jinja templates are supported. Internally, templates are loaded from a YAML file (discussed further below).
* Lastly, a builder constructs a spoken response and displays a contextual card in the Alexa smartphone/tablet app.

Since Alexa responses are usually short phrases, it's convenient to put them in the same file.
Flask-Ask has a `Jinja template loader <http://jinja.pocoo.org/docs/dev/api/#loaders>`_ that loads
multiple templates from a single YAML file. For example, here's a template that supports the minimal voice interface
above.Templates are stored in a file called `templates.yaml` located in the application root:

.. code-block:: yaml

  hello: Hello, {{ firstname }}

There are more code and template examples in the `samples directory <https://github.com/johnwheeler/flask-ask>`_ on
Github.

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

This section shows how to process Alexa requests with Flask-Ask.


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


``request``, ``session``, and ``version`` context locals
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


Building Responses
==================
The two primary constructs in Flask-Ask for creating responses are ``statement`` and ``question``.

Statements terminate Echo sessions. The user is free to start another session, but Alexa will have no memory of it
(unless persistence is programmed separately on the server with a database or the like).

A ``question``, on the other hand, prompts the user for additional speech and keeps a session open.
This session is similar to an HTTP session but the implementation is different. Since your application is
communicating with the Alexa service instead of a browser, there are no cookies or local storage. Instead, the
session is maintained in both the request and response JSON structures. In addition to the session component of
questions, questions also allow a ``reprompt``, which is typically a rephrasing of the question if user did not answer
the first time.


Telling with ``statement``
--------------------------
``statement`` closes the session::

  @ask.intent('AllYourBaseIntent')
  def all_your_base():
      return statement('All your base are belong to us')


Asking with ``question``
------------------------
Asking with ``question`` prompts the user for a response while keeping the session open::

  @ask.intent('AppointmentIntent')
  def make_appointment():
      return question("What day would you like to make an appointment for?")

If the user doesn't respond, encourage them by rephrasing the question with ``reprompt``::

  @ask.intent('AppointmentIntent')
  def make_appointment():
      return question("What day would you like to make an appointment for?") \
        .reprompt("I didn't get that. When would you like to be seen?")


Session management
------------------

The ``session`` context local has an ``attributes`` dictionary for persisting information across requests::

    session.attributes['city'] = "San Francisco"

When the response is rendered, the session attributes are automatically copied into its ``sessionAttributes``.
The renderer looks for an ``attribute_encoder`` attribute on the session. The ``attribute_encoder`` can either be
and instance of ``json.JSONEncoder`` or a function. Here's an example of a function::

    def _json_date_handler(obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

    session.attributes[SESSION_DATE] = date
    session.attributes_encoder = _json_date_handler

See the `json.dump documentation <https://docs.python.org/2/library/json.html#json.dump>`_ for for details about
that method's ``cls`` and ``default`` parameters. Flask-Ask's response render determines which one to set when it
calls ``json.dumps`` automatically.


Automatic handling of Plaintext and SSML
----------------------------------------
The Alexa Skills Kit supports plain text or
`SSML <https://en.wikipedia.org/wiki/Speech_Synthesis_Markup_Language>`_ outputs. Flask-Ask automatically
detects if your speech text contains SSML by attempting to parse it into XML, and checking
if the root element is ``speak``::

  try:
      xmldoc = ElementTree.fromstring(text)
      if xmldoc.tag == 'speak':
          # output type is 'SSML'
  except ElementTree.ParseError:
      pass
  # output type is 'PlainText'


Displaying Cards in the Alexa Smartphone/Tablet App
---------------------------------------------------
In addition to speaking back, Flask-Ask can display contextual cards in the Alexa smartphone/tablet app. All three
of the Alexa Skills Kit card types are supported.

Simple cards display a title and message::

  @ask.intent('AllYourBaseIntent')
  def all_your_base():
      return statement('All your base are belong to us') \
        .simple_card(title='CATS says...', content='Make your time')

Standard cards are like simple cards but they also support small and large image URLs::

  @ask.intent('AllYourBaseIntent')
  def all_your_base():
      return statement('All your base are belong to us') \
          .standard_card(title='CATS says...',
                         text='Make your time',
                         small_image_url='https://example.com/small.png',
                         large_image_url='https://example.com/large.png')


Jinja Templates
---------------
You can also use Jinja templates. Define them in a YAML file named `templates.yaml` inside your application root::

  @ask.intent('RBelongToUsIntent')
  def all_your_base():
      notice = render_template('all_your_base_msg', who='us')
      return statement(notice)

.. code-block:: yaml

      all_your_base_msg: All your base are belong to {{ who }}

      multiple_line_example: |
        I am a multi-line template. My content spans more than one line,
        so there's a pipe and a newline that separates my name and value.


Configuration
=============
Flask-Ask exposes the following configuration variables:

============================ ============================================================================================
`ASK_ROUTE`                  The Flask route the Alexa service will send requests to. This corresponds to the path
                             portion of the HTTPS endpoint specified in the Amazon Developer portal under the skill's
                             "Configuration" section. This route is created implicitly by Flask-Ask and is not exposed
                             to the developer. You really only need to change this setting if the default value
                             collides with an existing route. **Default:**  ``/_ask``
`ASK_APPLICATION_ID`         Turn on application ID verification by setting this variable to the application ID Amazon
                             assigned your application. By default, application ID verification is disabled and a
                             warning is logged. This variable or the one below should be set in production to ensure
                             requests are being sent by the application you specify. This variable is for convenience
                             if you're only accepting requests from one application. Otherwise, use the variable
                             below. **Default:** None
`ASK_APPLICATION_IDS`        Turn on application ID verification by setting this variable to a list of allowed
                             application IDs. By default, application ID verification is disabled and a
                             warning is logged. This variable or the one above should be set in production to ensure
                             requests are being sent by the applications you specify. This is same as the variable above
                             but allows a single skill to respond to multiple applications. **Default:** ``[]``
`ASK_VERIFY_TIMESTAMP_DEBUG` Turn on request timestamp verification while debugging by setting this to ``True``.
                             Timestamp verification helps mitigate against
                             `replay attacks <https://en.wikipedia.org/wiki/Replay_attack>`_. It
                             relies on the system clock being synchronized with an NTP server. This setting should not
                             be enabled in production. **Default:** ``False``
============================ ============================================================================================

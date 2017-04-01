Building Responses
==================

📼 A `Building Responses with Flask-Ask video <https://alexatutorial.com/2>`_ is available on
`AlexaTutorial.com <https://alexatutorial.com>`_.

The two primary constructs in Flask-Ask for creating responses are ``statement`` and ``question``.

Statements terminate Echo sessions. The user is free to start another session, but Alexa will have no memory of it
(unless persistence is programmed separately on the server with a database or the like).

A ``question``, on the other hand, prompts the user for additional speech and keeps a session open.
This session is similar to an HTTP session but the implementation is different. Since your application is
communicating with the Alexa service instead of a browser, there are no cookies or local storage. Instead, the
session is maintained in both the request and response JSON structures. In addition to the session component of
questions, questions also allow a ``reprompt``, which is typically a rephrasing of the question if user did not answer
the first time.

This sections shows how to build responses with Flask-Ask. It contains the following subsections:

.. contents::
   :local:
   :backlinks: none

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


Session Management
------------------

The ``session`` context local has an ``attributes`` dictionary for persisting information across requests::

    session.attributes['city'] = "San Francisco"

When the response is rendered, the session attributes are automatically copied over into
the response's ``sessionAttributes`` structure.

The renderer looks for an ``attribute_encoder`` on the session. If the renderer finds one, it will pass it to
``json.dumps`` as either that function's ``cls`` or ``default`` keyword parameters depending on whether
a ``json.JSONEncoder`` or a function is used, respectively.

Here's an example that uses a function::

    def _json_date_handler(obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()

    session.attributes['date'] = date
    session.attributes_encoder = _json_date_handler

See the `json.dump documentation <https://docs.python.org/2/library/json.html#json.dump>`_ for for details about
that method's ``cls`` and ``default`` parameters.


Automatic Handling of Plaintext and SSML
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
        <speak>
            I am a multi-line SSML template. My content spans more than one line,
            so there's a pipe and a newline that separates my name and value.
            Enjoy the sounds of the ocean.
            <audio src='https://s3.amazonaws.com/ask-storage/tidePooler/OceanWaves.mp3'/>
        </speak>

You can also use a custom templates file passed into the Ask object::

  ask = Ask(app, '/', None, 'custom-templates.yml')
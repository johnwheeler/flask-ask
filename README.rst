Flask-Ask: Rapid Alexa Skills Kit Development for Python
========================================================

.. image:: https://img.shields.io/pypi/v/flask-ask.svg
    :target: https://pypi.python.org/pypi/flask-ask

Flask-Ask is a Flask extension that makes it easy to write Alexa Skills hosted on a server. Flask-Ask is
a simple, convention-over-configuration based API. Use it with `Ngrok <https://ngrok.com>`_ to eliminate the
deploy-to-test step and get work done faster!

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

There are more code and template examples in the samples directory.

5-Minute Tutorial
-----------------

See how fast and easy it is to develop Alexa Skills with Flask-Ask and Ngrok

.. image:: http://i.imgur.com/Tajkmdi.png
   :target: https://www.youtube.com/watch?v=eC2zi4WIFX0

Features
--------

Flask-Ask:

* Verifies Alexa request signatures
* Provides decorators that map ASK requests to view functions
* Helps construct ask and tell responses, reprompts and cards
* Allows for the separation of code and speech through Jinja templates

Installation
------------
To install Flask-Ask::

  pip install flask-ask

Documentation
-------------
http://flask-ask.readthedocs.org

Todo
----
* docstrings
* tests

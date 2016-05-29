Getting Started
===============

Installation
------------
To install Flask-Ask::

  pip install flask-ask


A Minimal Voice User Interface
------------------------------
A Flask-Ask application looks like this:

.. code-block:: python

  from flask import Flask, render_template
  from flask_ask import Ask, statement

  app = Flask(__name__)
  ask = Ask(app, '/')

  @ask.intent('HelloIntent')
  def hello(firstname):
      text = render_template('hello', firstname=firstname)
      return statement(text).simple_card('Hello', text)

  if __name__ == '__main__':
      app.run(debug=True)

In the code above:

#. The ``Ask`` object is created by passing in the Flask application and a route to forward Alexa requests to.
#. The ``intent`` decorator maps ``HelloIntent`` to a view function ``hello``.
#. The intent's ``firstname`` slot is implicitly mapped to ``hello``'s ``firstname`` parameter.
#. Jinja templates are supported. Internally, templates are loaded from a YAML file (discussed further below).
#. Lastly, a builder constructs a spoken response and displays a contextual card in the Alexa smartphone/tablet app.

Since Alexa responses are usually short phrases, it's convenient to put them in the same file.
Flask-Ask has a `Jinja template loader <http://jinja.pocoo.org/docs/dev/api/#loaders>`_ that loads
multiple templates from a single YAML file. For example, here's a template that supports the minimal voice interface
above.Templates are stored in a file called `templates.yaml` located in the application root:

.. code-block:: yaml

    hello: Hello, {{ firstname }}

For more information about how the Alexa Skills Kit works, see `Understanding Custom Skills <https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/overviews/understanding-custom-skills>`_ in the Alexa Skills Kit documentation.

Additionally, more code and template examples are in the `samples <https://github.com/johnwheeler/flask-ask/tree/master/samples>`_ directory.

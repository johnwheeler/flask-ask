.. image:: http://flask-ask.readthedocs.io/en/latest/_images/logo-full.png

**Alexa Skills Kit Development for Python**

Building high-quality Alexa skills for Amazon Echo Devices takes time. Flask-Ask makes it easier and much more fun.
Use Flask-Ask with `ngrok <https://ngrok.com>`_ to eliminate the deploy-to-test step and get work done faster.

☤ The Basics
-------------
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

☤ Features
-----------
Flask-Ask handles the boilerplate, so you can focus on writing clean code. Flask-Ask:

* Has decorators to map Alexa requests and intent slots to view functions
* Helps construct ask and tell responses, reprompts and cards
* Makes session management easy
* Allows for the separation of code and speech through Jinja templates
* Verifies Alexa request signatures

☤ Installation
---------------
To install Flask-Ask::

  pip install flask-ask

☤ Documentation
----------------
These resources will get you up and running quickly:

`Full online documentation <https://johnwheeler.org/flask-ask>`_

.. image:: http://i.imgur.com/Tajkmdi.png
  :target: https://www.youtube.com/watch?v=eC2zi4WIFX0
  :alt: 5-minute Flask-Ask and ngrok tutorial.

☤ Todo
-------
* docstrings
* tests

☤ Thank You
------------
Thanks for checking this library out! I hope you find it useful.

Of course, there's always room for improvement.
Feel free to `open an issue <https://github.com/johnwheeler/flask-ask/issues>`_ so we can make Flask-Ask better.

Special thanks to `@kennethreitz <https://github.com/kennethreitz>`_ for his `sense <http://docs.python-requests.org/en/master/>`_ of `style <https://github.com/kennethreitz/records/blob/master/README.rst>`_, and of course, `@mitsuhiko <https://github.com/mitsuhiko>`_ for `Flask <https://www.palletsprojects.com/p/flask/>`_

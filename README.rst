
.. image:: http://flask-ask.readthedocs.io/en/latest/_images/logo-full.png

|Bird|_ `Follow @_johnwheeler for updates <https://twitter.com/_johnwheeler>`_

.. |Bird| image:: http://i.imgur.com/UUARvmc.png
.. _Bird: https://twitter.com/_johnwheeler

===================================
Program the Amazon Echo with Python
===================================

Flask-Ask is a `Flask extension <http://flask.pocoo.org/extensions/>`_ that makes building Alexa skills for the Amazon Echo easier and much more fun.

* `Flask-Ask quickstart on Amazon's Developer Blog <https://developer.amazon.com/public/community/post/Tx14R0IYYGH3SKT/Flask-Ask-A-New-Python-Framework-for-Rapid-Alexa-Skills-Kit-Development>`_.
* `Level Up with our Alexa Skills Kit Video Tutorial <https://alexatutorial.com/>`_
* `Chat on Gitter.im <https://gitter.im/johnwheeler/flask-ask/>`_

The Basics
===============

A Flask-Ask application looks like this:

.. code-block:: python

  from flask import Flask
  from flask_ask import Ask, statement

  app = Flask(__name__)
  ask = Ask(app, '/')

  @ask.intent('HelloIntent')
  def hello(firstname):
      speech_text = "Hello %s" % firstname
      return statement(speech_text).simple_card('Hello', speech_text)

  if __name__ == '__main__':
      app.run()

In the code above:

#. The ``Ask`` object is created by passing in the Flask application and a route to forward Alexa requests to.
#. The ``intent`` decorator maps ``HelloIntent`` to a view function ``hello``.
#. The intent's ``firstname`` slot is implicitly mapped to ``hello``'s ``firstname`` parameter.
#. Lastly, a builder constructs a spoken response and displays a contextual card in the Alexa smartphone/tablet app.

More code examples are in the `samples <https://github.com/johnwheeler/flask-ask/tree/master/samples>`_ directory.

Jinja Templates
---------------

Since Alexa responses are usually short phrases, you might find it convenient to put them in the same file.
Flask-Ask has a `Jinja template loader <http://jinja.pocoo.org/docs/dev/api/#loaders>`_ that loads
multiple templates from a single YAML file. For example, here's a template that supports the minimal voice interface
above:

.. code-block:: yaml

    hello: Hello, {{ firstname }}

Templates are stored in a file called `templates.yaml` located in the application root. Checkout the `Tidepooler example <https://github.com/johnwheeler/flask-ask/tree/master/samples/tidepooler>`_ to see why it makes sense to extract speech out of the code and into templates as the number of spoken phrases grow.

Features
===============

Flask-Ask handles the boilerplate, so you can focus on writing clean code. Flask-Ask:

* Has decorators to map Alexa requests and intent slots to view functions
* Helps construct ask and tell responses, reprompts and cards
* Makes session management easy
* Allows for the separation of code and speech through Jinja templates
* Verifies Alexa request signatures

Installation
===============

To install Flask-Ask::

  pip install flask-ask

Documentation
===============

These resources will get you up and running quickly:

* `5-minute quickstart <https://www.youtube.com/watch?v=cXL8FDUag-s>`_
* `Full online documentation <https://alexatutorial.com/flask-ask/>`_

Fantastic 3-part tutorial series by Harrison Kinsley

* `Intro and Skill Logic - Alexa Skills w/ Python and Flask-Ask Part 1 <https://pythonprogramming.net/intro-alexa-skill-flask-ask-python-tutorial/>`_
* `Headlines Function - Alexa Skills w/ Python and Flask-Ask Part 2 <https://pythonprogramming.net/headlines-function-alexa-skill-flask-ask-python-tutorial/>`_
* `Testing our Skill - Alexa Skills w/ Python and Flask-Ask Part 3 <https://pythonprogramming.net/testing-deploying-alexa-skill-flask-ask-python-tutorial/>`_

Deployment
===============

You can deploy using any WSGI compliant framework (uWSGI, Gunicorn). If you haven't deployed a Flask app to production, `checkout flask-live-starter <https://github.com/johnwheeler/flask-live-starter>`_.

To deploy on AWS Lambda, use `Zappa <https://github.com/Miserlou/Zappa>`_. This `blog post <https://developer.amazon.com/blogs/post/8e8ad73a-99e9-4c0f-a7b3-60f92287b0bf/new-alexa-tutorial-deploy-flask-ask-skills-to-aws-lambda-with-zappa>`_ shows how to deploy Flask-Ask with Zappa from scratch.

Note: When deploying to AWS Lambda with Zappa, make sure you point the Alexa skill to the HTTPS API gateway that Zappa creates, not the Lambda function's ARN.


Related projects
===============

`cookiecutter-flask-ask <https://github.com/chrisvoncsefalvay/cookiecutter-flask-ask>`_ is a Cookiecutter to easily bootstrap a Flask-Ask project, including documentation, speech assets and basic built-in intents.

Have a Google Home? Checkout `Flask-Assistant <https://github.com/treethought/flask-assistant>`_ (early alpha)


Thank You
===============

Thanks for checking this library out! I hope you find it useful.

Of course, there's always room for improvement.
Feel free to `open an issue <https://github.com/johnwheeler/flask-ask/issues>`_ so we can make Flask-Ask better.

Special thanks to `@kennethreitz <https://github.com/kennethreitz>`_ for his `sense <http://docs.python-requests.org/en/master/>`_ of `style <https://github.com/kennethreitz/records/blob/master/README.rst>`_, and of course, `@mitsuhiko <https://github.com/mitsuhiko>`_ for `Flask <https://www.palletsprojects.com/p/flask/>`_

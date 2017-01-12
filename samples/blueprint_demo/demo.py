import logging

from flask import Flask
from helloworld import blueprint

app = Flask(__name__)
app.register_blueprint(blueprint)

logging.getLogger('flask_app').setLevel(logging.DEBUG)


if __name__ == '__main__':
    app.run(debug=True)

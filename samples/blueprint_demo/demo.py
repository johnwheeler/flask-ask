import logging
import os

from flask import Flask
from helloworld import blueprint

app = Flask(__name__)
app.register_blueprint(blueprint)

logging.getLogger('flask_app').setLevel(logging.DEBUG)


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    app.run(debug=True)

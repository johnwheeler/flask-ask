import logging
import json

logger = logging.getLogger('flask_ask')
logger.addHandler(logging.StreamHandler())
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARN)


def log_json(obj, indent=2, default=None, cls=None):
    msg = json.dumps(obj, indent=indent, default=default, cls=cls)
    logger.debug(msg)


from models import statement, question
from .core import (
    Ask,
    request,
    session,
    version,
    state,
    context,
    current_stream,
    convert_errors
)

from .models import question, statement, audio

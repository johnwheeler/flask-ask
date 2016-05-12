import logging

logger = logging.getLogger('flask_ask')
logger.addHandler(logging.StreamHandler())
if logger.level == logging.NOTSET:
    logger.setLevel(logging.WARN)

from .core import Ask, question, statement, request, session

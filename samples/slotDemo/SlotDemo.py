import logging
import os

from flask import Flask
from flask_ask import Ask, request, session, question, statement


app = Flask(__name__)
app.debug = True

ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    speech_text = 'Welcome to the Flask Ask Slot demonstration.' + \
                  'You can ask me to add things to slots; for example ' + \
                  'add battle cat and megatron and top cat'
    return question(speech_text).reprompt(speech_text).simple_card('Flask Ask Slot Demo', speech_text)


def parse_slot(slot):
    if (slot is None):
        return "slot wasn't specified. "

    speech_text = 'slot has value ' + slot.value
    if str(slot.code) == 'ER_SUCCESS_MATCH':
        speech_text += ' and matched with id ' + str(slot.id)
        speech_text += ' and name ' + str(slot.name)
    else:
        speech_text += ' but had no match'
    speech_text += '. '
    return speech_text

@ask.intent('FlaskAskSlotTest', types={'first':'slot','second':'slot'})
def slot_test(first, second, third):
    speech_text  = 'First ' + parse_slot(first)
    speech_text += 'Second ' + parse_slot(second)
    speech_text += 'Third value is ' + str(third)
    return statement(speech_text).simple_card('Flask Ask Slot Demo', speech_text)


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    app.run(debug=True, port=4010)

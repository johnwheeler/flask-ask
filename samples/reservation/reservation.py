import logging
import datetime

from flask import Flask

import sys
sys.path.append('lib/flask_ask')

from flask_ask import Ask, statement, question, session, state


app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@ask.launch
def welcome():
    state.transition('capture_where_departing')
    return question("Welcome to the flight booking service. What city are you leaving from?")


@ask.intent("AMAZON.StopIntent")
def stop():
    return statement("The flight booking service has been stopped.")


# state - capture_where_departing

@ask.intent("CityIntent", state='capture_where_departing')
def where_departing(city):
    session.attributes['where_departing'] = city

    state.transition('capture_where_arriving')
    return question("Where are you going?")


# state - capture_where_arriving

@ask.intent("CityIntent", state='capture_where_arriving')
def where_arriving(city):
    session.attributes['where_arriving'] = city

    state.transition('capture_when_departing')
    return question("What date do you want to leave?")


# state - capture_when_departing

@ask.intent("DateIntent", state='capture_when_departing', convert={'date': 'date'})
def when_departing(date):
    session.attributes['when_departing'] = date
    session.attributes_encoder = _json_date_handler

    state.transition('capture_one_way_option')
    return question("Is it a one-way trip?")


# state - capture_one_way_option

@ask.intent("AMAZON.YesIntent", state='capture_one_way_option')
def one_way_yes():
    state.transition('confirmation')
    return _confirmation_question()


@ask.intent("AMAZON.NoIntent", state='capture_one_way_option')
def one_way_no():
    state.transition('capture_when_returning')
    return question("What date do you want to return?")


# state - capture_when_returning

@ask.intent("DateIntent", state='capture_when_returning', convert={'date': 'date'})
def when_returning(date):
    session.attributes['when_returning'] = date
    session.attributes_encoder = _json_date_handler

    state.transition('confirmation')
    return _confirmation_question()


# state - confirmation

@ask.intent("AMAZON.YesIntent", state='confirmation')
def confirm_yes():
    return statement("Your flight has been booked. Thank you.")


@ask.intent("AMAZON.NoIntent", state='confirmation')
def confirm_no():
    state.transition('capture_where_departing')
    return question("What city are you leaving from?")


def _json_date_handler(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()


def _confirmation_question():
    where_departing = session.attributes.get('where_departing')
    when_departing = session.attributes.get('when_departing')
    where_arriving = session.attributes.get('where_arriving')
    when_returning = session.attributes.get('when_returning')

    speech_text = "I have you leaving from {} and going to {} on {}. " \
        .format(where_departing, where_arriving, when_departing)
    if when_returning is not None:
        speech_text += "You are set to return on {}. ".format(when_returning)
    else:
        speech_text += "This is a one-way trip. "

    speech_text += "Do you want to confirm?"

    return question(speech_text)


if __name__ == '__main__':
    app.run(debug=True)

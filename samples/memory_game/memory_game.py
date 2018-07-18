import logging
from random import randint
from flask import Flask, render_template

import sys
sys.path.append("lib/flask_ask")

from flask_ask import Ask, statement, question, session, state

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger("flask_ask").setLevel(logging.DEBUG)

class AppStates:
    NEW = 0  # New session
    GAME_IN_PROGRESS = 1  # In middle of game
    GAME_OVER = 2  # No Game running 

@ask.launch
def new_game():
    session.attributes['state'] = AppStates.NEW
    state.transition(AppStates.NEW)
    session.attributes['numbers'] = []

    welcome_msg = render_template('welcome')
    return question(welcome_msg)

@ask.intent("AMAZON.YesIntent")
def next_round():
    session.attributes['state'] = AppStates.GAME_IN_PROGRESS
    numbers = [randint(0, 9) for _ in range(3)]
    round_msg = render_template('round', numbers=numbers)
    session.attributes['numbers'] = numbers[::-1]  # reverse
    return question(round_msg)

@ask.intent("AMAZON.NoIntent")
def nope():
    if session.attributes['state'] == AppStates.GAME_IN_PROGRESS:
        numbers = session.attributes['numbers']
        nope_msg = render_template('round', numbers=numbers[::-1])
    else:
        nope_msg = render_template('help')
    return question(nope_msg)

@ask.intent("AnswerIntent", convert={'first': int, 'second': int, 'third': int})
def answer(first, second, third):
    if session.attributes['state'] == AppStates.GAME_IN_PROGRESS:
        winning_numbers = session.attributes['numbers']
        if [first, second, third] == winning_numbers:
            msg = render_template('win')
        else:
            msg = render_template('lose')
    else:
        msg = render_template('help')

    session.attributes = reset(session.attributes)

    return question(msg)

def reset(attributes):
    attributes['state'] = AppStates.GAME_OVER
    attributes['numbers'] = []
    return attributes

@ask.intent("AMAZON.HelpIntent", state=AppStates.GAME_IN_PROGRESS)
def restate():
    numbers = session.attributes['numbers']
    help_msg = render_template('round', numbers=numbers[::-1])
    
    return question(help_msg)

@ask.intent("AMAZON.HelpIntent", state=AppStates.NEW)
def help():
    help_msg = render_template('help')
    return question(help_msg)
    

@ask.intent("AMAZON.StopIntent")
def stop():
    stop_msg = render_template('stop')
    return statement(stop_msg)

if __name__ == '__main__':
    app.run(debug=True)


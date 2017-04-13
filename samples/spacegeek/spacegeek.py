import logging
from random import randint

from flask import Flask, render_template
from flask_ask import Ask, request, session, question, statement


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    return get_new_fact()


@ask.intent('GetNewFactIntent')
def get_new_fact():
    num_facts = 13  # increment this when adding a new fact template
    fact_index = randint(0, num_facts-1)
    fact_text = render_template('space_fact_{}'.format(fact_index))
    card_title = render_template('card_title')
    return statement(fact_text).simple_card(card_title, fact_text)


@ask.intent('AMAZON.HelpIntent')
def help():
    help_text = render_template('help')
    return question(help_text).reprompt(help_text)


@ask.intent('AMAZON.StopIntent')
def stop():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.intent('AMAZON.CancelIntent')
def cancel():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    app.run(debug=True)

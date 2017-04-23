import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


COLOR_KEY = "COLOR"


@ask.launch
def launch():
    card_title = render_template('card_title')
    question_text = render_template('welcome')
    reprompt_text = render_template('welcome_reprompt')
    return question(question_text).reprompt(reprompt_text).simple_card(card_title, question_text)


@ask.intent('MyColorIsIntent', mapping={'color': 'Color'})
def my_color_is(color):
    card_title = render_template('card_title')
    if color is not None:
        session.attributes[COLOR_KEY] = color
        question_text = render_template('known_color', color=color)
        reprompt_text = render_template('known_color_reprompt')
    else:
        question_text = render_template('unknown_color')
        reprompt_text = render_template('unknown_color_reprompt')
    return question(question_text).reprompt(reprompt_text).simple_card(card_title, question_text)


@ask.intent('WhatsMyColorIntent')
def whats_my_color():
    card_title = render_template('card_title')
    color = session.attributes.get(COLOR_KEY)
    if color is not None:
        statement_text = render_template('known_color_bye', color=color)
        return statement(statement_text).simple_card(card_title, statement_text)
    else:
        question_text = render_template('unknown_color_reprompt')
        return question(question_text).reprompt(question_text).simple_card(card_title, question_text)


@ask.session_ended
def session_ended():
    return "{}", 200


if __name__ == '__main__':
    app.run(debug=True)

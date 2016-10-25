import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio

app = Flask(__name__)
ask = Ask(app, "/")
logger = logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    return statement('Welcome to soundcloud, what shall we listen to?')

@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused, yo.').stop()

@ask.intent('AMAZON.ResumeIntent')
def resume():
    return statement('Its resumed yo')


@ask.intent('DemoIntent')
def demo():
    return audio('weeeeeee').play('https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg')


@ask.session_ended
def session_ended():
    return "", 200


if __name__ == '__main__':
    app.run(debug=True)

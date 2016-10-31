import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    card_title = 'Audio Example'
    text = 'Welcome to an audio example. Ready to hear the stream?'
    return statement(text).simple_card(card_title, text)


@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused the stream, yo.').stop()

@ask.intent('AMAZON.StopIntent')
def stop():
    return audio('bye bye').clear_queue(stop=True)


@ask.on_playback_stopped(mapping={'pos': 'offsetInMilliseconds'})
def stopped(pos, token):
    log.info('Audio Stream was stopped at {} ms'.format(pos))
    log.info('The stopped AudioStream owns the token {}'.format(token))


@ask.intent('AMAZON.ResumeIntent')
def resume():
    return audio('Its resumed yo').resume()


@ask.intent('DemoIntent')
def demo():
    return audio('weee').play('https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg')


@ask.on_playback_started(mapping={'stream_number': 'token'})
def on_start(offset, stream_number):
    log.info('Audio Stream was started at {} ms'.format(offset))
    log.info('The stopped AudioStream owns the token {}'.format(stream_number))


@ask.session_ended
def session_ended():
    return "", 200


if __name__ == '__main__':
    app.run(debug=True)

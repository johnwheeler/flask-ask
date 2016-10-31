import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def launch():
    card_title = 'Audio Example'
    text = 'Welcome to an audio example. You can ask to begin demo, or try asking me to play the sax.'
    prompt = 'You can ask to begin demo, or try asking me to play the sax.'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('DemoIntent')
def demo(offset):
    speech = "Here's one of my favorites"
    stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
    return audio(speech).play(stream_url, offset=93000)


# 'ask audio_skil Play the sax
@ask.intent('SaxIntent')
def george_michael():
    speech = 'yeah you got it!'
    stream_url = 'https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg'
    return audio(speech).play(stream_url)


@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused the stream.').stop()


@ask.intent('AMAZON.ResumeIntent')
def resume():
    return audio('Resuming.').resume()


# optional callbacks
@ask.on_playback_stopped(mapping={'pos': 'offsetInMilliseconds'})
def stopped(pos, url, token):
    print('Playback stopped from {}'.format(url))
    print('Audio Stream was stopped at {} ms'.format(pos))
    print('The stopped AudioStream owns the token {}'.format(token))


@ask.on_playback_started(
    mapping={'offset': 'offsetInMilliseconds', 'stream_location': 'url', 'stream_number': 'token'})
def on_start(offset, stream_location, stream_number):
    print('Playback started from {}'.format(stream_location))
    print('Audio stream was started with an offset of {} ms'.format(offset))
    print('The stopped stream owns the token {}'.format(stream_number))


@ask.session_ended
def session_ended():
    return "", 200


if __name__ == '__main__':
    app.run(debug=True)

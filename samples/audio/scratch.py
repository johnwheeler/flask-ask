import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream
import collections

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


queue = collections.deque([
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Ringing.mp3',
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Risset%20Drum%201.mp3',
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Submarine.mp3',
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/negativeapplause.mp3',
        'https://ia801304.us.archive.org/22/items/mailboxbadgerdrumsamplesvolume2/Cat%20Call.mp3',
        'https://ia801304.us.archive.org/22/items/mailboxbadgerdrumsamplesvolume2/silly%20rimshot.mp3'
        'https://www.freesound.org/data/previews/367/367420_4701691-lq.mp3',
        'https://www.freesound.org/data/previews/367/367142_2188-lq.mp3',
        'https://www.freesound.org/data/previews/367/367201_4316284-lq.mp3'
    ])

    

@ask.launch
def launch():
    card_title = 'Audio Example'
    text = 'Welcome to an audio example. You can ask to begin demo, or try asking me to play the sax.'
    prompt = 'You can ask to begin demo, or try asking me to play the sax.'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('DemoIntent')
def demo():
    return audio().play('https://www.freesound.org/data/previews/367/367420_4701691-lq.mp3')

# 'ask audio_skil Play the sax


@ask.intent('SaxIntent')
def george_michael():
    speech = 'yeah you got it!'
    # stream_url = 'https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg'
    # stream_url = 'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Ringing.mp3'
    stream_url = 'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Risset%20Drum%201.mp3'
    return audio(speech).play(stream_url)

# @ask.on_playback_nearly_finished()
#     def play_next_stream():
          stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#         audio().enqueue(stream_url, offset=93000)

@ask.on_playback_nearly_finished()
def show_request_feedback(offset, token):
    print('Nearly Finished')
    print('Stream at {} ms when Playback Request sent'.format(offset))
    print('Stream holds the token {}'.format(token))
    stream = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
    return audio().enqueue('https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3', offset=93000)


# # test nearly finished with params, no directive
# @ask.on_playback_nearly_finished()
# def log_info(offset, token):
#     print('Playback Nearly finished')
#     print('Offset at {} ms'.format(offset))
#     print('Stream has token {}'.format(token))
#     stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#     return audio().enqueue(stream_url, offset=93000)



# # test nearly finished directive, but no params #works
# @ask.on_playback_nearly_finished()
# def send_dir():
#     logging.info('Nearly Finished')
#     stream_url = queue.popleft()
#     # stream_url = 'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/negativeapplause.mp3'
#     # stream_url = 'https://www.freesound.org/data/previews/367/367420_4701691-lq.mp3'
#     stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#     return audio().enqueue(stream_url, offset=93000)
    

# # The example in the code is never called #works
# @ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds'})
# def play_next_stream(offset):
#     print("Nearly Fininshed")
#     print('current offset is {}'.format(offset))
#     stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#     return audio().enqueue(stream_url, offset=93000)


# # Error no speech
# @ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds', 'stream_number':'token'})
# def play_next_stream():
#      print("Nearly Fininshed")
#      stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#      audio().enqueue(stream_url)


# # Error AttributeError: type object 'audio' has no attribute 'prev_stream'
# @ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds', 'stream_number':'token'})
# def play_next_stream(offset, stream_number):
#     print("Nearly Fininshed")
#     print(offset)
#     print(stream_number)
#     stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#     audio().enqueue(stream_url)


# Error no speech
#@ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds', 'stream_location': 'url', 'stream_number':'token'})
# def play_next_stream():
#  print("Nearly Fininshed")
#  stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#  audio().play_next(stream_url)


# This plays and finishes but the next song doesn't start
#@ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds', 'stream_location': 'url', 'stream_number':'token'})
# def play_next_stream():
#  print("Nearly Fininshed")
#  stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#  audio("Next").play_next(stream_url)


# Try with return but get error AttributeError: '_Session' object has no attribute 'attributes'
# @ask.on_playback_nearly_finished(mapping={'offset': 'offsetInMilliseconds', 'stream_number': 'token'})
# def play_next_stream():
#     print("Nearly Fininshed")
#     stream_url = 'https://www.vintagecomputermusic.com/mp3/s2t9_Computer_Speech_Demonstration.mp3'
#     return audio("Next").play_next(stream_url)


@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused the stream.').stop()


@ask.intent('AMAZON.ResumeIntent')
def resume():
    return audio('Resuming.').resume()


# optional callbacks
# @ask.on_playback_stopped(mapping={'pos': 'offsetInMilliseconds'})
# def stopped(pos, token):
#     print('Audio Stream was stopped at {} ms'.format(pos))
#     print('The stopped AudioStream owns the token {}'.format(token))


# @ask.on_playback_started(
#     mapping={'offset': 'offsetInMilliseconds', 'stream_number': 'token'})
# def on_start(offset, stream_number):
#     print('Audio stream was started with an offset of {} ms'.format(offset))
#     print('The stopped stream owns the token {}'.format(stream_number))


@ask.session_ended
def session_ended():
    return "", 200




if __name__ == '__main__':
    app.run(debug=True)

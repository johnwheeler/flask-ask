import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream
import collections

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


queue = collections.deque([
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Ringing.mp3',
        'https://www.freesound.org/data/previews/367/367142_2188-lq.mp3',
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Risset%20Drum%201.mp3',
        'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Submarine.mp3',
        'https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg'

    ])

@ask.launch
def launch():
    card_title = 'Playlist Example'
    text = 'Welcome to an example of playing a playlist. You can ask to start the playlist'
    prompt = 'Try asking me to start the playlist'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('PlaylistDemoIntent')
def begin_playlist():
    speech = 'Heres a playlist of some short sounds. You can say Alexa Next to skip a song'
    stream_url = queue.popleft()
    return audio(speech).play(stream_url)


@ask.on_playback_nearly_finished()
def show_request_feedback(offset, token):
    print('Nearly Finished')
    print('Stream at {} ms when Playback Request sent'.format(offset))
    print('Stream holds the token {}'.format(token))
    # print('Stream playing from url {}'.format(current_stream.url))
    next_stream = queue.popleft()
    return audio().enqueue(next_stream)

@ask.intent('AMAZON.NextIntent')
def next_song():
    speech = 'playing next queued song'
    next_song = queue.popleft()
    return audio(speech).play(next_song)



@ask.intent('AMAZON.PauseIntent')
def pause():
    return audio('Paused the stream.').stop()


@ask.intent('AMAZON.ResumeIntent')
def resume():
    return audio('Resuming.').resume()


@ask.session_ended
def session_ended():
    return "", 200


if __name__ == '__main__':
    app.run(debug=True)

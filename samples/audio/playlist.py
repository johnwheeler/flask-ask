import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream, logger

import collections

app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.INFO)


queue = collections.deque([
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Ringing.mp3',
    'https://archive.org/download/petescott20160927/20160927%20RC300-53-127.0bpm.mp3',
    'https://archive.org/download/plpl011/plpl011_05-johnny_ripper-rain.mp3',
    'https://archive.org/download/piano_by_maxmsp/beats107.mp3',
    'https://archive.org/download/petescott20160927/20160927%20RC300-58-115.1bpm.mp3',
    'https://archive.org/download/PianoScale/PianoScale.mp3',
    # 'https://www.freesound.org/data/previews/367/367142_2188-lq.mp3',
    'https://archive.org/download/FemaleVoiceSample/Female_VoiceTalent_demo.mp4',
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Risset%20Drum%201.mp3',
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Submarine.mp3',
    # 'https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg'

])


@ask.launch
def launch():
    card_title = 'Audio Example'
    text = 'Welcome to an example for playing a playlist. You can ask me to start the playlist.'
    prompt = 'You can ask start playlist.'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('PlaylistDemoIntent')
def begin_playlist():
    speech = 'Heres a playlist of some short sounds. You can say Alexa Next to skip a song'
    stream_url = queue.popleft()
    return audio(speech).play(stream_url)


@ask.on_playback_nearly_finished()
def show_request_feedback(offset, token):
    logger.info('Nearly Finished')
    logger.info('Stream at {} ms when Playback Request sent'.format(offset))
    logger.info('Stream holds the token {}'.format(token))
    logger.info('Stream playing from url {}'.format(current_stream.url))
    try:
        next_stream = queue.popleft()
        return audio().enqueue(next_stream)
    except IndexError:
        logger.info('No more songs to enqueue')


@ask.on_playback_started()
def started(offset, token):
    logger.info('STARTED Audio Stream at {} ms'.format(offset))
    logger.info('STARTED Audio Stream with token {}'.format(token))
    logger.info('STARTED Audio stream from {}'.format(current_stream.url))


@ask.on_playback_stopped()
def stopped(offset, token):
    logger.info('STOPPED Audio Stream at {} ms'.format(offset))
    logger.info('STOPPED Audio Stream with token {}'.format(token))
    logger.info('STOPPED Audio stream from {}'.format(current_stream.url))


@ask.on_playback_finished()
def finished(offset, token):
    logger.info('FINISHED Audio Stream at {} ms'.format(offset))
    logger.info('FINISHED Audio Stream with token {}'.format(token))
    logger.info('FINISHED Audio stream from {}'.format(current_stream.url))
    if len(queue) < 1:
        end_of_queue()


@ask.intent('AMAZON.NextIntent')
def next_song():
    speech = 'playing next queued song'
    try:
        next_song = queue.popleft()
        return audio(speech).play(next_song)
    except IndexError:
        return audio('There are no more songs in the queue')


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

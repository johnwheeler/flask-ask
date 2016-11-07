import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream, logger

import collections
from pprint import pprint
from werkzeug.local import LocalProxy


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


playlist = [
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
]


class QueueManager(object):
    """Manages queue data in a seperate context from current_stream.

    The flask-ask Local current_stream refers only to the current data from Alexa requests and Skill Responses.
    Alexa Skills Kit does not provide enqueued or stream-histroy data and does not provide a session attribute
    when deliverying AudioPlayer Requests.

    This class is used to maintain accurate control of multiple streams,
    so that the user may send Intents to move throughout a queue.
    """

    def __init__(self, urls):
        self._queued = collections.deque(urls)
        self._history = []
        self._current = None

    def __repr__(self):
        return """
        Queue at track {}
        Current url: {}
        History: {}""".format(self.current_position, self.current, self.history)

    @property
    def up_next(self):
        """Returns the url at the front of the queue"""
        return self._queued[0]

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, url):
        self._save_to_history()
        self._current = url

    @property
    def history(self):
        return self._history

    @property
    def previous(self):
        return self._history[-1]

    def add(self, url):
        self._queued.append(url)

    def _save_to_history(self):
        if self._current:
            self._history.append(self._current)

    def end_current(self):
        self._save_to_history
        self._current = None

    def step(self):
        self.end_current()
        self._current = self._queued.popleft()
        return self._current

    def step_back(self):
        self._queued.appendleft(self._current)
        self._current = self._history.pop()
        return self._current

    @property
    def current_position(self):
        return len(self._history)


queue = QueueManager(playlist)


@ask.launch
def launch():
    card_title = 'Audio Example'
    text = 'Welcome to an example for playing a playlist. You can ask me to start the playlist.'
    prompt = 'You can ask start playlist.'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('PlaylistDemoIntent')
def begin_playlist():
    speech = 'Heres a playlist of some sounds. You can say Alexa Next to skip a song'
    stream_url = queue.step()
    print(queue)
    return audio(speech).play(stream_url)


@ask.on_playback_nearly_finished()
def show_request_feedback(token):
    logger.info('Nearly Finished with stream token'.format(token))
    logger.info('Stream playing from url {}'.format(current_stream.url))
    next_stream = queue.up_next
    print(queue)
    return audio().enqueue(next_stream)


@ask.intent('AMAZON.NextIntent')
def next_song():
    speech = 'playing next queued song'
    try:
        next_stream = queue.step()
        print(queue)
        return audio(speech).play(next_stream)
    except IndexError:
        return audio('There are no more songs in the queue')


@ask.intent('AMAZON.PreviousIntent')
def previous_song():
    try:
        speech = 'playing previously played song'
        prev_stream = queue.step_back()
        print(queue)
        return audio(speech).play(previous)
    except IndexError:
        return audio('There are no songs in your playlist history.')


@ask.on_playback_finished()
def finished():
    logger.info('FINISHED Audio stream from {}'.format(current_stream.url))
    queue.step()
    print(queue)


@ask.on_playback_started()
def started(offset, token):
    logger.info('STARTED Audio Stream at {} ms'.format(offset))
    logger.info('STARTED Audio Stream with token {}'.format(token))
    logger.info('STARTED Audio stream from {}'.format(current_stream.url))
    print(queue)


@ask.on_playback_stopped()
def stopped(offset, token):
    logger.info('STOPPED Audio Stream at {} ms'.format(offset))
    logger.info('Stream was playing from {}'.format(current_stream.url))


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

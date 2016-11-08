import logging

from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement, context, audio, current_stream, logger

import collections
from pprint import pprint
from werkzeug.local import LocalProxy


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.INFO)


playlist = [
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Ringing.mp3',
    'https://archive.org/download/petescott20160927/20160927%20RC300-53-127.0bpm.mp3',
    'https://archive.org/download/plpl011/plpl011_05-johnny_ripper-rain.mp3',
    'https://archive.org/download/piano_by_maxmsp/beats107.mp3',
    'https://archive.org/download/petescott20160927/20160927%20RC300-58-115.1bpm.mp3',
    'https://archive.org/download/PianoScale/PianoScale.mp3',
    # 'https://www.freesound.org/data/previews/367/367142_2188-lq.mp3',
    # 'https://archive.org/download/FemaleVoiceSample/Female_VoiceTalent_demo.mp4',
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Risset%20Drum%201.mp3',
    'https://archive.org/download/mailboxbadgerdrumsamplesvolume2/Submarine.mp3',
    # 'https://ia800203.us.archive.org/27/items/CarelessWhisper_435/CarelessWhisper.ogg'
]


class QueueManager(object):
    """Manages queue data in a seperate context from current_stream.

    The flask-ask Local current_stream refers only to the current data from Alexa requests and Skill Responses.
    Alexa Skills Kit does not provide enqueued or stream-histroy data and does not provide a session attribute
    when delivering AudioPlayer Requests.

    This class is used to maintain accurate control of multiple streams,
    so that the user may send Intents to move throughout a queue.
    """

    def __init__(self, urls):
        self._urls = urls
        self._queued = collections.deque(urls)
        self._history = collections.deque()
        self._current = None

    @property
    def status(self):
        status = {
        'Current Position': self.current_position,
        'Current URl': self.current,
        'Next URL': self.up_next,
        'Previous': self.previous,
        'History': list(self.history)
        }
        return status

    @property
    def up_next(self):
        """Returns the url at the front of the queue"""
        qcopy = self._queued.copy()
        try:
            return qcopy.popleft()
        except IndexError:
            return None

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
        history = self.history.copy()
        try:
            return history.pop()
        except IndexError:
            return None

    def add(self, url):
        self._urls.append(url)
        self._queued.append(url)

    def extend(self, urls):
        self._urls.extend(urls)
        self._queued.extend(urls)

    def _save_to_history(self):
        if self._current:
            self._history.append(self._current)

    def end_current(self):
        self._save_to_history()
        self._current = None

    def step(self):
        self.end_current()
        self._current = self._queued.popleft()
        return self._current

    def step_back(self):
        self._queued.appendleft(self._current)
        self._current = self._history.pop()
        return self._current

    def reset(self):
        self._queued = collections.deque(self._urls)
        self._history = []

    def start(self):
        self.__init__(self._urls)
        return self.step()

    @property
    def current_position(self):
        return len(self._history)


queue = QueueManager(playlist)


@ask.launch
def launch():
    card_title = 'Playlist Example'
    text = 'Welcome to an example for playing a playlist. You can ask me to start the playlist.'
    prompt = 'You can ask start playlist.'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('PlaylistDemoIntent')
def start_playlist():
    speech = 'Heres a playlist of some sounds. You can ask me Next, Previous, or Start Over'
    stream_url = queue.start()
    return audio(speech).play(stream_url)


# QueueManager object is not stepped forward here.
# This allows for Next Intents and on_playback_finished requests to trigger the step
@ask.on_playback_nearly_finished()
def nearly_finished():
    if queue.up_next:
        _infodump('Alexa is now ready for a Next or Previous Intent')
        next_stream = queue.up_next
        return audio().enqueue(next_stream)
    else:
        _infodump('Nearly finished with last song in playlist')


@ask.on_playback_finished()
def play_back_finished():
    _infodump('FINISHED Audio stream from {}'.format(current_stream.url))
    if queue.up_next:
        queue.step()
    else:
        return statement('You have reached the end of the playlist!')


# NextIntent steps queue forward and clears enqueued streams that were already sent to Alexa
# next_stream will match queue.up_next and enqueue Alexa with the correct subsequent stream.
@ask.intent('AMAZON.NextIntent')
def next_song():
    if queue.up_next:
        speech = 'playing next queued song'
        next_stream = queue.step()
        return audio(speech).play(next_stream)
    else:
        return audio('There are no more songs in the queue')


@ask.intent('AMAZON.PreviousIntent')
def previous_song():
    if queue.previous:
        speech = 'playing previously played song'
        prev_stream = queue.step_back()
        return audio(speech).play(prev_stream)

    else:
        return audio('There are no songs in your playlist history.')


@ask.intent('AMAZON.StartOverIntent')
def restart_track():
    if queue.current:
        speech = 'Restarting current track'
        return audio(speech).play(queue.current, offset=0)
    else:
        return statement('There is no current song')


@ask.on_playback_started()
def started(offset):
    _infodump('STARTED Audio Stream at {} ms'.format(offset))
    _infodump('STARTED Audio stream from {}'.format(current_stream.url))
    _infodump({'queue': queue.status})


@ask.on_playback_stopped()
def stopped(offset):
    _infodump('STOPPED Audio Stream at {} ms'.format(offset))
    _infodump('Stream stopped playing from {}'.format(current_stream.url))


@ask.intent('AMAZON.PauseIntent')
def pause():
    msg = 'Paused the Playlist on track {}'.format(queue.current_position)
    return audio('Paused the stream.').stop().simple_card(msg)


@ask.intent('AMAZON.ResumeIntent')
def resume():
    msg = 'Paused the Playlist on track {}'.format(queue.current_position)
    return audio('Resuming.').resume().simple_card(msg)


@ask.session_ended
def session_ended():
    return "", 200


def _infodump(obj, indent=2):
    msg = json.dumps(obj, indent=indent)
    logger.info(msg)


if __name__ == '__main__':
    app.run(debug=True)

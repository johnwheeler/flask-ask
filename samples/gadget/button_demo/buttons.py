import json
import logging
import os

from flask import Flask
from flask_ask import Ask, question, statement, gadget, animation, session

app = Flask(__name__)
ask = Ask(app, "/")
logger = logging.getLogger()
logging.getLogger('flask_ask').setLevel(logging.INFO)


@ask.launch
def launch():
    session.attributes['activity'] = ''
    session.attributes['players'] = []
    session.attributes['max_players'] = 4
    card_title = 'Gadget Skill Example'
    text = 'Welcome to the gadget skill example.'
    prompt = 'To register your Echo Buttons, say, "Start the roll call."'
    return question(text).reprompt(prompt).simple_card(card_title, text)


@ask.intent('RollCallIntent')
def start_roll_call():
    """Identifies all Echo Buttons that are present."""
    speech = 'Players, press your buttons now.'
    prompt = "I'm still waiting for you to press your buttons."
    session.attributes['players'] = []
    session.attributes['activity'] = 'roll call'
    return gadget(speech).reprompt(prompt).roll_call(timeout=10000, max_buttons=session.attributes['max_players'])


@ask.intent('StartRound')
def start_round():
    """Prompts all users to press their buttons and responds to the first one."""
    if not session.attributes['players']:
        return question("I don't see any players yet.  Start the roll call first.")
    session.attributes['activity'] = 'new round'
    return gadget('Press your button to buzz in.').first_button(
        timeout=8000,
        gadget_ids=[p['gid'] for p in session.attributes['players']],
        animations=[animation(repeat=4).crossfade(duration=200).off()]
    )


@ask.intent('SetButtonColor')
def set_color(button='1', color='red'):
    colors = {
        'white': 'FFFFFF',
        'red': 'FF0000',
        'orange': 'FF3300',
        'yellow': 'FFD400',
        'green': '00FF00',
        'blue': '0000FF',
        'purple': '4B0098',
        'black': '000000'
    }
    hex = colors.get(color, 'FFFFFF')
    try:
        gid = [p['gid'] for p in session.attributes['players'] if p['pid'] == button][0]
    except LookupError:
        return question("I couldn't find that button.").reprompt("What would you like to do?")
    return gadget().set_light(targets=[gid], animations=[animation().on(color=hex)])


@ask.on_input_handler_event()
def event_received(type, requestId, originatingRequestId, events):
    """Receives an Input Handler event from Alexa."""
    if len(events) == 1 and events[0].get('name', '') == 'timeout':
        if not events[0].get('inputEvents', []):
            return question('Timeout received, no events')
        else:
            if session.attributes['activity'] == 'roll call':
                session.attributes['activity'] = 'roll call complete'
                return question('I found {} buttons. Ready to start the round?'.format(len(session.attributes['players'])))
            elif session.attributes['activity'] == 'new round':
                return question('Nobody buzzed in.')
    for event in events:
        for input_event in event['inputEvents']:
            if session.attributes['activity'] == 'roll call':
                return register_player(event['name'], input_event)
            elif session.attributes['activity'] == 'new round':
                return buzz_in(input_event)


def register_player(event_name, input_event):
    """Adds a player's button to the list of known buttons and makes the button pulse yellow."""
    if input_event['action'] == 'down':
        button_number = event_name[-1]
        gid = input_event['gadgetId']
        session.attributes['players'].append({'pid': button_number, 'gid': gid})
        speech = ""
        if event_name.endswith(str(session.attributes['max_players'])):
            session.attributes['activity'] = 'roll call complete'
            speech = 'I found {} buttons. Ready to start the round?'.format(session.attributes['max_players'])
        return gadget(speech).set_light(
            targets=[gid],
            animations=[animation().pulse(color='FFFF00', duration=100)]
        )


def buzz_in(input_event):
    """Acknowledges the first button that was pressed with speech and a 'breathing' animation."""
    gid = input_event['gadgetId']
    try:
        pid = [p['pid'] for p in session.attributes['players'] if p['gid'] == gid][0]
    except LookupError:
        return question("I couldn't find the player associated with that button.")
    return gadget("Player {}, you buzzed in first.".format(pid)).set_light(
        targets=[gid],
        animations=[animation(repeat=3).breathe(duration=500, color='00FF00')]
    )


@ask.intent('AMAZON.StopIntent')
def stop():
    return statement('Goodbye')


@ask.intent('AMAZON.YesIntent')
def yes():
    if session.attributes['activity'] == 'roll call complete':
        return start_round()
    else:
        return fallback()


@ask.intent('AMAZON.NoIntent')
def no():
    return fallback()


@ask.intent('AMAZON.FallbackIntent')
def fallback():
    return question('What would you like to do?').reprompt('Are you still there?')


@ask.session_ended
def session_ended():
    return "{}", 200


def _infodump(obj, indent=2):
    msg = json.dumps(obj, indent=indent)
    logger.info(msg)


if __name__ == '__main__':
    if 'ASK_VERIFY_REQUESTS' in os.environ:
        verify = str(os.environ.get('ASK_VERIFY_REQUESTS', '')).lower()
        if verify == 'false':
            app.config['ASK_VERIFY_REQUESTS'] = False
    app.run(debug=True)

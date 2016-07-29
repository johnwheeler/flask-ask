import logging

from flask import Flask
from flask_ask import Ask, statement, question, session, state


app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


@ask.launch
def welcome():
    state.transition('user_name')
    return question("Welcome to the interview. What is your name?")


@ask.intent("NameIntent", state='user_name')
def get_user_name(name):
    session.attributes['user_name'] = name
    state.transition('friend_name')
    return question("What is your friends name?")


@ask.intent("NameIntent", state='friend_name')
def get_friend_name(name):
    session.attributes['friend_name'] = name
    user_name = session.attributes['user_name']
    return statement("Your name is {} and your friend's name is {}".format(user_name, name))


@ask.intent("AMAZON.StopIntent")
def stop():
    return statement("The program has been stopped.")


"""
{
    "intents": [
    {
        "intent": "NameIntent",
        "slots": [
        {
            "name": "name",
            "type": "AMAZON.US_FIRST_NAME"
        }]
    },
    {
        "intent": "AMAZON.StopIntent"
    }]
}
"""

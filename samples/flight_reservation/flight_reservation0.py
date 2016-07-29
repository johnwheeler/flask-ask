import logging

from flask import Flask
from flask_ask import Ask, statement, question, session, state


app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@states.initial
def welcome():
    state.transition = 'from_city'
    return question("Welcome to the flight booking service. What city are you leaving from?")


@states.from_city("CityIntent")
def from_city(city):
    state.transition = 'to_city'
    return question("Where are you going?")


@states.to_city("CityIntent")
def to_city(city):
    state.transition = 'from_date'
    return question("What date do you want to leave?")


@states.from_date("DateIntent")
def from_date(date):
    state.transition = 'one_way'
    return question("Is it a one-way trip?")


@states.one_way("AMAZON.YesIntent")
def one_way_yes():
    state.transition = 'confirm'
    return question("Do you want to confirm this trip?")


@states.one_way("AMAZON.NoIntent")
def one_way_no():
    state.transition = 'from_date'
    return question("What date do you want to return?")


@states.to_date("DateIntent")
def to_date(date):
    state.transition = 'confirm'
    return question("Do you want to confirm this trip?")


@states.confirm("AMAZON.YesIntent")
def confirm_yes():
    return statement("Your flight has been booked. Thank you.")


@states.confirm("AMAZON.NoIntent")
def confirm_no():
    state.transition = 'from_city'
    return question("What city are you leaving from?")


@states.intent("AMAZON.StopIntent")
def stop():
    return statement("The flight booking service has been stopped.")

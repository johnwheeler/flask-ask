import logging

from flask import Flask
from flask_ask import Ask, statement, question, session, state


app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@state.initial()
@ask.launch()
def welcome():
    state.transition = 'from_city'
    return question("Welcome to the flight booking service. What city are you leaving from?")


@state.from_city()
@ask.intent("CityIntent")
def from_city(city):
    state.transition = 'to_city'
    return question("Where are you going?")


@state.to_city()
@ask.intent("CityIntent")
def to_city(city):
    state.transition = 'from_date'
    return question("What date do you want to leave?")


@state.from_date()
@ask.intent("DateIntent")
def from_date(date):
    state.transition = 'one_way'
    return question("Is it a one-way trip?")


@state.one_way()
@ask.intent("AMAZON.YesIntent")
def one_way_yes():
    state.transition = 'confirm'
    return question("Do you want to confirm this trip?")


@state.one_way()
@ask.intent("AMAZON.NoIntent")
def one_way_no():
    state.transition = 'from_date'
    return question("What date do you want to return?")
    

@state.to_date()
@ask.intent("DateIntent")
def to_date(date):
    state.transition = 'confirm'
    return question("Do you want to confirm this trip?")    


@state.confirm()
@ask.intent("AMAZON.YesIntent")
def confirm_yes():
    return statement("Your flight has been booked. Thank you.")


@state.confirm()
@ask.intent("AMAZON.NoIntent")
def confirm_no():
    state.transition = 'from_city'
    return question("What city are you leaving from?")

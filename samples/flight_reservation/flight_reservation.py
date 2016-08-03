import logging

from flask import Flask
from flask_ask import Ask, statement, question, session, state


app = Flask(__name__)
ask = Ask(app, '/')
logging.getLogger("flask_ask").setLevel(logging.DEBUG)


@ask.launch
def welcome():
    state.transition('from_city')
    return question("Welcome to the flight booking service. What city are you leaving from?")


@ask.intent("CityIntent", state='from_city')
def from_city(city):
    state.transition('to_city')
    return question("Where are you going?")


@ask.intent("CityIntent", state='to_city')
def to_city(city):
    state.transition('from_date')
    return question("What date do you want to leave?")


@ask.intent("DateIntent", state='from_date')
def from_date(date):
    state.transition('one_way')
    return question("Is it a one-way trip?")


@ask.intent("AMAZON.YesIntent", state='one_way')
def one_way_yes():
    state.transition('confirm')
    return question("Do you want to confirm this trip?")


@ask.intent("AMAZON.NoIntent", state='one_way')
def one_way_no():
    state.transition('to_date')
    return question("What date do you want to return?")
    

@ask.intent("DateIntent", state='to_date')
def to_date(date):
    state.transition('confirm')
    return question("Do you want to confirm this trip?")    


@ask.intent("AMAZON.YesIntent", state='confirm')
def confirm_yes():
    return statement("Your flight has been booked. Thank you.")


@ask.intent("AMAZON.NoIntent", state='confirm')
def confirm_no():
    state.transition('from_city')
    return question("What city are you leaving from?")


@ask.intent("AMAZON.StopIntent")
def stop():
    return statement("The flight booking service has been stopped.")

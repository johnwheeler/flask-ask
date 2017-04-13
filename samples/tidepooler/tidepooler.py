import os
import logging
import datetime
import math
import re
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode

import aniso8601
from flask import Flask, json, render_template
from flask_ask import Ask, request, session, question, statement


ENDPOINT = "http://tidesandcurrents.noaa.gov/api/datagetter"
SESSION_CITY = "city"
SESSION_DATE = "date"

# NOAA station codes
STATION_CODE_SEATTLE = "9447130"
STATION_CODE_SAN_FRANCISCO = "9414290"
STATION_CODE_MONTEREY = "9413450"
STATION_CODE_LOS_ANGELES = "9410660"
STATION_CODE_SAN_DIEGO = "9410170"
STATION_CODE_BOSTON = "8443970"
STATION_CODE_NEW_YORK = "8518750"
STATION_CODE_VIRGINIA_BEACH = "8638863"
STATION_CODE_WILMINGTON = "8658163"
STATION_CODE_CHARLESTON = "8665530"
STATION_CODE_BEAUFORT = "8656483"
STATION_CODE_MYRTLE_BEACH = "8661070"
STATION_CODE_MIAMI = "8723214"
STATION_CODE_TAMPA = "8726667"
STATION_CODE_NEW_ORLEANS = "8761927"
STATION_CODE_GALVESTON = "8771341"

STATIONS = {}
STATIONS["seattle"] =  STATION_CODE_SEATTLE
STATIONS["san francisco"] =  STATION_CODE_SAN_FRANCISCO
STATIONS["monterey"] =  STATION_CODE_MONTEREY
STATIONS["los angeles"] =  STATION_CODE_LOS_ANGELES
STATIONS["san diego"] =  STATION_CODE_SAN_DIEGO
STATIONS["boston"] =  STATION_CODE_BOSTON
STATIONS["new york"] =  STATION_CODE_NEW_YORK
STATIONS["virginia beach"] =  STATION_CODE_VIRGINIA_BEACH
STATIONS["wilmington"] =  STATION_CODE_WILMINGTON
STATIONS["charleston"] =  STATION_CODE_CHARLESTON
STATIONS["beaufort"] =  STATION_CODE_BEAUFORT
STATIONS["myrtle beach"] =  STATION_CODE_MYRTLE_BEACH
STATIONS["miami"] =  STATION_CODE_MIAMI
STATIONS["tampa"] =  STATION_CODE_TAMPA
STATIONS["new orleans"] =  STATION_CODE_NEW_ORLEANS
STATIONS["galveston"] =  STATION_CODE_GALVESTON


app = Flask(__name__)
ask = Ask(app, "/")
logging.getLogger('flask_ask').setLevel(logging.DEBUG)


class TideInfo(object):

    def __init__(self):
        self.first_high_tide_time = None
        self.first_high_tide_height = None
        self.low_tide_time = None
        self.low_tide_height = None
        self.second_high_tide_time = None
        self.second_high_tide_height = None


@ask.launch
def launch():
    welcome_text = render_template('welcome')
    help_text = render_template('help')
    return question(welcome_text).reprompt(help_text)


@ask.intent('OneshotTideIntent',
    mapping={'city': 'City', 'date': 'Date'},
    convert={'date': 'date'},
    default={'city': 'seattle', 'date': datetime.date.today })
def one_shot_tide(city, date):
    if city.lower() not in STATIONS:
        return supported_cities()
    return _make_tide_request(city, date)


@ask.intent('DialogTideIntent',
    mapping={'city': 'City', 'date': 'Date'},
    convert={'date': 'date'})
def dialog_tide(city, date):
    if city is not None:
        if city.lower() not in STATIONS:
            return supported_cities()
        if SESSION_DATE not in session.attributes:
            session.attributes[SESSION_CITY] = city
            return _dialog_date(city)
        date = aniso8601.parse_date(session.attributes[SESSION_DATE])
        return _make_tide_request(city, date)
    elif date is not None:
        if SESSION_CITY not in session.attributes:
            session.attributes[SESSION_DATE] = date.isoformat()
            return _dialog_city(date)
        city = session.attributes[SESSION_CITY]
        return _make_tide_request(city, date)
    else:
        return _dialog_no_slot()


@ask.intent('SupportedCitiesIntent')
def supported_cities():
    cities = ", ".join(sorted(STATIONS.keys()))
    list_cities_text = render_template('list_cities', cities=cities)
    list_cities_reprompt_text = render_template('list_cities_reprompt')
    return question(list_cities_text).reprompt(list_cities_reprompt_text)


@ask.intent('AMAZON.HelpIntent')
def help():
    help_text = render_template('help')
    list_cities_reprompt_text = render_template('list_cities_reprompt')
    return question(help_text).reprompt(list_cities_reprompt_text)


@ask.intent('AMAZON.StopIntent')
def stop():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.intent('AMAZON.CancelIntent')
def cancel():
    bye_text = render_template('bye')
    return statement(bye_text)


@ask.session_ended
def session_ended():
    return "{}", 200


@app.template_filter()
def humanize_date(dt):
    # http://stackoverflow.com/a/20007730/1163855
    ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(n/10%10!=1)*(n%10<4)*n%10::4])
    month_and_day_of_week = dt.strftime('%A %B')
    day_of_month = ordinal(dt.day)
    year = dt.year if dt.year != datetime.datetime.now().year else ""
    formatted_date = "{} {} {}".format(month_and_day_of_week, day_of_month, year)
    formatted_date = re.sub('\s+', ' ', formatted_date)
    return formatted_date


@app.template_filter()
def humanize_time(dt):
    morning_threshold = 12
    afternoon_threshold = 17
    evening_threshold = 20
    hour_24 = dt.hour
    if hour_24 < morning_threshold:
        period_of_day = "in the morning"
    elif hour_24 < afternoon_threshold:
        period_of_day = "in the afternoon"
    elif hour_24 < evening_threshold:
        period_of_day = "in the evening"
    else:
        period_of_day = " at night"
    the_time = dt.strftime('%I:%M')
    formatted_time = "{} {}".format(the_time, period_of_day)
    return formatted_time


@app.template_filter()
def humanize_height(height):
    round_down_threshold = 0.25
    round_to_half_threshold = 0.75
    is_negative = False
    if height < 0:
        height = abs(height)
        is_negative = True
    remainder = height % 1
    if remainder < round_down_threshold:
        remainder_text = ""
        feet = int(math.floor(height))
    elif remainder < round_to_half_threshold:
        remainder_text = "and a half"
        feet = int(math.floor(height))
    else:
        remainder_text = ""
        feet = int(math.floor(height))
    if is_negative:
        feet *= -1
    formatted_height = "{} {} feet".format(feet, remainder_text)
    formatted_height = re.sub('\s+', ' ', formatted_height)
    return formatted_height


def _dialog_no_slot():
    if SESSION_CITY in session.attributes:
        date_dialog2_text = render_template('date_dialog2')
        return question(date_dialog2_text).reprompt(date_dialog2_text)
    else:
        return supported_cities()


def _dialog_date(city):
    date_dialog_text = render_template('date_dialog', city=city)
    date_dialog_reprompt_text = render_template('date_dialog_reprompt')
    return question(date_dialog_text).reprompt(date_dialog_reprompt_text)


def _dialog_city(date):
    session.attributes[SESSION_DATE] = date
    session.attributes_encoder = _json_date_handler
    city_dialog_text = render_template('city_dialog', date=date)
    city_dialog_reprompt_text = render_template('city_dialog_reprompt')
    return question(city_dialog_text).reprompt(city_dialog_reprompt_text)


def _json_date_handler(obj):
    if isinstance(obj, datetime.date):
        return obj.isoformat()


def _make_tide_request(city, date):
    station = STATIONS.get(city.lower())
    noaa_api_params = {
        'station': station,
        'product': 'predictions',
        'datum': 'MLLW',
        'units': 'english',
        'time_zone': 'lst_ldt',
        'format': 'json'
    }
    if date == datetime.date.today():
        noaa_api_params['date'] = 'today'
    else:
        noaa_api_params['begin_date'] = date.strftime('%Y%m%d')
        noaa_api_params['range'] = 24
    url = ENDPOINT + "?" + urlencode(noaa_api_params)
    resp_body = urlopen(url).read()
    if len(resp_body) == 0:
        statement_text = render_template('noaa_problem')
    else:
        noaa_response_obj = json.loads(resp_body)
        predictions = noaa_response_obj['predictions']
        tideinfo = _find_tide_info(predictions)
        statement_text = render_template('tide_info', date=date, city=city, tideinfo=tideinfo)
    return statement(statement_text).simple_card("Tide Pooler", statement_text)


def _find_tide_info(predictions):
    """
     Algorithm to find the 2 high tides for the day, the first of which is smaller and occurs
     mid-day, the second of which is larger and typically in the evening.
    """

    last_prediction = None
    first_high_tide = None
    second_high_tide = None
    low_tide = None
    first_tide_done = False
    for prediction in predictions:
        if last_prediction is None:
            last_prediction = prediction
            continue
        if last_prediction['v'] < prediction['v']:
            if not first_tide_done:
                first_high_tide = prediction
            else:
                second_high_tide = prediction
        else:  # we're decreasing
            if not first_tide_done and first_high_tide is not None:
                first_tide_done = True
            elif second_high_tide is not None:
                break  # we're decreasing after having found the 2nd tide. We're done.
            if first_tide_done:
                low_tide = prediction
        last_prediction = prediction

    fmt = '%Y-%m-%d %H:%M'
    parse = datetime.datetime.strptime
    tideinfo = TideInfo()
    tideinfo.first_high_tide_time = parse(first_high_tide['t'], fmt)
    tideinfo.first_high_tide_height = float(first_high_tide['v'])
    tideinfo.second_high_tide_time = parse(second_high_tide['t'], fmt)
    tideinfo.second_high_tide_height = float(second_high_tide['v'])
    tideinfo.low_tide_time = parse(low_tide['t'], fmt)
    tideinfo.low_tide_height = float(low_tide['v'])
    return tideinfo


if __name__ == '__main__':
    app.run(debug=True)

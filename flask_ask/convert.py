import re
from datetime import datetime, time

import aniso8601

from . import logger


_DATE_PATTERNS = {
    # "today", "tomorrow", "november twenty-fifth": 2015-11-25
    '^\d{4}-\d{2}-\d{2}$': '%Y-%m-%d',
    # "this week", "next week": 2015-W48
    '^\d{4}-W\d{2}$': '%Y-W%U-%w',
    # "this weekend": 2015-W48-WE
    '^\d{4}-W\d{2}-WE$': '%Y-W%U-WE-%w',
    # "this month": 2015-11
    '^\d{4}-\d{2}$': '%Y-%m',
    # "next year": 2016
    '^\d{4}$': '%Y',
}


def to_date(amazon_date):
    if amazon_date == "":
        return None
    # make so 'next decade' matches work against 'next year' regex
    amazon_date = re.sub('X$', '0', amazon_date)
    for re_pattern, format_pattern in _DATE_PATTERNS.items():
        if re.match(re_pattern, amazon_date):
            if '%U' in format_pattern:
                # http://stackoverflow.com/a/17087427/1163855
                amazon_date += '-0'
            return datetime.strptime(amazon_date, format_pattern).date()
    return None


def to_time(amazon_time):
    if amazon_time == "":
        return None
    if amazon_time == "AM":
        return time(hour=0)
    if amazon_time == "PM":
        return time(hour=12)
    try:
        return aniso8601.parse_time(amazon_time)
    except ValueError, e:
        logger.warn("ValueError for amazon_time '{}'.".format(amazon_time))
        logger.warn("ValueError message: {}".format(e.message))
        return None


def to_timedelta(amazon_duration):
    if amazon_duration == "":
        return None
    return aniso8601.parse_duration(amazon_duration)

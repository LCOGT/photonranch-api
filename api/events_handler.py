import random 
import datetime
import json
import time
import requests
import sys
import os
import logging

import pytz
from skyfield import api, almanac
from pytz.exceptions import UnknownTimeZoneError

from api.events import make_site_events
from api.events import get_moon_riseset_illum
from helpers import BUCKET_NAME, REGION, S3_PUT_TTL, S3_GET_TTL
from helpers import dynamodb_r, ssm_c
from helpers import DecimalEncoder, http_response, _get_body, get_secret, get_db_connection

log = logging.getLogger()
log.setLevel(logging.INFO)


def _get_site_config(site):
    """Retrieves the site config from the DynamoDB table."""

    table = dynamodb_r.Table('site_configurations')
    config = table.get_item(Key={"site": site})
    if "Item" not in config:
        raise LookupError("bad key")
    return config["Item"]["configuration"]


def get_moon_riseset_illum_handler(event, context):
    """Gets the moon rise, moon set, and moon illumination values at a site.

    The rise, set, and illumination values are calculated for a given site
    using the latitude and longitude, as well as a time period to check during.

    Args:
        event.body.lat (float): Site latitude in deg N.
        event.body.lng (float): Site longitude in deg E.
        event.body.start (str): UTC datestring of starting time to check.
        event.body.end (str): UTC datestring of ending time to check.

    Returns:
        200 status code with moon rise, set, and illum values if successful.
        404 status code if incorrect datestring formats supplied.
        404 status code if another exception occurs.
    """

    query_params = event['queryStringParameters']

    lat = float(query_params['lat'])
    lng = float(query_params['lng'])
    start = query_params['start']
    end = query_params['end']

    try: 
        moon_riseset_illum = get_moon_riseset_illum(lat, lng, start, end)
    except ValueError as e:
        print(e)
        error_msg = (
            "Error with format of start/end times. "
            "Format should be like: '2020-12-31T01:00:00Z. "
        )
        log.exception(error_msg)
        return http_response(404, error_msg)
    except Exception as e:
        error_msg = "Error while calculating moon rise set illum values."
        log.exception(error_msg)
        return http_response(404, error_msg)

    return http_response(200, moon_riseset_illum)


def siteevents(event, context):
    """Handler to provide a dictionary of site events at a given site and time.

    Site events calculated in events.py include:
        "Eve Bias Dark"
        "End Eve Bias Dark"
        "Eve Scrn Flats"
        "End Eve Scrn Flats"
        "Ops Window Start"
        "Observing Begins"
        "Observing Ends"
        "Cool Down, Open"
        "Eve Sky Flats"
        "Sun Set"
        "Civil Dusk"
        "End Eve Sky Flats"
        "Clock & Auto Focus"
        "Naut Dusk"
        "Astro Dark"
        "Middle of Night"
        "End Astro Dark
        "Final Clock & Auto Focus"
        "Naut Dawn"
        "Morn Sky Flats"
        "Civil Dawn"
        "End Morn Sky Flats"
        "Ops Window Closes"
        "Sunrise"
    
    Args:
        event.body.when (float):
            Unix timestamp within the 24hr block (local noon-noon) when we
            want to get events. Optionally provide a different time.
            Default is current time.
        event.body.site (str): Sitecode used to get site config (eg. "saf").

    Returns:
        200 status code with JSON dict of site events.
        400 status code if site missing from request body.
        500 status code if:
            - Provided sitecode does not match any existing site.
            - Invalid timezone name supplied in site config.
            - Request missing a required parameter in
            [latitude, longitude, elevation, reference_ambient,
            reference_pressure, TZ_database_name].
    """

    # Get the site included in the request
    query_params = event['queryStringParameters']
    if "site" not in query_params.keys():
        error = { "error": "Missing 'site' query string request parameter." }
        return http_response(400, error)

    # Calculate events for current day unless another time is specified.
    when = time.time() 
    if "when" in query_params.keys():
        when = float(query_params["when"])
        
    # Get the site configuration so we can access lat, lng, elevation, etc.
    try:
        site_config = _get_site_config(query_params["site"])
    except LookupError as e:
        log.exception("Bad sitecode; could not get site config")
        error = {
            "error": "The specified sitecode did not match any config file."
        }
        return http_response(500, error)


    # Get the parameters we want from the config, used to init the events class.
    try:
        latitude = float(site_config['latitude'])
        longitude = float(site_config['longitude'])
        elevation = float(site_config['elevation'])
        reference_ambient = float(site_config['reference_ambient'][0])
        reference_pressure = float(site_config['reference_pressure'][0])
        tz_name = site_config['TZ_database_name']
    except Exception as e:
        log.exception("Site config missing required parameters.")
        error = {
            "error": (
                "Site config missing required parameters. "
                "Please ensure it includes latitude, longitude, elevation, "
                "reference_ambient, reference_pressure, and TZ_database_name."
            )
        }
        return http_response(500, error)

    # Make sure the timezone is valid
    try: 
        tz = pytz.timezone(tz_name)
    except UnknownTimeZoneError as e:
        error = {
            "error": f"Invalid timezone name from site config: {str(e)}"
        }
        return http_response(500, error)

    # This method returns a dict with all the events to return.
    events_dict = make_site_events(latitude, longitude, when, tz_name)
    log.info(json.dumps(events_dict))
    return http_response(200, events_dict)


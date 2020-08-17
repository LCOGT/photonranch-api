
import random, datetime, json, time, requests, sys, os, pytz

from skyfield import api, almanac
from api import events

from pytz.exceptions import UnknownTimeZoneError

from helpers import BUCKET_NAME, REGION, S3_PUT_TTL, S3_GET_TTL
from helpers import dynamodb_r, ssm_c
from helpers import DecimalEncoder, _get_response, _get_body, _get_secret, get_db_connection

def _get_site_config(site):
    table = dynamodb_r.Table('site_configurations')
    config = table.get_item(Key={"site": site})
    if "Item" not in config:
        raise LookupError("bad key")
    #print(config["Item"])
    #print(config["Item"]["configuration"]["events"]["Sun Rise"])
    return config["Item"]["configuration"]

def siteevents(event, context):

    # Get the site included in the request
    query_params = event['queryStringParameters']
    if "site" not in query_params.keys():
        error = { "error": "Missing 'site' query string request parameter." }
        return _get_response(400, error)

    # Calculate events for current day unless another time is specified.
    when = time.time() 
    if "when" in query_params.keys():
        when = float(query_params["when"])
        
    # Get the site configuration so we can access lat, lng, elevation, etc.
    try:
        site_config = _get_site_config(query_params["site"])
    except LookupError as e:
        print("Error: bad sitecode. Couldn't get site config.")
        error = {
            "error": "The specified sitecode did not match any config file."
        }
        return _get_response(500, error)


    # Get the parameters we want from the config, used to init the events class.
    try:
        latitude = float(site_config['latitude'])
        longitude = float(site_config['longitude'])
        elevation = float(site_config['elevation'])
        reference_ambient = float(site_config['reference_ambient'][0])
        reference_pressure = float(site_config['reference_pressure'][0])
        tz_name = site_config['TZ_database_name']
    except Exception as e:
        print(str(e))
        error = {
            "error": (
                "Site config missing required parameters. "
                "Please ensure it includes latitude, longitude, elevation, "
                "reference_ambient, reference_pressure, and TZ_database_name."
            )
        }
        return _get_response(500, error)

    # Make sure the timezone is valid
    try: 
        tz = pytz.timezone(tz_name)
    except UnknownTimeZoneError as e:
        error = {
            "error": f"Invalid timezone name from site config: {str(e)}"
        }
        return _get_response(500, error)


    # This method returns a dict with all the events to return.
    events_dict = events.make_site_events(latitude,longitude,when,tz_name)
    print(json.dumps(events_dict))
    return _get_response(200, events_dict)


import random, datetime, json, time, requests, sys, os
from events import Events

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
        return _get_response(400, "Missing 'site' query string request parameter.")

    # Get the site configuration so we can access lat, lng, elevation, etc.
    try:
        site_config = _get_site_config(query_params["site"])
    except LookupError as e:
        print("Error: bad sitecode. Couldn't get site config.")

    # Get the parameters we want from the config, used to init the events class.
    try:
        latitude = float(site_config['latitude'])
        longitude = float(site_config['longitude'])
        elevation = float(site_config['elevation'])
        reference_ambient = float(site_config['reference_ambient'][0])
        reference_pressure = float(site_config['reference_pressure'][0])
    except Exception as e:
        print(str(e))
        return _get_response(500, "Site config missing required parameters.\
            Please ensure it includes latitude, longitude, elevation, \
            reference_ambient, and reference_pressure.")

    # Create the events class which does the calculations.
    e = Events(latitude, longitude, elevation, reference_ambient, reference_pressure)

    # This method returns a dict with all the items to return.
    events_dict = e.display_events()
    print(json.dumps(events_dict))
    return _get_response(200, events_dict)


if __name__=="__main__":
    siteevents({"queryStringParameters": {"site": "saf"}},{})
    

    import requests
    url = "https://api.photonranch.org/test/events?site=saf"
    print(json.dumps(requests.get(url).json(), indent=2))
    url = "https://api.photonranch.org/test/all/config"
    print(json.dumps(requests.get(url).json(), indent=2))
    #c = _get_site_config('saf')
    #print(c.keys())
    #print(c['longitude'])
    #print(c['elevation'])
    #print(c['reference_ambient'])
    #print(c['reference_pressure'])
    #print(c['latitude'])

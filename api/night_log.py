import os
import json
import time
from http import HTTPStatus

from api.helpers import dynamodb_r
from api.helpers import _get_body
from api.helpers import http_response

NIGHT_LOG_TABLE = dynamodb_r.Table(os.getenv('NIGHT_LOG_TABLE'))
SECONDS_PER_HOUR = 60 * 60


############################
######  Helpers  ###########
############################

def get_note(site):
    """Retrieve the details of a specified note from the night log table."""

    note = NIGHT_LOG_TABLE.get_item(
        Key={ "site": site } 
    )
    return note['Item']


def remove_note(site):
    """Deletes a specified note from the night log table."""

    NIGHT_LOG_TABLE.delete_item(
        Key={ "site": site}
    )
    return
    

def create_note(site, note_data):
    """Adds a note into the night log table at a specified site.
    
    The night log table is a DynamoDB table at AWS containing
    operations logs for each site. An operator can add a note
    to this table if needed.

    Args:
        site (str): Sitecode (eg. "saf").
        note_data (str): Body of note to be added.

    Returns:
        Note for specified site inserted into the DynamoDB night log table.
    """

    # Time to live timestamp two days from now
    now = int(time.time())
    ttl_hours = note_data['ttl_hours']
    ttl = now + (ttl_hours * SECONDS_PER_HOUR)

    response = NIGHT_LOG_TABLE.put_item(
        Item={ 
            "site": site,
            "created_timestamp": now,
            "ttl_timestamp_seconds": ttl,
            "note_data": note_data
            }
    )
    return response


############################
######  Handlers ###########
############################

def get_note_handler(event, context):
    """Handler method for retrieving a note from a specified site.
    
    Args:
        event.body.site (str): Sitecode (eg. "saf").

    Returns:
        200 status code with requested note details.
    """

    site = event['pathParameters']['site']
    try:
        note = get_note(site)
    except KeyError:
        return http_response(HTTPStatus.NOT_FOUND)
    return http_response(HTTPStatus.OK, note)
    

def create_note_handler(event, context):
    """Handler method for creating a note at a specified site.
    
    Args:
        event.body.site (str): Sitecode (eg. "saf").
        event.body.note_data (str): Body of note to be added.

    Returns:
        200 status code with successful creation of note at site.
    """

    body = _get_body(event)
    site = event['pathParameters']['site']
    note_data = body.get('note_data')
    create_note(site, note_data)
    return http_response(HTTPStatus.OK, 'Note created successfully')


def delete_note_handler(event, context):
    """Handler method for retrieving a note from a specified site.
    
    Args:
        event.body.site (str): Sitecode (eg. "saf").

    Returns:
        200 status code
    """

    site = event['pathParameters']['site']
    note = remove_note(site)
    return http_response(HTTPStatus.OK, note)

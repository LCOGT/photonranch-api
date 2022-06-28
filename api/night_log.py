import os
import json
import time
from http import HTTPStatus

from api.helpers import dynamodb_r
from api.helpers import _get_body
from api.helpers import http_response

NIGHT_LOG_TABLE = dynamodb_r.Table(os.getenv('NIGHT_LOG_TABLE'))

SECONDS_PER_DAY = 60 * 60 * 24

############################
######  Helpers  ###########
############################

def get_note(site):
    note = NIGHT_LOG_TABLE.get_item(
        Key={ "site": site } 
    )
    return note['Item']

def remove_note(site):
    NIGHT_LOG_TABLE.delete_item(
        Key={ "site": site}
    )
    return
    
def create_note(site, note_data):

    # time to live timestamp two days from now
    now = int(time.time())
    ttl = now + (2 * SECONDS_PER_DAY)

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
    site = event['pathParameters']['site']
    note = get_note(site)
    return http_response(HTTPStatus.OK, note)
    
def create_note_handler(event, context):
    body = _get_body(event)
    site = event['pathParameters']['site']
    note_data = body.get('note_data')
    create_note(site, note_data)
    return http_response(HTTPStatus.OK, 'Note created successfully')

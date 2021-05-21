
import json 
import os 
import boto3 
import decimal 
import sys 
import time 
import datetime 
import re 
import requests
import psycopg2
import logging
from http import HTTPStatus
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from botocore.client import Config

from api.helpers import BUCKET_NAME, REGION, S3_PUT_TTL, S3_GET_TTL
from api.helpers import dynamodb_r, ssm_c
from api.helpers import DecimalEncoder, http_response, _get_body, _get_secret, get_db_connection

db_host = _get_secret('db-host')
db_database = _get_secret('db-database')
db_user = _get_secret('db-user')
db_password = _get_secret('db-password')

log = logging.getLogger()
log.setLevel(logging.INFO)

info_images_table = dynamodb_r.Table(os.getenv('INFO_IMAGES_TABLE'))

def dummy_requires_auth(event, context):
    """ No purpose other than testing auth functionality """
    log.info(json.dumps(event, indent=2))

    return http_response(HTTPStatus.OK, "auth successful")


def default(event, context):
    log.info(json.dumps(event, indent=2))
    return http_response(HTTPStatus.OK, "New photon ranch API")


def upload(event, context): 
    """
    A request for a presigned post url requires the name of the object.
    This is sent in a single string under the key 'object_name' in the 
    json-string body of the request.

    Example request body:
    '{"object_name":"a_file.txt"}'

    This request will save an image into the main s3 bucket as:
    MAIN_BUCKET_NAME/data/a_file.txt

    * * *

    Here's how another Python program can use the presigned URL to upload a file:

    with open(object_name, 'rb') as f:
        files = {'file': (object_name, f)}
        http_response = requests.post(response['url'], data=response['fields'], files=files)
    # If successful, returns HTTP status code 204
    log.info(f'File upload HTTP status code: {http_response.status_code}')

    """
    log.info(json.dumps(event, indent=2))
    body = _get_body(event)
    
    # retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        log.warning(error_msg)
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    # get upload metadata
    metadata = body.get('metadata', None)
    if metadata is not None:
        metadata = json.dumps(json.loads(metadata), cls=DecimalEncoder)
    
    # TODO:
    # if applicable: add metadata to database
    #

    key = f"{s3_directory}/{body['object_name']}"
    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    url = json.dumps(s3.generate_presigned_post(
        Bucket = BUCKET_NAME,
        Key = key,
        ExpiresIn = S3_PUT_TTL
    ))
    log.info(f"Presigned upload url: {url}")
    return http_response(HTTPStatus.OK, url)


def download(event, context): 
    log.info(json.dumps(event, indent=2))
    body = _get_body(event)

    # retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        log.warning(error_msg)
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    key = f"{s3_directory}/{body['object_name']}"
    params = {
        "Bucket": BUCKET_NAME,
        "Key": key,
    }
    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params=params,
        ExpiresIn=S3_GET_TTL
    )
    log.info(f"Presigned download url: {url}")
    return http_response(HTTPStatus.OK, str(url))


def get_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table = dynamodb_r.Table('site_configurations')
    config = table.get_item(Key = { "site": site })
    return http_response(HTTPStatus.OK, config['Item'])


def put_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    body = _get_body(event)
    table = dynamodb_r.Table('site_configurations')
    response = table.put_item(Item = {
        "site": site,
        "configuration": body
    })
    return http_response(HTTPStatus.OK, response)


def delete_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table = dynamodb_r.Table('site_configurations')
    response = table.delete_item(Key={"site": site})
    return http_response(HTTPStatus.OK,response)


def all_config(event, context):
    log.info(json.dumps(event, indent=2))
    table = dynamodb_r.Table('site_configurations')
    response = table.scan()
    items = {}
    for entry in response['Items']: 
        items[entry['site']] = entry['configuration']
    return http_response(HTTPStatus.OK,items)


def get_status(event, context):
    # TODO: change site code to use the new endpoint directly, not this one.
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table_name = str(site)
    key = {"Type": "State"}
    table = dynamodb_r.Table(table_name)
    status =table.get_item(Key=key)
    return http_response(HTTPStatus.OK, {
        "site": site,
        "content": status['Item']
    })


def put_status(event, context):
    # TODO: change site code to use the new endpoint directly, not this one.
    log.info(json.dumps(event, indent=2))

    status_item = _get_body(event)
    status_item["Type"] = "State"

    site = event['pathParameters']['site']

    # Send status to the newer dynamodb table
    url = f"https://status.photonranch.org/status/{site}/status"
    payload = {
        "status": _get_body(event),
        "statusType": "deviceStatus",
    }
    log.info(f"Payload: {payload}")
    data = json.dumps(payload, cls=DecimalEncoder)
    response = requests.post(url, data=data)
    log.info(f"Status endpoint response: {response}")

    return http_response(HTTPStatus.OK, {
        "site": site,
    })

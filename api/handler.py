
import json 
import os 
import boto3 
import base64
from pprint import pprint
import psycopg2
import logging
from http import HTTPStatus
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from botocore.client import Config

from api.helpers import BUCKET_NAME, REGION, S3_PUT_TTL, S3_GET_TTL
from api.helpers import dynamodb_r
from api.helpers import DecimalEncoder, http_response, _get_body, _get_secret, get_db_connection
from api.helpers import get_base_filename_from_full_filename

from api.db import get_files_within_date_range

db_host = _get_secret('db-host')
db_database = _get_secret('db-database')
db_user = _get_secret('db-user')
db_password = _get_secret('db-password')

log = logging.getLogger()
log.setLevel(logging.INFO)

info_images_table = dynamodb_r.Table(os.getenv('INFO_IMAGES_TABLE'))
recent_uploads_table = dynamodb_r.Table(os.getenv('UPLOADS_LOG_TABLE_NAME'))
s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
lambda_client = boto3.client('lambda', REGION)

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
    '{"object_name":"a_file.txt", "s3_directory": "data"}'

    This request will save an image into the main s3 bucket as:
    MAIN_BUCKET_NAME/data/a_file.txt

    * * *

    Here's how another Python program can use the presigned URL to upload a file:

    with open(object_name, 'rb') as f:
        files = {'file': (object_name, f)}
        http_response = requests.post(response['url'], data=response['fields'], files=files)
    # If successful, returns HTTP status code 204
    log.info(f'File upload HTTP status code: {http_response.status_code}')

    * * *

    If the upload url is to be used with an info image, then the request must include 
    'info_channel' with a value of 1, 2, or 3.
    This will prompt an update to the info-images table, where it will store the provided
    base_filename in the row with pk=={site}#metadata, under the attribute channel{n}.

    For example, the request body 
    {
        "object_name": "tst-inst-20211231-00000001-EX10.jpg",
        "s3_directory": "info-images",
        "info_channel": 2
    }
    will result in the info-images table being updated with
    {
        "pk": "tst#metadata",
        "channel2": "tst-inst-20211231-00000001",
        ...
    }
    The URL returned by this endpoint will allow a POST request to s3 with the actual file. 
    The code that processes new s3 objects will see that it is an info image, then 
    query the info-images table to find which channel to use, and finally update the info-images
    table with an entry like
    {
        "pk": "tst#2",
        "jpg_10_exists": true,
        ...
    }
    This is the object that is queried to find the info image at site tst, channel 2. 
    """

    log.info(json.dumps(event, indent=2))
    body = _get_body(event)
    
    # retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    filename = body.get('object_name')
    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        log.warning(error_msg)
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    # if info image: get the channel number to use
    if s3_directory == 'info-images':

        site = filename.split('-')[0]
        base_filename = get_base_filename_from_full_filename(filename)
        channel = int(body.get('info_channel', 1))
        if channel not in [1,2,3]:
            error_msg = f"Value for info_channel must be either 1, 2, or 3. Recieved {channel} instead."
            log.warning(error_msg)
            return http_response(HTTPStatus.FORBIDDEN, error_msg)

        # create an entry to track metadata for the next info image that will be uploaded
        info_images_table.update_item(
            Key={ 'pk': f'{site}#metadata' },
            UpdateExpression=f"set channel{channel}=:basefilename",
            ExpressionAttributeValues={':basefilename': base_filename}
        )

    # get upload metadata
    metadata = body.get('metadata', None)
    if metadata is not None:
        metadata = json.dumps(json.loads(metadata), cls=DecimalEncoder)
    
    # TODO:
    # if applicable: add metadata to database
    #

    key = f"{s3_directory}/{body['object_name']}"
    url = s3.generate_presigned_post(
        Bucket = BUCKET_NAME,
        Key = key,
        ExpiresIn = S3_PUT_TTL
    )
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
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params=params,
        ExpiresIn=S3_GET_TTL
    )
    log.info(f"Presigned download url: {url}")
    return http_response(HTTPStatus.OK, str(url))

def download_zip(event, context):

    pprint(event)
    body = _get_body(event)
    pprint(body)

    start_timestamp_s = int(body.get('start_timestamp_s'))
    end_timestamp_s = int(body.get('end_timestamp_s'))
    fits_size = body.get('fits_size')
    site = body.get('site')

    files = get_files_within_date_range(site, start_timestamp_s, end_timestamp_s, fits_size)

    # Return 404 if no images fit the query.
    if len(files) == 0:
        return http_response(HTTPStatus.NOT_FOUND, 'No images exist for the given query.')

    print('number of files: ', len(files))
    print('first file: ', files[0])

    payload = json.dumps({
        'filenames': files
        }).encode('utf-8')

    response = lambda_client.invoke(
        FunctionName='zip-downloads-dev-zip',
        InvocationType='RequestResponse',
        LogType='Tail',
        Payload=payload
    )
    lambda_response = response['Payload'].read()

    zip_url = json.loads(json.loads(lambda_response)['body'])
    print(zip_url)

    log_response = base64.b64decode(response['LogResult']).decode('utf-8')
    pprint(log_response)

    logs = log_response.splitlines()
    pprint(logs)
    return http_response(HTTPStatus.OK, zip_url)

def get_recent_uploads(event, context):
    
    print("Query string params: ", event['queryStringParameters'])
    site = event['queryStringParameters']['site']
    response = recent_uploads_table.query(
        KeyConditionExpression=Key('site').eq(site)
    )
    results = response['Items']
    return http_response(HTTPStatus.OK, results) 
    
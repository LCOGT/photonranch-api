
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
from api.helpers import DecimalEncoder, http_response, _get_body, get_secret, get_db_connection
from api.helpers import get_base_filename_from_full_filename
from api.helpers import get_s3_file_url
from api.s3_helpers import save_tiff_to_s3
from api.db import get_files_within_date_range

db_host = get_secret('db-host')
db_database = get_secret('db-database')
db_user = get_secret('db-user')
db_password = get_secret('db-password')

log = logging.getLogger()
log.setLevel(logging.INFO)

info_images_table = dynamodb_r.Table(os.getenv('INFO_IMAGES_TABLE'))
recent_uploads_table = dynamodb_r.Table(os.getenv('UPLOADS_LOG_TABLE_NAME'))
s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
lambda_client = boto3.client('lambda', REGION)


def dummy_requires_auth(event, context):
    """No purpose other than testing auth functionality."""

    log.info(json.dumps(event, indent=2))
    log.info("Testing individual method deployment")
    return http_response(HTTPStatus.OK, "successful authorization")


def default(event, context):
    log.info(json.dumps(event, indent=2))
    return http_response(HTTPStatus.OK, "New photon ranch API")


def upload(event, context): 
    """Generates a presigned URL to upload files at AWS.

    A request for a presigned post URL requires the name of the object.
    This is sent in a single string under the key 'object_name' in the 
    json-string body of the request.

    Args:
        event.body.s3_directory (str): Name of the s3 bucket to use.
        event.body.filename (str): Name of the file to upload.

    Returns:
        204 status code with presigned upload URL string if successful.
        403 status code if incorrect s3 bucket or info channel supplied.

    Example request body:
        '{"object_name":"a_file.txt", "s3_directory": "data"}'
    This request will save an image into the main s3 bucket as:
        MAIN_BUCKET_NAME/data/a_file.txt

    * * *

    Another example Python program using the presigned URL to upload a file:

        with open(object_name, 'rb') as f:
            files = {'file': (object_name, f)}
            http_response = requests.post(
                    response['url'], data=response['fields'], files=files)
        # If successful, returns HTTP status code 204
        log.info(f'File upload HTTP status code: {http_response.status_code}')

    * * *

    If the upload URL is to be used with an info image, then
    the request must include 'info_channel' with a value of 1, 2, or 3.
    This will prompt an update to the info-images table, where it will
    store the provided base_filename in the row with pk=={site}#metadata,
    under the attribute channel{n}.

    For example, the request body:
        {
            "object_name": "tst-inst-20211231-00000001-EX10.jpg",
            "s3_directory": "info-images",
            "info_channel": 2
        }
    will result in the info-images table being updated with:
        {
            "pk": "tst#metadata",
            "channel2": "tst-inst-20211231-00000001",
            ...
        }
    The URL returned by this endpoint will allow a POST request
    to s3 with the actual file. The code that processes new s3 objects
    will see that it is an info image, then query the info-images table
    to find which channel to use, and finally update the info-images
    table with an entry like:
        {
            "pk": "tst#2",
            "jpg_10_exists": true,
            ...
        }
    This is the object that is queried to find the info image at
    site 'tst', channel 2. 
    """

    log.info(json.dumps(event, indent=2))
    body = _get_body(event)
    
    # Retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    filename = body.get('object_name')
    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        log.warning(error_msg)
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    # If info image: get the channel number to use
    if s3_directory == 'info-images':

        site = filename.split('-')[0]
        base_filename = get_base_filename_from_full_filename(filename)
        channel = int(body.get('info_channel', 1))
        if channel not in [1,2,3]:
            error_msg = f"Value for info_channel must be either 1, 2, or 3. Received {channel} instead."
            log.warning(error_msg)
            return http_response(HTTPStatus.FORBIDDEN, error_msg)

        # Create an entry to track metadata for the next info image that will be uploaded
        info_images_table.update_item(
            Key={ 'pk': f'{site}#metadata' },
            UpdateExpression=f"set channel{channel}=:basefilename",
            ExpressionAttributeValues={':basefilename': base_filename}
        )

    # Get upload metadata
    metadata = body.get('metadata', None)
    if metadata is not None:
        metadata = json.dumps(json.loads(metadata), cls=DecimalEncoder)
    
    # TODO: if applicable, add metadata to database

    key = f"{s3_directory}/{body['object_name']}"
    url = s3.generate_presigned_post(
        Bucket = BUCKET_NAME,
        Key = key,
        ExpiresIn = S3_PUT_TTL
    )
    log.info(f"Presigned upload url: {url}")
    return http_response(HTTPStatus.OK, url)


def download(event, context): 
    """Handles requests to download individual data files.
    
    Args:
        s3_directory (str):
            data | info-images | allsky | test,
            specifies the s3 object prefix (folder) where the data is stored.
            Default is 'data'.
        object_name (str):
            The full filename of the requested file. Appending this to the end
            of s3_directory should specify the full key for the object in s3.
        image_type (str):
            tif | fits, used if the requester wants a tif file created 
            from the underlying fits image. If so, the tif file is
            created on the fly. Default is 'fits'.
        stretch (str):
            linear | arcsinh, used to specify the stretch parameters if
            a tif file is requested. Default is 'arcsinh'.

    Returns:
        Status code 200 with presigned s3 download URL string
        that the requester can use to access the file, if successful.
        Otherwise, 403 status code.
    """

    log.info(event)
    body = _get_body(event)

    # Retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        log.warning(error_msg)
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    key = f"{s3_directory}/{body['object_name']}"  # Full path to object in s3 bucket
    params = {
        "Bucket": BUCKET_NAME,
        "Key": key,
    }
    
    image_type = body.get('image_type', 'fits')  # Assume 'tif' if not otherwise specified

    # Routine if TIFF file is specified
    if image_type in ['tif', 'tiff']:   
        stretch = body.get('stretch', 'arcsinh')
        #s3_destination_key = f"downloads/tif/{body['object_name']}"
        s3_destination_key = save_tiff_to_s3(BUCKET_NAME, key, stretch)
        url = get_s3_file_url(s3_destination_key)
        log.info(f"Presigned download url: {url}")
        return http_response(HTTPStatus.OK, str(url))

    # If TIFF file not requested, just get the file as-is from s3
    else: 
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params=params,
            ExpiresIn=S3_GET_TTL
        )
        log.info(f"Presigned download url: {url}")
        return http_response(HTTPStatus.OK, str(url))


def download_zip(event, context):
    """Returns a link to download a zip of multiple images in FITS format.

    First, get a list of files to be zipped based on
    the query parameters specified. Next, call a Lambda function
    (defined in the repository zip-downloads) that creates a zip
    from the list of specified files and uploads that back to s3,
    returning a presigned download URL. Finally, return the URL
    in the HTTP response to the requester.

    Args:
        event.body.start_timestamp_s: UTC datestring of starting time to query.
        event.body.end_timestamp_s: UTC datestring of ending time to query.
        event.body.fits_size: Size of the FITS file (eg. 'small', 'large').
        event.body.site: Sitecode to zip files from.

    Returns:
        200 status code with requested presigned URL at AWS.
        Otherwise, 404 status code if no images match the query.
    """

    body = _get_body(event)
    pprint(body)

    start_timestamp_s = int(body.get('start_timestamp_s'))
    end_timestamp_s = int(body.get('end_timestamp_s'))
    fits_size = body.get('fits_size')  # small | large | best
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
    """Queries for a list of files recently uploaded to s3.

    The logs routine is found in the ptrdata repository,
    in which a lambda funciton is triggered for new objects in the
    s3 bucket with prefix 'data/' (where all the regular site data is sent).

    This is mainly used for easier debugging, and is displayed in the PTR web UI. 

    Args:
        event.body.site: Sitecode to query recent files from.
        
    Returns:
        200 status code with list of recent files if successful.
        Otherwise, 404 status code if missing sitecode in request.
    """

    print("Query string params: ", event['queryStringParameters'])
    try: 
        site = event['queryStringParameters']['site']
    except: 
        msg = "Please be sure to include the sitecode query parameter."
        return http_response(HTTPStatus.NOT_FOUND, msg)

    # Results from across all sites
    if site == 'all': 
        response = recent_uploads_table.scan()
        results = response['Items']
    
    # Results for specific site
    else:
        response = recent_uploads_table.query(
            KeyConditionExpression=Key('site').eq(site)
        )
        results = response['Items']

    return http_response(HTTPStatus.OK, results) 
    

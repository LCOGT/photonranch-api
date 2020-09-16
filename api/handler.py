
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

def dummy_requires_auth(event, context):
    """ No purpose other than testing auth functionality """
    log.info(json.dumps(event, indent=2))

    return http_response(200, "auth successful")

def default(event, context):
    log.info(json.dumps(event, indent=2))
    return http_response(200, "New photon ranch API")

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
    key = 'data/' + body['object_name']
    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    url = json.dumps(s3.generate_presigned_post(
        Bucket = BUCKET_NAME,
        Key = key,
        ExpiresIn = S3_PUT_TTL
    ))
    logger.info(f"Presigned upload url: {url}")
    return http_response(200, url)

def download(event, context): 
    log.info(json.dumps(event, indent=2))
    body = _get_body(event)
    key = "data/"+body['object_name']
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
    return http_response(200, str(url))


# TODO: refactor this function so that it produces an image package for a 
# single image rather than a whole list at a time. 
def _generate_image_packages(db_query, cursor):
    """Build a dict that contains metadata and pointers to the image files.

    The frontend uses these 'image package' entities to represent each image
    obtained from an observation. 
    """

    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))

    # Note: this list of attributes must match the attributes from the
    # sql query passed in to this function.
    attributes = [
        'image_id',
        'base_filename',
        'site',
        'capture_date',
        'sort_date',
        'right_ascension',
        'declination',
        'ex00_fits_exists',
        'ex01_fits_exists',
        'ex10_fits_exists',
        'ex13_fits_exists',
        'ex10_jpg_exists',
        'ex13_jpg_exists',
        'altitude',
        'azimuth',
        'filter_used',
        'airmass',
        'exposure_time',
        'username',
        'user_id',
    ]
    image_packages = []
    try:
        for index, record in enumerate(db_query):
            image_package = dict(zip(attributes, record))
            image_package.update({'recency_order': index})
            
            # Format the capture_date to a javascript-ready timestamp (eg. miliseconds)
            capture_date = image_package['capture_date'].timetuple()
            capture_timestamp_ms = 1000*int(time.mktime(capture_date))
            image_package['capture_date'] = capture_timestamp_ms

            # Format the sort_date to a javascript-ready timestamp (eg. miliseconds)
            sort_date = image_package['sort_date'].timetuple()
            sort_timestamp_milis = 1000*int(time.mktime(sort_date))
            image_package['sort_date'] = sort_timestamp_milis

            # Extract site and base_filename for image path construction
            base_filename = image_package['base_filename']
            site = image_package['site']

            # Get url for the jpg
            jpg_url = ''
            if image_package['ex13_jpg_exists']: 
                full_jpg13_path = f"data/{base_filename}-EX13.jpg"
                jpg_url = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": BUCKET_NAME, "Key": full_jpg13_path},
                    ExpiresIn=S3_GET_TTL
                )
            elif image_package['ex10_jpg_exists']: 
                full_jpg10_path = f"data/{base_filename}-EX10.jpg"
                jpg_url = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": BUCKET_NAME, "Key": full_jpg10_path},
                    ExpiresIn=S3_GET_TTL
                )
            image_package.update({'jpg_url':jpg_url})

            # Add to the collection to return as long as the jpg preview exists.
            if image_package['ex10_jpg_exists']: 
                image_packages.append(image_package)

    except AttributeError:
        log.exception(('There was an error in the image package generation process. '
            'Check that attributes line up with query results.'))

    return image_packages

def get_image(event, context):
    """ This endpoint returns the image package for the requested file. """
    log.info(json.dumps(event, indent=2))

    # The requested file
    base_filename = event['pathParameters']['base_filename'] 

    # Connect to the database.
    connection = None
    try:
        connection_params = {
            'host': db_host,
            'database': db_database,
            'user': db_user,
            'password': db_password,
        }
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        error_msg = f"Problem connecting to the database. {error}"
        log.exception("Exception occurred, problem connecting to database") 
        return http_response(500, error_msg)
        
    # Build the sql query
    sql = (
        "SELECT "
            "image_id, "
            "base_filename, "
            "site, "
            "capture_date, "
            "sort_date, "
            "right_ascension, "
            "declination, "
            "ex00_fits_exists, " 
            "ex01_fits_exists, " 
            "ex10_fits_exists, " 
            "ex13_fits_exists, " 
            "ex10_jpg_exists, " 
            "ex13_jpg_exists, " 
            "altitude, "
            "azimuth, "
            "filter_used, "
            "airmass, "
            "exposure_time, "
            "username, "
            "user_id "
        "FROM images "
        "WHERE base_filename = %s "
    )
    sql_data = (base_filename, ) # values to inject. 
    images = []

    try:
        cursor.execute(sql, sql_data)
        db_query = cursor.fetchall()
    except (Exception, psycopg2.Error) as error :
        if connection is not None:
            connection.close()

        error_msg = f"Problem with database query: {error}"
        log.exception("problem with db query")
        return http_response(500, error_msg)

    image_packages = _generate_image_packages(db_query, cursor)

    # When the query returns nothing.
    if len(image_packages) == 0: 
        error_msg = f"Database query for {base_filename} returned empty."
        log.error(error_msg)
        return http_response(404, error_msg)

    if connection is not None:
        connection.close()

    # There should only be one image from the query matching the base_filename. 
    image_package = image_packages[0]

    return http_response(200, image_package)

def latest_images(event, context):
    ''' 
    Get the k most recent images in a site's s3 directory.
    '''
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    k = event['pathParameters']['k'] # number of images to return 

    query_params = event['queryStringParameters']

    connection = None
    try:
        connection_params = {
            'host': db_host,
            'database': db_database,
            'user': db_user,
            'password': db_password,
        }
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        log.exception("Connection to database failed.")
        return json.dumps([])
        
    sql = (
        "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
        "ex00_fits_exists, " 
        "ex01_fits_exists, " 
        "ex10_fits_exists, " 
        "ex13_fits_exists, " 
        "ex10_jpg_exists, " 
        "ex13_jpg_exists, " 
        "altitude, azimuth, filter_used, airmass, "
        "exposure_time, username, user_id "
        "FROM images "
        "WHERE site = %s "
        "AND capture_date is not null "
        "ORDER BY sort_date "
        "DESC LIMIT %s "
    )
    sql_data = (site, k)
    images = []

    # If we need to only return images from the user, use different sql:
    if query_params and "userid" in query_params.keys():
        userid = query_params['userid']
        sql = (
            "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
            "ex00_fits_exists, " 
            "ex01_fits_exists, " 
            "ex10_fits_exists, " 
            "ex13_fits_exists, " 
            "ex10_jpg_exists, " 
            "ex13_jpg_exists, " 
            "altitude, azimuth, filter_used, airmass, "
            "exposure_time, username, user_id "
            "FROM images "
            "WHERE site = %s "
            "AND user_id = %s "
            "AND capture_date is not null "
            "ORDER BY sort_date "
            "DESC LIMIT %s "
        )
        sql_data = (site, userid, k)

    try:
        cursor.execute(sql, sql_data)
        db_query = cursor.fetchall()
        images = _generate_image_packages(db_query, cursor)
    except (Exception, psycopg2.Error) as error :
        log.exception("Error while retrieving db records")

    if connection is not None:
        connection.close()

    return http_response(200, images)

def filtered_image_query(event, context):
    log.info(json.dumps(event, indent=2))

    filter_params = event['queryStringParameters']

    connection = None
    connection_params = {
        'host': db_host,
        'database': db_database,
        'user': db_user,
        'password': db_password,
    }
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    #retrieve images with given filter parameters
    #images = rds.filtered_images(cursor, filter_params)
    sql = [
    "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
    "ex00_fits_exists, " 
    "ex01_fits_exists, " 
    "ex10_fits_exists, " 
    "ex13_fits_exists, " 
    "ex10_jpg_exists, " 
    "ex13_jpg_exists, " 
    "altitude, azimuth, filter_used, airmass, "
    "exposure_time, username, user_id"

    "FROM images img "
    "INNER JOIN users usr "
    "ON usr.user_id = img.created_user "
    "WHERE usr.user_name = %s "
    ]
    
    username = filter_params.get('username', None)
    filename = filter_params.get('filename', None)
    exposure_time_min = filter_params.get('exposure_time_min', None)
    exposure_time_max = filter_params.get('exposure_time_max', None)
    site = filter_params.get('site', None)
    filter = filter_params.get('filter', None)
    start_date = filter_params.get('start_date', None)
    end_date = filter_params.get('end_date', None)

    # We need to query at least one parameter. 
    params = [username, ]

    if filename:
        sql.append("AND base_filename=%s ")
        params.append(filename)

    if exposure_time_min and exposure_time_max:
        sql.append("AND exposure_time BETWEEN %s AND %s ")
        params.append(exposure_time_min)
        params.append(exposure_time_max)
    elif exposure_time_min:
        sql.append("AND exposure_time=%s ")
        params.append(exposure_time_min)

    if site:
        sql.append("AND site= %s ")
        params.append(site)

    if filter:
        sql.append("AND filter_used=%s ")
        params.append(filter)

    if start_date and end_date:
        sql.append("AND capture_date BETWEEN %s AND %s ")
        params.append(start_date)
        params.append(end_date)

    sql.append("ORDER BY sort_date DESC ")
    sql = ' '.join(sql)
    params = tuple(params)

    try:
        cursor.execute(sql, params)
        db_query = cursor.fetchall()
        images = _generate_image_packages(db_query, cursor)
    except (Exception, psycopg2.Error) as error :
        log.exception("Error while retrieving records")
        return http_response(500, error)

    if connection is not None:
        connection.close()
    
    return http_response(200, images)

def get_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table = dynamodb_r.Table('site_configurations')
    config = table.get_item(Key={"site": site})
    return http_response(200, config['Item'])
def put_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    body = _get_body(event)
    table = dynamodb_r.Table('site_configurations')
    response = table.put_item(Item={
        "site": site,
        "configuration": body
    })
    return http_response(200,response)
def delete_config(event, context):
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table = dynamodb_r.Table('site_configurations')
    response = table.delete_item(Key={"site": site})
    return http_response(200,response)

def all_config(event, context):
    log.info(json.dumps(event, indent=2))
    table = dynamodb_r.Table('site_configurations')
    response = table.scan()
    items = {}
    for entry in response['Items']: 
        items[entry['site']] = entry['configuration']
    return http_response(200,items)

def get_fits_header_from_db(event, context):
    # TODO: Clean this up!
    log.info(json.dumps(event, indent=2))
    base_filename = event['pathParameters']['baseFilename']
    site = base_filename[:3]
    header = []
    connection = None
    connection_params = {
        'host': db_host,
        'database': db_database,
        'user': db_user,
        'password': db_password,
    }
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()
    sql = "SELECT header FROM images WHERE base_filename = %s"
    try: 
        cursor.execute(sql, (base_filename,))
        header = cursor.fetchone()
        if header[0]: 
            result = json.loads(header[0])
        else: 
            result = []
    except (Exception, psycopg2.Error) as error :
        log.exception("error while retrieving records")
        return http_response(500, "Unable to retrieve header.")
    result = json.loads(header[0])
    return http_response(200, result)

def get_status(event, context):
    # TODO: change site code to use the new endpoint directly, not this one.
    log.info(json.dumps(event, indent=2))
    site = event['pathParameters']['site']
    table_name = str(site)
    key = {"Type": "State"}
    table = dynamodb_r.Table(table_name)
    status =table.get_item(Key=key)
    return http_response(200, {
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

    return http_response(200, {
        "site": site,
    })

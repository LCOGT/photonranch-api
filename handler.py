import json, os, boto3, decimal, sys, time, datetime, re, requests
import psycopg2
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from botocore.client import Config

from helpers import DecimalEncoder, _get_response, _get_body, _get_secret, get_db_connection


BUCKET_NAME = 'photonranch-001'
REGION = 'us-east-1'
S3_PUT_TTL = 300
S3_GET_TTL = 3600

dynamodb_r = boto3.resource('dynamodb', REGION)
ssm_c = boto3.client('ssm')


def _generate_image_packages(db_query, cursor):
    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    attributes = [
        'image_id',
        'base_filename',
        'site',
        'capture_date',
        'sort_date',
        'right_ascension',
        'declination',
        'ex01_fits_exists',
        'ex13_fits_exists',
        'ex13_jpg_exists',
        'altitude',
        'azimuth',
        'filter_used',
        'airmass',
        'exposure_time',
        'created_user'
        ]
    image_packages = []
    try:
        for index, record in enumerate(db_query):
            image_package = dict(zip(attributes, record))
            image_package.update({'recency_order': index})
            
            # Format the capture_date to a javascript-ready timestamp (eg. miliseconds)
            capture_date = image_package['capture_date'].timetuple()
            capture_timestamp_milis = 1000*int(time.mktime(capture_date))
            image_package['capture_date'] = capture_timestamp_milis

            # Format the sort_date to a javascript-ready timestamp (eg. miliseconds)
            sort_date = image_package['sort_date'].timetuple()
            sort_timestamp_milis = 1000*int(time.mktime(sort_date))
            image_package['sort_date'] = sort_timestamp_milis

            # Extract site and base_filename for image path construction
            base_filename = image_package['base_filename']
            site = image_package['site']

            jpg13_url = ''
            # Get urls to some of the images, if they exist
            if image_package['ex13_jpg_exists']: 
                full_jpg13_path = f"{site}/raw_data/2019/{base_filename}-EX13.jpg"
                jpg13_url = s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": BUCKET_NAME, "Key": full_jpg13_path},
                    ExpiresIn=S3_GET_TTL
                )
            image_package.update({'jpg13_url': jpg13_url})

            image_packages.append(image_package)
    except AttributeError:
        print('There was an error in the image package generation process. Check that sttributes line up with query results.')

    return image_packages

def ping(event, context):
    print(json.dumps(event))
    return _get_response(200, "pong")

def default(event, context):
    return _get_response(200, "New photon ranch API")

def upload(event, context): 
    """
    A request for a presigned post url requires the name of the object
    and the path at which it is stored. This is sent in a single string under
    the key 'object_name' in the json-string body of the request.

    Example request body:
    '{"object_name":"raw_data/2019/a_file.txt"}'

    This request will save an image into the main s3 bucket as:
    MAIN_BUCKET_NAME/site/raw_data/2019/img001.fits

    * * *

    Here's how another Python program can use the presigned URL to upload a file:

    with open(object_name, 'rb') as f:
        files = {'file': (object_name, f)}
        http_response = requests.post(response['url'], data=response['fields'], files=files)
    # If successful, returns HTTP status code 204
    logging.info(f'File upload HTTP status code: {http_response.status_code}')

    """
    print(json.dumps(event))
    body = _get_body(event)
    site = event['pathParameters']['site']
    key = f"{site}/{body['object_name']}"
    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    url = json.dumps(s3.generate_presigned_post(
        Bucket = BUCKET_NAME,
        Key = key,
        ExpiresIn = S3_PUT_TTL
    ))
    print(f"Presigned upload url: {url}")
    return _get_response(200, url)

def download(event, context): 
    print(json.dumps(event))
    body = _get_body(event)
    site = event['pathParameters']['site']
    key = f"{site}/{body['object_name']}"
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
    print(f"Presigned download url: {url}")
    return _get_response(200, str(url))

def latest_image(event, context):
    ''' 
    Get the k most recent jpgs in a site's s3 directory.
    '''
    site = event['pathParameters']['site']
    connection = None
    try:
        connection_params = {
            'host': _get_secret('db-host'),
            'database': _get_secret('db-database'),
            'user': _get_secret('db-user'),
            'password': _get_secret('db-password')
        }
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Connection to database failed.")
        print(error)
        return json.dumps([])
        
    # List of k last modified files returned from ptr archive query
    #latest_k_files = rds.get_last_modified_by_site(cursor, connection, site, k)
    sql = (
        "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
        "ex01_fits_exists, ex13_fits_exists, ex13_jpg_exists, altitude, azimuth, filter_used, airmass, "
        "exposure_time, created_user "
        "FROM images "
        "WHERE site = %s "
        "AND capture_date is not null "
        "ORDER BY sort_date "
        "DESC LIMIT %s "
    )
    images = []
    try:
        k = 1 # we want the single latest image
        cursor.execute(sql, (site, k))
        db_query = cursor.fetchall()
        images = _generate_image_packages(db_query, cursor)
    except (Exception, psycopg2.Error) as error :
        print("Error while retrieving records:", error)
    if connection is not None:
        connection.close()

    return _get_response(200, images)

def latest_images(event, context):
    ''' 
    Get the k most recent jpgs in a site's s3 directory.
    '''
    site = event['pathParameters']['site']
    k = event['pathParameters']['k'] # number of images to return 
    connection = None
    try:
        connection_params = {
            'host': _get_secret('db-host'),
            'database': _get_secret('db-database'),
            'user': _get_secret('db-user'),
            'password': _get_secret('db-password')
        }
        connection = psycopg2.connect(**connection_params)
        cursor = connection.cursor()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Connection to database failed.")
        print(error)
        return json.dumps([])
        
    # List of k last modified files returned from ptr archive query
    #latest_k_files = rds.get_last_modified_by_site(cursor, connection, site, k)
    sql = (
        "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
        "ex01_fits_exists, ex13_fits_exists, ex13_jpg_exists, altitude, azimuth, filter_used, airmass, "
        "exposure_time, created_user "
        "FROM images "
        "WHERE site = %s "
        "AND capture_date is not null "
        "ORDER BY sort_date "
        "DESC LIMIT %s "
    )
    images = []
    try:
        cursor.execute(sql, (site, k))
        db_query = cursor.fetchall()
        images = _generate_image_packages(db_query, cursor)
    except (Exception, psycopg2.Error) as error :
        print("Error while retrieving records:", error)

    if connection is not None:
        connection.close()

    return _get_response(200, images)


def get_config(event, context):
    print(json.dumps(event))
    site = event['pathParameters']['site']
    table = dynamodb_r.Table('site_configurations')
    config = table.get_item(Key={"site": site})
    return _get_response(200, config['Item'])
def put_config(event, context):
    print(json.dumps(event))
    site = event['pathParameters']['site']
    body = _get_body(event)
    table = dynamodb_r.Table('site_configurations')
    response = table.put_item(Item={
        "site": site,
        "configuration": body
    })
    return _get_response(200,response)
def all_config(event, context):
    print(json.dumps(event))
    table = dynamodb_r.Table('site_configurations')
    response = table.scan()
    items = {}
    for entry in response['Items']: 
        items[entry['site']] = entry['configuration']
    return _get_response(200,items)

def get_fits_header(event, context):
    # TODO: Clean this up!
    #site = event['pathParameters']['site']
    base_filename = event['pathParameters']['baseFilename']
    site = base_filename[:3]
    header = []
    connection = None
    connection_params = {
        'host': _get_secret('db-host'),
        'database': _get_secret('db-database'),
        'user': _get_secret('db-user'),
        'password': _get_secret('db-password')
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
        print("Error while retrieving records:", error)
        return _get_response(500, "Unable to retrieve header.")
    result = json.loads(header[0])
    return _get_response(200, result)

def get_fits_01(event, context):
    '''
    Get the full raw (01) fits image url
    '''
    base_filename = event['pathParameters']['baseFilename']
    site = base_filename[:3]
    key = f"{site}/raw_data/2019/{base_filename}-EX01.fits.bz2"
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
    return _get_response(200, url)

def get_fits_13(event, context):
    '''
    Get the smaller raw (13) fits image url
    '''
    base_filename = event['pathParameters']['baseFilename']
    site = base_filename[:3]
    key = f"{site}/raw_data/2019/{base_filename}-EX13.fits.bz2"
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
    return _get_response(200, url)

def filtered_image_query(event, context):
    print(json.dumps(event))

    filter_params = event['queryStringParameters']

    connection = None
    connection_params = {
        'host': _get_secret('db-host'),
        'database': _get_secret('db-database'),
        'user': _get_secret('db-user'),
        'password': _get_secret('db-password')
    }
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    #retrieve images with given filter parameters
    #images = rds.filtered_images(cursor, filter_params)
    sql = [
    "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
    "ex01_fits_exists, ex13_fits_exists, ex13_jpg_exists, altitude, azimuth, filter_used, airmass, "
    "exposure_time, user_name "

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
        print("Error while retrieving records:", error)
        return _get_response(500, error)

    if connection is not None:
        connection.close()
    
    return _get_response(200, images)

def image_by_user(event, context):
    print(json.dumps(event))

    #filter_params = event['queryStringParameters']
    filter_params = {}

    username = event['pathParameters']['user_id']

    connection = None
    connection_params = {
        'host': _get_secret('db-host'),
        'database': _get_secret('db-database'),
        'user': _get_secret('db-user'),
        'password': _get_secret('db-password')
    }
    connection = psycopg2.connect(**connection_params)
    cursor = connection.cursor()

    sql = [
    "SELECT image_id, base_filename, site, capture_date, sort_date, right_ascension, declination, "
    "ex01_fits_exists, ex13_fits_exists, ex13_jpg_exists, altitude, azimuth, filter_used, airmass, "
    "exposure_time, user_name "

    "FROM images img "
    "INNER JOIN users usr "
    "ON usr.user_id = img.created_user "
    "WHERE usr.user_name = %s "
    ]
    
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
        print("Error while retrieving records:", error)
        return _get_response(200,'error while retrieving records')

    if connection is not None:
        connection.close()
    
    return _get_response(200, images)

def get_command(event, context):
    print(json.dumps(event))
    sqs_c = boto3.client('sqs', REGION)
    site = event['pathParameters']['site']
    mount = event['pathParameters']['mount']
    queue_name = f"{site}_{mount}.fifo"
    print(f"queue name: {queue_name}")
    queue = sqs_c.get_queue_url(
        QueueName=queue_name,
    )
    print(queue)
    response = sqs_c.receive_message(
        QueueUrl=queue['QueueUrl'],
        MaxNumberOfMessages=1,
        VisibilityTimeout=10, # my notes tell me this shouldn't be 0 (?)
        WaitTimeSeconds=3
    )
    print(response)
    try:
        message = response['Messages'][0]
        # receipt_handle is used to delete the entry from the queue.
        receipt_handle = message['ReceiptHandle']
        delete_response = sqs_c.delete_message(QueueUrl=queue['QueueUrl'], ReceiptHandle=receipt_handle)
        return _get_response(200, json.loads(message['Body']))
    except KeyError as e:
        print(e)
        return _get_response(200, {})

    return _get_response(200, 'Empy placeholder function')
def post_command(event, context):
    print(json.dumps(event))
    body = _get_body(event)
    body = json.dumps(body)
    sqs_c = boto3.client('sqs', REGION)
    site = event['pathParameters']['site']
    mount = event['pathParameters']['mount']
    queue_name = f"{site}_{mount}.fifo"
    queue = sqs_c.get_queue_url(
        QueueName=queue_name,
    )
    # All messages with this group id will maintain FIFO ordering.
    messageGroupId = 'primary_message_group_id'
    response = sqs_c.send_message(
        QueueUrl=queue['QueueUrl'],
        MessageBody=body,
        MessageGroupId=messageGroupId,
    )
    return _get_response(200, response)

def options_command(event, context):
    return _get_response(200, '')

def get_status(event, context):
    site = event['pathParameters']['site']
    table_name = str(site)
    key = {"Type": "State"}
    table = dynamodb_r.Table(table_name)
    status =table.get_item(Key=key)
    return _get_response(200, {
        "site": site,
        "content": status['Item']
    })
def put_status(event, context):
    status_item = _get_body(event)
    status_item["Type"] = "State"

    site = event['pathParameters']['site']
    table_name = str(site)
    table = dynamodb_r.Table(table_name)

    status = table.put_item(Item=status_item)

    # Also send status to the newer dynamodb table
    url = f"https://status.photonranch.org/status/{site}/status"
    payload = {
        "status": _get_body(event),
        "statusType": "deviceStatus",
    }
    print(f"payload: {payload}")
    response = requests.post(url, data=json.dumps(payload))
    print("alt status response: ")
    print(response)


    return _get_response(200, {
        "site": site,
        "content": status
    })

if __name__=="__main__":
    print("hello")
    db_host = _get_secret('db-host')
    print(db_host)

    streamHandlerEvent = {
        "Records": [
            {
                "eventID": "8fa90daf0b22a7cb2d6f0b41b6b15c8a",
                "eventName": "INSERT",
                "eventVersion": "1.1",
                "eventSource": "aws:dynamodb",
                "awsRegion": "us-east-1",
                "dynamodb": {
                    "ApproximateCreationDateTime": 1581091425,
                    "Keys": {
                        "site": {
                            "S": "wmd"
                        },
                        "ulid": {
                            "S": "01E0GEY4GZNYRP3JYGSAXZ13CY"
                        }
                    },
                    "NewImage": {
                        "deviceInstance": {
                            "S": "camera1"
                        },
                        "deviceType": {
                            "S": "camera"
                        },
                        "optional_params": {
                            "M": {}
                        },
                        "site": {
                            "S": "wmd"
                        },
                        "statusId": {
                            "S": "UNREAD#01E0GEY4GZNYRP3JYGSAXZ13CY"
                        },
                        "ulid": {
                            "S": "01E0GEY4GZNYRP3JYGSAXZ13CY"
                        },
                        "required_params": {
                            "M": {}
                        },
                        "action": {
                            "S": "stop"
                        },
                        "timestamp_ms": {
                            "N": "1581091424628"
                        }
                    },
                    "SequenceNumber": "34094600000000017645425689",
                    "SizeBytes": 218,
                    "StreamViewType": "NEW_AND_OLD_IMAGES"
                },
                "eventSourceARN": "arn:aws:dynamodb:us-east-1:306389350997:table/photonranch-jobs1/stream/2020-02-06T18:04:45.173"
            }
        ]
    }

    print(latest_image({"pathParameters": {"site": "wmd"}}, {}))
import boto3
import os
import json
import psycopg2
import decimal
import logging

from botocore.client import Config

BUCKET_NAME = os.environ['S3_BUCKET_NAME']
CONFIG_TABLE_NAME = os.environ['CONFIG_TABLE_NAME']
REGION = os.environ['REGION']
S3_PUT_TTL = 300
S3_GET_TTL = 86400 * 5  # 5 days before s3 image links expire

dynamodb_r = boto3.resource('dynamodb', REGION)
ssm_c = boto3.client('ssm', region_name=REGION)

log = logging.getLogger()
log.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON."""
    
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 != 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def json_dumps_ddb(o):
    return json.dumps(o, cls=DecimalEncoder)

def http_response(status_code, body):
    """Returns a given HTTP status code."""

    if not isinstance(body, str):
        body = json.dumps(body,cls=DecimalEncoder)
    return {
        "statusCode": status_code, 
        "headers": {
            # Required for CORS support to work
            "Access-Control-Allow-Origin": "*",
            # Required for cookies, authorization headers with HTTPS
            "Access-Control-Allow-Credentials": "true",
        },
        "body": body
    }


def _get_body(event):
    try:
        return json.loads(event.get("body", ""), parse_float=decimal.Decimal)
    except:
        log.exception("event body could not be JSON decoded.")
        return {}


def get_secret(key):
    """Gets environment secrets from the AWS Parameter Store.

    Some parameters are stored in AWS Systems Manager Parameter Store.
    This replaces the .env variables we used to use with flask.
    """

    resp = ssm_c.get_parameter(
    	Name=key,
    	WithDecryption=True
    )
    return resp['Parameter']['Value']


def get_db_connection():
    """Connects to psycopg2 database."""

    connection_params = {
        'host': get_secret('db-host'),
        'database': get_secret('db-database'),
        'user': get_secret('db-user'),
        'password': get_secret('db-password')
    }
    connection = psycopg2.connect(**connection_params)
    return connection


def get_s3_image_path(base_filename, datatype, reduction_level, file_extension):
    """Gets the path to a file at AWS."""

    full_filename = f"{base_filename}-{datatype}{reduction_level}.{file_extension}"
    path = f"data/{full_filename}"
    return path


def get_base_filename_from_full_filename(full_filename):
    """Converts a full filename string to its base filename.

    Args:
        full_filename (str):
            Name of the file with file extensions
            (eg. tst001-inst-20210525-00000123-EX01.fits.bz2).

    Returns:
        Converted filename string in the format tst001-inst-20210525-00000123.
    """

    return full_filename.split('.')[0].rsplit('-', 1)[0]


def get_s3_file_url(path, ttl=604800):
    """Generates a presigned URL for a file at AWS."""

    s3 = boto3.client('s3', REGION, config=Config(signature_version='s3v4'))
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": path},
        ExpiresIn=ttl
    )
    return url


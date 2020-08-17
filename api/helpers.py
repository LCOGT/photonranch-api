import boto3
import os
import json
import psycopg2
import decimal

BUCKET_NAME = os.environ['S3_BUCKET_NAME']
REGION = os.environ['REGION']
S3_PUT_TTL = 300
S3_GET_TTL = 3600

dynamodb_r = boto3.resource('dynamodb', REGION)
ssm_c = boto3.client('ssm')


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def _get_response(status_code, body):
    if not isinstance(body, str):
        body = json.dumps(body,cls=DecimalEncoder)
    return {
        "statusCode": status_code, 
        "headers": {
            # Required for CORS support to work
            "Access-Control-Allow-Origin": "*",
            # Required for cookies, authorization headers with HTTPS
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "*",
            "Content-Type": "application/json",
        },
        "body": body
    }

def _get_body(event):
    try:
        return json.loads(event.get("body", ""), parse_float=decimal.Decimal)
    except:
        print("event body could not be JSON decoded.")
        return {}

def _get_secret(key):
    """
    Some parameters are stored in AWS Systems Manager Parameter Store.
    This replaces the .env variables we used to use with flask.
    """
    resp = ssm_c.get_parameter(
    	Name=key,
    	WithDecryption=True
    )
    return resp['Parameter']['Value']

def get_db_connection():
    connection_params = {
        'host': _get_secret('db-host'),
        'database': _get_secret('db-database'),
        'user': _get_secret('db-user'),
        'password': _get_secret('db-password')
    }
    connection = psycopg2.connect(**connection_params)
    return connection

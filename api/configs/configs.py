import json
import jsonschema
from http import HTTPStatus
import boto3

from api.helpers import dynamodb_r
from api.helpers import DecimalEncoder
from api.helpers import json_dumps_ddb
from api.configs.validation_schemas import wema_config_schema
from api.configs.validation_schemas import platform_config_schema

table = dynamodb_r.Table("WemaPlatformConfigs")

######################################
###### DynamoDB Table Design  ########
######################################

"""
TABLE STRUCTURE 

Store the data in the table:

To store a WEMA config:
ConfigID: [wema_id]
ConfigType: WEMA
Config: {WEMA JSON}
To store a platform:

To store a platform config:
ConfigID: [platform_id]
ConfigType: PLATFORM
Config: {Platform JSON}
WemaID: [Associated wema_id] (Store the associated wema_id as an attribute in the platform item)
"""

""" 
QUERY AND WRITE PATTERNS

Get a WEMA:
Query by the partition key (ConfigID = [wema_id]) and sort key (ConfigType = WEMA).

Get a WEMA and all its platforms:
Scan the table for items with the sort key ConfigType = PLATFORM and filter the results by the wema_id attribute.

Get a platform and its associated WEMA:
Query the platform by the partition key (ConfigID = [platform_id]) and sort key (ConfigType = PLATFORM).
Get the associated WEMA by querying the partition key (ConfigID = [Associated wema_id]) and 
sort key (ConfigType = WEMA).

Write a WEMA:
Insert a new item with the partition key (ConfigID = [wema_id]), sort key (ConfigType = WEMA), and the 
WEMA JSON as the Config attribute.

Write a platform:
Insert a new item with the partition key (ConfigID = [platform_id]), sort key (ConfigType = PLATFORM), 
the platform JSON as the Config attribute, and the associated wema_id.
"""


def filter_json(data, schema):
    if 'properties' in schema:
        filtered_data = {}
        for key, subschema in schema['properties'].items():
            if key in data:
                filtered_data[key] = filter_json(data[key], subschema)
        return filtered_data
    elif 'type' in schema and schema['type'] == 'array' and 'items' in schema:
        return [filter_json(item, schema['items']) for item in data]
    else:
        return data

#####################################
#####  Query and Write Methods  #####
#####################################

def get_wema(wema_id):
    response = table.get_item(
        Key={
            'ConfigID': wema_id,
            'ConfigType': 'WEMA'
        }
    )
    return response.get('Item')

def get_wema_and_all_platforms(wema_id):
    response = table.scan(
        FilterExpression="ConfigType = :platform AND WemaID = :wema_id",
        ExpressionAttributeValues={
            ":platform": "PLATFORM",
            ":wema_id": wema_id
        }
    )
    wema = get_wema(wema_id)
    platforms = response.get('Items')
    return wema, platforms

def get_platform_and_associated_wema(platform_id):
    response = table.get_item(
        Key={
            'ConfigID': platform_id,
            'ConfigType': 'PLATFORM'
        }
    )
    platform = response.get('Item')
    if platform:
        wema_id = platform.get('WemaID')
        wema = get_wema(wema_id)
        return platform, wema
    return None, None

def write_wema(wema_id, wema_config):
    table.put_item(
        Item={
            'ConfigID': wema_id,
            'ConfigType': 'WEMA',
            'Config': wema_config
        }
    )

def write_platform(platform_id, wema_id, platform_config):
    table.put_item(
        Item={
            'ConfigID': platform_id,
            'ConfigType': 'PLATFORM',
            'WemaID': wema_id,
            'Config': platform_config
        }
    )

def get_all_wemas():
    response = table.scan(
        FilterExpression="ConfigType = :wema",
        ExpressionAttributeValues={
            ":wema": "WEMA"
        }
    )
    wemas = response.get('Items')
    wemas_dict = {wema['ConfigID']: wema['Config'] for wema in wemas}
    return wemas_dict


############################
######  Handlers ###########
############################

def get_wema_handler(event, context):
    wema_id = event['pathParameters']['wema_id']
    wema = get_wema(wema_id)

    if wema:
        return {
            'statusCode': HTTPStatus.OK,
            'body': json.dumps(wema)
        }
    else:
        return {
            'statusCode': HTTPStatus.NOT_FOUND,  # 404
            'body': 'WEMA not found'
        }

def get_wema_and_all_platforms_handler(event, context):
    wema_id = event['pathParameters']['wema_id']
    wema, platforms = get_wema_and_all_platforms(wema_id)

    if wema:
        return {
            'statusCode': HTTPStatus.OK,  # 200
            'body': json.dumps({
                'wema': wema,
                'platforms': platforms
            })
        }
    else:
        return {
            'statusCode': HTTPStatus.NOT_FOUND,  # 404
            'body': 'WEMA not found'
        }

def get_platform_and_associated_wema_handler(event, context):
    platform_id = event['pathParameters']['platform_id']
    platform, wema = get_platform_and_associated_wema(platform_id)

    if platform:
        return {
            'statusCode': HTTPStatus.OK,  # 200
            'body': json.dumps({
                'platform': platform,
                'wema': wema
            })
        }
    else:
        return {
            'statusCode': HTTPStatus.NOT_FOUND,  # 404
            'body': 'Platform not found'
        }

def write_wema_handler(event, context):
    request_body = json.loads(event['body'])
    wema_config = request_body['config']
    wema_id = request_body['wema_id']

    # Validate the config against the JSON schema
    try:
        jsonschema.validate(wema_config, wema_config_schema)
    except jsonschema.ValidationError as e:
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,  # 400
            'body': str(e)
        }

    simple_wema_config = filter_json(wema_config, wema_config_schema)
    write_wema(wema_id, json_dumps_ddb(wema_config))

    return {
        'statusCode': HTTPStatus.CREATED,  # 201
        'body': 'WEMA created'
    }

def write_platform_handler(event, context):
    request_body = json.loads(event['body'])
    platform_id = request_body['platform_id']
    wema_id = request_body['wema_id']
    platform_config = request_body['config']

    # Validate the config against the JSON schema
    try:
        jsonschema.validate(platform_config, platform_config_schema)
    except jsonschema.ValidationError as e:
        return {
            'statusCode': HTTPStatus.BAD_REQUEST,  # 400
            'body': str(e)
        }

    write_platform(platform_id, wema_id, json_dumps_ddb(platform_config))

    return {
        'statusCode': HTTPStatus.CREATED,  # 201
        'body': 'Platform created'
    }
    
def get_all_wemas_handler(event, context):
    wemas = get_all_wemas()

    return {
        'statusCode': HTTPStatus.OK,  # 200
        'body': json.dumps(wemas)
    }

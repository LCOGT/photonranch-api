import json
import time
import uuid
import boto3
import logging
import os
from http import HTTPStatus
from boto3.dynamodb.conditions import Key, Attr

from api.helpers import http_response, _get_body, dynamodb_r

# Serverless.yml dynamodb table definition, for reference
# Removed from serverless.yml after it was created to avoid duplication errors
# in subsequent deployments.
#
# PipeQueueTable:
#   Type: AWS::DynamoDB::Table
#   Properties:
#     TableName: ${self:provider.environment.PIPE_QUEUE_TABLE_NAME}
#     BillingMode: PAY_PER_REQUEST
#     AttributeDefinitions:
#       - AttributeName: pk
#         AttributeType: S
#       - AttributeName: sk
#         AttributeType: S
#     KeySchema:
#       - AttributeName: pk
#         KeyType: HASH
#       - AttributeName: sk
#         KeyType: RANGE
#     StreamSpecification:
#       StreamViewType: NEW_AND_OLD_IMAGES

# Configure logging
log = logging.getLogger()
log.setLevel(logging.INFO)

# Initialize DynamoDB table resource
PIPE_QUEUE_TABLE = dynamodb_r.Table(os.getenv('PIPE_QUEUE_TABLE_NAME'))

# Item types
QUEUE_ITEM = 'QUEUE_ITEM'
STATUS_ITEM = 'STATUS_ITEM'

#############################
###### Helper Methods #######
#############################

def generate_queue_item_id():
    """Generates a unique ID for queue items with timestamp prefix for FIFO ordering."""
    timestamp = int(time.time() * 1000)  # Millisecond timestamp
    unique_id = str(uuid.uuid4())[:8]    # Use part of a UUID for uniqueness
    return f"{timestamp}_{unique_id}"


def get_queue_items(queue_name, limit=10, oldest_first=True):
    """Retrieves items from a specified queue.

    Args:
        queue_name (str): Name of the queue to retrieve items from
        limit (int): Maximum number of items to return
        oldest_first (bool): If True, return oldest items first (FIFO)

    Returns:
        list: Queue items sorted by timestamp
    """
    response = PIPE_QUEUE_TABLE.query(
        KeyConditionExpression=Key('pk').eq(f"QUEUE#{queue_name}") &
                              Key('sk').begins_with('ITEM#'),
        Limit=limit,
        ScanIndexForward=oldest_first  # True = ascending order (oldest first)
    )

    items = []
    for item in response.get('Items', []):
        items.append({
            'id': item['id'],
            'queue_name': queue_name,
            'payload': item.get('payload', {}),
            'created_at': item.get('created_at'),
            'sender': item.get('sender', 'unknown')
        })

    return items


def get_all_queues():
    """Lists all existing queues with their item counts.

    Returns:
        dict: Map of queue names to item counts
    """
    # Use a scan with a filter to find all queue items
    response = PIPE_QUEUE_TABLE.scan(
        FilterExpression=Attr('item_type').eq(QUEUE_ITEM)
    )

    # Count items by queue
    queue_counts = {}
    for item in response.get('Items', []):
        queue_name = item['pk'].split('#')[1]
        if queue_name in queue_counts:
            queue_counts[queue_name] += 1
        else:
            queue_counts[queue_name] = 1

    return queue_counts


def get_pipe_status(pipe_id):
    """Gets the status of a PIPE machine.

    Args:
        pipe_id (str): Identifier for the PIPE machine

    Returns:
        dict: Status information for the PIPE machine or None if not found
    """
    response = PIPE_QUEUE_TABLE.get_item(
        Key={
            'pk': f"STATUS#{pipe_id}",
            'sk': 'INFO'
        }
    )

    item = response.get('Item')
    if not item:
        return None

    return {
        'pipe_id': pipe_id,
        'status': item.get('status', 'unknown'),
        'last_updated': item.get('last_updated'),
        'details': item.get('details', {})
    }


def get_all_pipe_statuses():
    """Gets the status of all PIPE machines.

    Returns:
        list: Status information for all PIPE machines
    """
    response = PIPE_QUEUE_TABLE.scan(
        FilterExpression=Attr('item_type').eq(STATUS_ITEM)
    )

    statuses = []
    for item in response.get('Items', []):
        pipe_id = item['pk'].split('#')[1]
        statuses.append({
            'pipe_id': pipe_id,
            'status': item.get('status', 'unknown'),
            'last_updated': item.get('last_updated'),
            'details': item.get('details', {})
        })

    return statuses


def queue_exists(queue_name):
    """Checks if a queue with the given name exists.

    Args:
        queue_name (str): Name of the queue to check

    Returns:
        bool: True if the queue exists, False otherwise
    """
    # Check if there are any items with this queue name
    response = PIPE_QUEUE_TABLE.query(
        KeyConditionExpression=Key('pk').eq(f"QUEUE#{queue_name}"),
        Limit=1
    )

    return len(response.get('Items', [])) > 0

#############################
######  API Handlers  #######
#############################

def create_queue(event, context):
    """Creates a new queue.

    Args:
        event.body.queue_name (str): Name of the queue to create

    Returns:
        200 status code if successful
        409 status code if the queue already exists
        400 status code if queue_name is missing
    """
    body = _get_body(event)
    queue_name = body.get('queue_name')

    if not queue_name:
        log.error("Missing required field: queue_name")
        return http_response(HTTPStatus.BAD_REQUEST, "Missing required field: queue_name")

    # Check if the queue already exists
    if queue_exists(queue_name):
        log.warning(f"Queue already exists: {queue_name}")
        return http_response(HTTPStatus.CONFLICT, f"Queue already exists: {queue_name}")

    # Create a metadata record for the queue
    PIPE_QUEUE_TABLE.put_item(
        Item={
            'pk': f"QUEUE#{queue_name}",
            'sk': 'METADATA',
            'item_type': QUEUE_ITEM,
            'created_at': int(time.time() * 1000),
            'queue_name': queue_name
        }
    )

    return http_response(HTTPStatus.OK, {"message": f"Queue created: {queue_name}"})


def enqueue_item(event, context):
    """Adds an item to a queue.

    Args:
        event.body.queue_name (str): Name of the queue to add the item to
        event.body.payload (dict): Data to store with the queue item
        event.body.sender (str, optional): Identifier for who sent the item

    Returns:
        200 status code with the created item if successful
        404 status code if the queue doesn't exist
        400 status code if required fields are missing
    """
    body = _get_body(event)
    queue_name = body.get('queue_name')
    payload = body.get('payload', {})
    sender = body.get('sender', 'unknown')

    if not queue_name:
        log.error("Missing required field: queue_name")
        return http_response(HTTPStatus.BAD_REQUEST, "Missing required field: queue_name")

    # Check if the queue exists
    if not queue_exists(queue_name):
        log.warning(f"Queue does not exist: {queue_name}")
        return http_response(HTTPStatus.NOT_FOUND, f"Queue does not exist: {queue_name}")

    # Generate a unique ID for the item
    item_id = generate_queue_item_id()
    created_at = int(time.time() * 1000)

    # Add the item to the queue
    PIPE_QUEUE_TABLE.put_item(
        Item={
            'pk': f"QUEUE#{queue_name}",
            'sk': f"ITEM#{item_id}",
            'id': item_id,
            'item_type': QUEUE_ITEM,
            'payload': payload,
            'created_at': created_at,
            'sender': sender
        }
    )

    item = {
        'id': item_id,
        'queue_name': queue_name,
        'payload': payload,
        'created_at': created_at,
        'sender': sender
    }

    return http_response(HTTPStatus.OK, item)


def peek_queue(event, context):
    """Retrieves items from a queue without removing them.

    Args:
        event.pathParameters.queue_name (str): Name of the queue to retrieve items from
        event.queryStringParameters.limit (int, optional): Maximum number of items to return

    Returns:
        200 status code with queue items if successful
        404 status code if the queue doesn't exist
    """
    queue_name = event['pathParameters']['queue_name']

    # Parse query parameters
    query_params = event.get('queryStringParameters') or {}
    limit = int(query_params.get('limit', 10))

    # Check if the queue exists
    if not queue_exists(queue_name):
        log.warning(f"Queue does not exist: {queue_name}")
        return http_response(HTTPStatus.NOT_FOUND, f"Queue does not exist: {queue_name}")

    # Get items from the queue
    items = get_queue_items(queue_name, limit=limit)

    return http_response(HTTPStatus.OK, items)


def dequeue_item(event, context):
    """Removes and returns the oldest item from a queue.

    Args:
        event.pathParameters.queue_name (str): Name of the queue to dequeue from

    Returns:
        200 status code with the dequeued item if successful
        404 status code if the queue doesn't exist or is empty
    """
    queue_name = event['pathParameters']['queue_name']

    # Check if the queue exists
    if not queue_exists(queue_name):
        log.warning(f"Queue does not exist: {queue_name}")
        return http_response(HTTPStatus.NOT_FOUND, f"Queue does not exist: {queue_name}")

    # Get the oldest item from the queue
    items = get_queue_items(queue_name, limit=1)

    if not items:
        log.warning(f"Queue is empty: {queue_name}")
        return http_response(HTTPStatus.NOT_FOUND, f"Queue is empty: {queue_name}")

    # Remove the item from the queue
    item = items[0]
    PIPE_QUEUE_TABLE.delete_item(
        Key={
            'pk': f"QUEUE#{queue_name}",
            'sk': f"ITEM#{item['id']}"
        }
    )

    return http_response(HTTPStatus.OK, item)


def delete_queue(event, context):
    """Deletes a queue and all its items.

    Args:
        event.pathParameters.queue_name (str): Name of the queue to delete

    Returns:
        200 status code if successful
        404 status code if the queue doesn't exist
    """
    queue_name = event['pathParameters']['queue_name']

    # Check if the queue exists
    if not queue_exists(queue_name):
        log.warning(f"Queue does not exist: {queue_name}")
        return http_response(HTTPStatus.NOT_FOUND, f"Queue does not exist: {queue_name}")

    # Get all items in the queue
    response = PIPE_QUEUE_TABLE.query(
        KeyConditionExpression=Key('pk').eq(f"QUEUE#{queue_name}")
    )

    # Delete each item
    with PIPE_QUEUE_TABLE.batch_writer() as batch:
        for item in response.get('Items', []):
            batch.delete_item(
                Key={
                    'pk': item['pk'],
                    'sk': item['sk']
                }
            )

    return http_response(HTTPStatus.OK, {"message": f"Queue deleted: {queue_name}"})


def list_queues(event, context):
    """Lists all existing queues with their item counts.

    Returns:
        200 status code with a map of queue names to item counts
    """
    queue_counts = get_all_queues()
    return http_response(HTTPStatus.OK, queue_counts)


def set_pipe_status(event, context):
    """Sets the status of a PIPE machine.

    Args:
        event.body.pipe_id (str): Identifier for the PIPE machine
        event.body.status (str): Status to set (e.g., "online", "offline")
        event.body.details (dict, optional): Additional details about the status

    Returns:
        200 status code if successful
        400 status code if required fields are missing
    """
    body = _get_body(event)
    pipe_id = body.get('pipe_id')
    status = body.get('status')
    details = body.get('details', {})

    if not pipe_id or not status:
        log.error("Missing required fields: pipe_id and status")
        return http_response(
            HTTPStatus.BAD_REQUEST,
            "Missing required fields: pipe_id and status"
        )

    last_updated = int(time.time() * 1000)

    # Update the status
    PIPE_QUEUE_TABLE.put_item(
        Item={
            'pk': f"STATUS#{pipe_id}",
            'sk': 'INFO',
            'item_type': STATUS_ITEM,
            'status': status,
            'last_updated': last_updated,
            'details': details
        }
    )

    status_info = {
        'pipe_id': pipe_id,
        'status': status,
        'last_updated': last_updated,
        'details': details
    }

    return http_response(HTTPStatus.OK, status_info)


def get_pipe_status_handler(event, context):
    """Gets the status of a PIPE machine.

    Args:
        event.pathParameters.pipe_id (str): Identifier for the PIPE machine

    Returns:
        200 status code with status information if successful
        404 status code if the PIPE machine is not found
    """
    pipe_id = event['pathParameters']['pipe_id']

    status = get_pipe_status(pipe_id)

    if not status:
        log.warning(f"PIPE machine not found: {pipe_id}")
        return http_response(HTTPStatus.NOT_FOUND, f"PIPE machine not found: {pipe_id}")

    return http_response(HTTPStatus.OK, status)


def get_all_pipe_statuses_handler(event, context):
    """Gets the status of all PIPE machines.

    Returns:
        200 status code with status information for all PIPE machines
    """
    statuses = get_all_pipe_statuses()
    return http_response(HTTPStatus.OK, statuses)
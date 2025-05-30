# api/db.py (modified query functions to work with DynamoDB)

import logging
import json
import time
import boto3
from datetime import datetime
from http import HTTPStatus
from boto3.dynamodb.conditions import Key, Attr
import os
from decimal import Decimal

from api.helpers import get_s3_file_url, http_response, DecimalEncoder

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3 = boto3.client('s3', region_name=os.environ['REGION'])

# Get DynamoDB table references
images_table = dynamodb.Table(os.environ['IMAGES_TABLE'])
info_images_table = dynamodb.Table(os.environ['INFO_IMAGES_TABLE'])

# Constants
BUCKET_NAME = os.environ['BUCKET_NAME']

def format_image_response(item):
    """Formats a DynamoDB item as an image response."""
    # Convert DynamoDB format to standard Python types
    image = json.loads(json.dumps(item, cls=DecimalEncoder))

    # Format the response
    response = {
        "base_filename": image.get('base_filename'),
        "site": image.get('site'),
        "capture_date": image.get('capture_date'),
        "username": image.get('username'),
        "user_id": image.get('user_id'),
        "header_data": image.get('header_data', {})
    }

    # Add URLs for JPG and thumbnail if available
    jpg_key = image.get('jpg_key')
    if jpg_key:
        response["jpg_url"] = get_s3_file_url(jpg_key)

    thumbnail_key = image.get('thumbnail_key')
    if thumbnail_key:
        response["jpg_thumbnail_url"] = get_s3_file_url(thumbnail_key)

    return response

def get_latest_site_images(site, number_of_images, user_id=None):
    """Gets the n latest images from a site.

    Args:
        site (str): 3-letter site code.
        number_of_images (int): Number of images to return.
        user_id (str, optional): Filter to only images by this user.

    Returns:
        list[dict]: List of dicts, each representing one image with metadata.
    """
    try:
        if user_id:
            # Query using the UserIdIndex if filtering by user
            response = images_table.query(
                IndexName='UserIdIndex',
                KeyConditionExpression=Key('user_id').eq(user_id),
                FilterExpression=Attr('site').eq(site) & Attr('processed').eq(True),
                ScanIndexForward=False,  # Sort descending by sort_date
                Limit=number_of_images
            )
        else:
            # Query using the primary index
            response = images_table.query(
                KeyConditionExpression=Key('site').eq(site),
                FilterExpression=Attr('processed').eq(True),
                ScanIndexForward=False,  # Sort descending by sort_date
                Limit=number_of_images
            )

        # Format the response
        images = [format_image_response(item) for item in response.get('Items', [])]
        return images

    except Exception as e:
        logger.error(f"Error getting latest site images: {str(e)}")
        return []

def get_latest_image_all_sites():
    """Gets the latest images at all sites."""
    try:
        # Get all site codes (this could be cached or stored in a config)
        sites = get_all_sites()

        results = {}
        for site in sites:
            # Query for the latest image at this site
            response = images_table.query(
                KeyConditionExpression=Key('site').eq(site),
                FilterExpression=Attr('processed').eq(True),
                ScanIndexForward=False,  # Sort descending by sort_date
                Limit=1
            )

            items = response.get('Items', [])
            if items:
                # Get the JPG URL for the latest image
                jpg_key = items[0].get('jpg_key')
                if jpg_key:
                    results[site] = get_s3_file_url(jpg_key)

        return results

    except Exception as e:
        logger.error(f"Error getting latest image all sites: {str(e)}")
        return {}

def get_all_sites():
    """Gets all available site codes."""
    try:
        # Scan the images table to find all unique site values
        response = images_table.scan(
            ProjectionExpression='site',
            Select='SPECIFIC_ATTRIBUTES'
        )

        # Extract unique site codes
        sites = set()
        for item in response.get('Items', []):
            sites.add(item.get('site'))

        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = images_table.scan(
                ProjectionExpression='site',
                Select='SPECIFIC_ATTRIBUTES',
                ExclusiveStartKey=response['LastEvaluatedKey']
            )

            for item in response.get('Items', []):
                sites.add(item.get('site'))

        return list(sites)

    except Exception as e:
        logger.error(f"Error getting all sites: {str(e)}")
        return []

def get_image_by_filename(base_filename):
    """Gets the image package for the image specified by the filename.

    Args:
        base_filename (str): The base filename without extensions.

    Returns:
        dict: The image package representing the image with metadata.
    """
    try:
        # Query using the BaseFilenameIndex
        response = images_table.query(
            IndexName='BaseFilenameIndex',
            KeyConditionExpression=Key('base_filename').eq(base_filename),
            FilterExpression=Attr('processed').eq(True)
        )

        items = response.get('Items', [])
        if not items:
            raise ValueError(f"No results found for {base_filename}")

        if len(items) > 1:
            raise ValueError(f"Multiple images found for {base_filename}")

        # Format and return the response
        return format_image_response(items[0])

    except Exception as e:
        logger.error(f"Error getting image by filename: {str(e)}")
        raise

def remove_image_by_filename(base_filename):
    """Removes an image from DynamoDB by its base filename.

    Args:
        base_filename (str): Identifies what to delete.
    """
    try:
        # Query to find the item first
        response = images_table.query(
            IndexName='BaseFilenameIndex',
            KeyConditionExpression=Key('base_filename').eq(base_filename)
        )

        items = response.get('Items', [])
        if not items:
            logger.warning(f"No image found to delete with base_filename {base_filename}")
            return

        # Delete each found item
        for item in items:
            site = item.get('site')
            sort_date = item.get('sort_date')

            images_table.delete_item(
                Key={
                    'site': site,
                    'sort_date': sort_date
                }
            )

        logger.info(f"Deleted {len(items)} items with base_filename {base_filename}")

    except Exception as e:
        logger.error(f"Error removing image by filename: {str(e)}")
        raise

def filtered_images_query(query_filters):
    """Gets images that satisfy the specified filters.

    Args:
        query_filters (dict): Filter criteria to apply.

    Returns:
        list[dict]: List of dicts, each representing an image with metadata.
    """
    try:
        # Start with a base filter expression that requires processed=True
        filter_expr = Attr('processed').eq(True)

        # Add site filter if specified
        site = query_filters.get('site')
        if site:
            # If site is specified, we can use a query instead of a scan
            key_condition = Key('site').eq(site)
            use_query = True
        else:
            key_condition = None
            use_query = False

        # Add user_id filter if specified
        user_id = query_filters.get('user_id')
        if user_id:
            filter_expr = filter_expr & Attr('user_id').eq(user_id)
            # If we have a user_id but no site, we can query on the UserIdIndex
            if not use_query:
                key_condition = Key('user_id').eq(user_id)
                use_query = True
                index_name = 'UserIdIndex'

        # Add filter_used filter if specified
        filter_used = query_filters.get('filter')
        if filter_used:
            filter_expr = filter_expr & Attr('header_data.FILTER').eq(filter_used)

        # Add exposure_time filters if specified
        exposure_time_min = query_filters.get('exposure_time_min')
        if exposure_time_min:
            filter_expr = filter_expr & Attr('header_data.EXPTIME').gte(float(exposure_time_min))

        exposure_time_max = query_filters.get('exposure_time_max')
        if exposure_time_max:
            filter_expr = filter_expr & Attr('header_data.EXPTIME').lte(float(exposure_time_max))

        # Add date filters if specified
        start_date = query_filters.get('start_date')
        if start_date:
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d+%H').timestamp() * 1000)
            filter_expr = filter_expr & Attr('capture_date').gte(start_timestamp)

        end_date = query_filters.get('end_date')
        if end_date:
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d+%H').timestamp() * 1000)
            filter_expr = filter_expr & Attr('capture_date').lte(end_timestamp)

        # Add filename filter if specified
        filename = query_filters.get('filename')
        if filename:
            filter_expr = filter_expr & Attr('base_filename').contains(filename)

        # Execute the query or scan
        if use_query:
            if site:
                # Query on the primary index with site
                response = images_table.query(
                    KeyConditionExpression=key_condition,
                    FilterExpression=filter_expr,
                    ScanIndexForward=False  # Sort descending by sort_date
                )
            else:
                # Query on the UserIdIndex
                response = images_table.query(
                    IndexName='UserIdIndex',
                    KeyConditionExpression=key_condition,
                    FilterExpression=filter_expr,
                    ScanIndexForward=False  # Sort descending by sort_date
                )
        else:
            # Fall back to a scan with filter expression
            response = images_table.scan(
                FilterExpression=filter_expr
            )

        # Format the response
        images = [format_image_response(item) for item in response.get('Items', [])]

        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            if use_query:
                if site:
                    response = images_table.query(
                        KeyConditionExpression=key_condition,
                        FilterExpression=filter_expr,
                        ScanIndexForward=False,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
                else:
                    response = images_table.query(
                        IndexName='UserIdIndex',
                        KeyConditionExpression=key_condition,
                        FilterExpression=filter_expr,
                        ScanIndexForward=False,
                        ExclusiveStartKey=response['LastEvaluatedKey']
                    )
            else:
                response = images_table.scan(
                    FilterExpression=filter_expr,
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )

            images.extend([format_image_response(item) for item in response.get('Items', [])])

        return images

    except Exception as e:
        logger.error(f"Error in filtered images query: {str(e)}")
        raise


def get_fits_header_from_db(base_filename):
    """Returns the header data for the given base filename.

    Args:
        base_filename (str): The filename (without the extension)
                            for identifying the header we want.

    Returns:
        dict: The header data as a dictionary.

    Raises:
        ValueError: If no header found for the given base_filename.
    """
    try:
        # Query using the BaseFilenameIndex
        response = images_table.query(
            IndexName='BaseFilenameIndex',
            KeyConditionExpression=Key('base_filename').eq(base_filename),
            ProjectionExpression='header_data'  # Only retrieve the header_data attribute
        )

        items = response.get('Items', [])
        if not items:
            raise ValueError(f"No header found for {base_filename}")

        # Return the header_data
        header_data = items[0].get('header_data', {})

        # Convert from DynamoDB format if needed
        if header_data:
            header_data = json.loads(json.dumps(header_data, cls=DecimalEncoder))

        return header_data

    except Exception as e:
        logger.error(f"Error getting header for {base_filename}: {str(e)}")
        raise

# Handler functions for API Gateway

def get_latest_site_images_handler(event, context):
    """Handler for getting the latest images at a site."""
    # Parse the arguments passed in the http request
    site = event['pathParameters']['site']
    number_of_images = int(event['pathParameters']['number_of_images'])

    # Check for user_id filter
    query_params = event['queryStringParameters']
    user_id = None
    if query_params and "userid" in query_params:
        user_id = query_params["userid"]

    # Get the images
    images = get_latest_site_images(site, number_of_images, user_id)
    return http_response(HTTPStatus.OK, images)

def get_latest_images_all_sites_handler(event, context):
    """Handler for getting the latest images at all sites."""
    images = get_latest_image_all_sites()
    return http_response(HTTPStatus.OK, images)

def get_image_by_filename_handler(event, context):
    """Handler for retrieving an image given the base filename."""
    base_filename = event['pathParameters']['base_filename']

    try:
        image = get_image_by_filename(base_filename)
        return http_response(HTTPStatus.OK, image)

    except ValueError as e:
        error_msg = str(e)
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

    except Exception as e:
        error_msg = f"Error retrieving image: {str(e)}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.INTERNAL_SERVER_ERROR, error_msg)

def remove_image_by_filename_handler(event, context):
    """Handler for removing an image given the base filename."""
    base_filename = event['pathParameters']['base_filename']

    try:
        remove_image_by_filename(base_filename)
        return http_response(HTTPStatus.OK, f'Successfully removed {base_filename}')

    except Exception as e:
        error_msg = f"Could not delete {base_filename}. Error: {str(e)}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

def filtered_images_query_handler(event, context):
    """Handler for querying images based on specified filters."""
    filter_params = event['queryStringParameters'] or {}

    try:
        images = filtered_images_query(filter_params)
        return http_response(HTTPStatus.OK, images)

    except ValueError as e:
        error_msg = f"Invalid query filter: {str(e)}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.BAD_REQUEST, error_msg)

    except Exception as e:
        error_msg = f"Error in filter images query: {str(e)}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

def get_fits_header_from_db_handler(event, context):
    """Handler for retrieving the header from a specified file.

    Args:
        event.pathParameters.base_filename:
            The filename (without the extension)
            for identifying the header we want.

    Returns:
        200 status code with header info if successful.
        404 status code if no header found with given base_filename.
    """
    base_filename = event['pathParameters']['base_filename']

    try:
        header = get_fits_header_from_db(base_filename)
        return http_response(HTTPStatus.OK, header)

    except ValueError as e:
        error_msg = f"No header found in the database for {base_filename}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

    except Exception as e:
        error_msg = f"Error retrieving header: {str(e)}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.INTERNAL_SERVER_ERROR, error_msg)

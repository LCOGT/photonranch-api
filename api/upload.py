# api/handler.py (modified upload function)
import json
import os
import boto3
import time
from http import HTTPStatus
from datetime import datetime

from api.helpers import BUCKET_NAME, REGION, S3_PUT_TTL, get_base_filename_from_full_filename, http_response, _get_body, DecimalEncoder

# Initialize AWS clients
s3 = boto3.client('s3', REGION)
dynamodb = boto3.resource('dynamodb', REGION)

# Get DynamoDB table references
images_table = dynamodb.Table(os.environ['IMAGES_TABLE'])
info_images_table = dynamodb.Table(os.environ['INFO_IMAGES_TABLE'])

def upload(event, context):
    """Generates a presigned URL to upload files at AWS.

    This modified version now also stores image metadata in DynamoDB
    when the upload URL is requested, rather than waiting for the
    file to arrive in S3.

    Args:
        event.body.s3_directory (str): Name of the s3 bucket to use.
        event.body.object_name (str): Name of the file to upload.
        event.body.header_data (dict, optional): Metadata for the image.
        event.body.info_channel (int, optional): Channel for info images.

    Returns:
        200 status code with presigned upload URL if successful.
        403 status code if incorrect s3 bucket or info channel supplied.
    """

    # Parse the request body
    body = _get_body(event)

    # Retrieve and validate the s3_directory
    s3_directory = body.get('s3_directory', 'data')
    filename = body.get('object_name')

    if s3_directory not in ['data', 'info-images', 'allsky', 'test']:
        error_msg = "s3_directory must be either 'data', 'info-images', or 'allsky'."
        return http_response(HTTPStatus.FORBIDDEN, error_msg)

    # Handle info images
    if s3_directory == 'info-images':
        site = filename.split('-')[0]
        base_filename = get_base_filename_from_full_filename(filename)
        channel = int(body.get('info_channel', 1))

        if channel not in [1, 2, 3]:
            error_msg = f"Value for info_channel must be either 1, 2, or 3. Received {channel} instead."
            return http_response(HTTPStatus.FORBIDDEN, error_msg)

        # Create an entry to track metadata for the next info image
        info_images_table.update_item(
            Key={'pk': f'{site}#metadata'},
            UpdateExpression=f"set channel{channel}=:basefilename",
            ExpressionAttributeValues={':basefilename': base_filename}
        )

    # Handle regular images
    elif s3_directory == 'data' and filename.lower().endswith('.jpg'):
        base_filename = get_base_filename_from_full_filename(filename)
        site = base_filename.split('-')[0]

        # Get header metadata from the request
        header_data = body.get('header_data', {})

        # Convert strings to appropriate types if needed
        header_data = sanitize_header_data(header_data)

        # Get the capture timestamp from the header data
        capture_date = get_capture_timestamp(header_data)

        # Store the metadata in DynamoDB
        try:
            images_table.put_item(
                Item={
                    'site': site,
                    'sort_date': capture_date,
                    'base_filename': base_filename,
                    'capture_date': capture_date,
                    'username': header_data.get('USERNAME', ''),
                    'user_id': header_data.get('USERID', ''),
                    'header_data': header_data,
                    'processed': False,
                    'last_updated': int(time.time() * 1000)
                }
            )
        except Exception as e:
            print(f"Error storing metadata in DynamoDB: {str(e)}")
            # Continue anyway to provide the upload URL

    # Generate the presigned upload URL
    key = f"{s3_directory}/{filename}"
    url = s3.generate_presigned_post(
        Bucket=BUCKET_NAME,
        Key=key,
        ExpiresIn=S3_PUT_TTL
    )

    return http_response(HTTPStatus.OK, url)

def sanitize_header_data(header_data):
    """Sanitizes header data to ensure correct types."""
    sanitized = {}

    for key, value in header_data.items():
        # Try to convert numeric values to the appropriate type
        if isinstance(value, str):
            value = value.strip()

            # Remove quotes from string values
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            # Try to convert numeric values
            try:
                if '.' in value:
                    # Try float conversion
                    sanitized[key] = float(value)
                else:
                    # Try integer conversion
                    sanitized[key] = int(value)
            except (ValueError, TypeError):
                # Keep as string if conversion fails
                sanitized[key] = value
        else:
            # Keep non-string values as is
            sanitized[key] = value

    return sanitized

def get_capture_timestamp(header_data):
    """Extracts the capture timestamp from header data."""
    try:
        date_obs = header_data.get('DATE-OBS')
        if date_obs:
            # Replace 'T' with space if present
            date_obs = date_obs.replace('T', ' ')

            # Try parsing with fractional seconds first
            try:
                # Handle fractional seconds (microseconds)
                dt = datetime.strptime(date_obs, '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                # Fallback to format without fractional seconds
                dt = datetime.strptime(date_obs, '%Y-%m-%d %H:%M:%S')

            # Convert to milliseconds
            return int(dt.timestamp() * 1000)
    except Exception as e:
        print(f"Error parsing DATE-OBS: {str(e)}")
        # Return current time as fallback
        return int(time.time() * 1000)
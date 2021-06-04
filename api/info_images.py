import json
import boto3
import os
from http import HTTPStatus

from api.helpers import _get_secret, http_response, get_s3_file_url


ddb = boto3.resource('dynamodb', os.getenv('REGION'))
info_images_table = ddb.Table(os.getenv('INFO_IMAGES_TABLE'))

def get_info_image_package(event, context):
    site = event['pathParameters']['site']
    channel = event['pathParameters']['channel']
    info_image_query = info_images_table.get_item(Key={
        "pk": f"{site}#{channel}"
    })
    try:
        info_image = info_image_query['Item']

        info_image_package = {
            **info_image, 
            "site": site,
            "channel": channel,
            "base_filename": info_image["base_filename"],
            #TODO: check for file existence by checking if the file path exists. Then remove the explicit existance keys from info-images database.
            "jpg_medium_exists": info_image.get("jpg_medium_exists", False),
            "jpg_small_exists": info_image.get("jpg_small_exists", False),
            "fits_01_exists": info_image.get("fits_01_exists", False),
            "fits_10_exists": info_image.get("fits_10_exists", False),
            "s3_directory": "info-images",
        }

        if info_image_package["jpg_medium_exists"]:
            jpg_medium_url = get_s3_file_url(info_image["jpg_10_file_path"])
            info_image_package["jpg_url"] = jpg_medium_url
        if info_image_package["jpg_small_exists"]:
            jpg_small_url = get_s3_file_url(info_image["jpg_11_file_path"])
            info_image_package["jpg_small_url"] = jpg_small_url
        if info_image_package["fits_01_exists"]:
            fits_01_url = get_s3_file_url(info_image["fits_01_file_path"])
            info_image_package["fits_01_url"] = fits_01_url
        if info_image_package["fits_10_exists"]:
            fits_10_url = get_s3_file_url(info_image["fits_10_file_path"])
            info_image_package["fits_10_url"] = fits_10_url

        print(info_image_package)
        return http_response(HTTPStatus.OK, info_image_package)
    except KeyError:
        return http_response(HTTPStatus.NOT_FOUND, f'No info image for site {site}.')

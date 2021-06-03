
import pytest, json
from http import HTTPStatus

from api.handler import info_images_table
from api.handler import upload 

from api.helpers import get_base_filename_from_full_filename


##### TEST HELPERS #####
def get_info_image_site_metadata(site):
    response = info_images_table.get_item(
        Key={ 'pk': f'{site}#metadata' }
    )
    print(response)
    return response


def test_upload_data():
    object_name = 'object_from_unit_test.txt'
    s3_directory = 'data'
    event = {
        "body": json.dumps({
            "object_name": object_name,
            "s3_directory": s3_directory,
        })
    }
    response = upload(event, {})
    response_body = json.loads(response['body'])
    print(response)
    print(response_body)
    assert(response['statusCode']==HTTPStatus.OK)
    assert("url" in response_body.keys())
    assert(response_body['fields']['key'] == f"{s3_directory}/{object_name}")


def test_upload_bad_s3_directory():
    object_name = 'object_from_unit_test.txt'
    s3_directory = 'not_a_valid_s3_dir'
    event = {
        "body": json.dumps({
            "object_name": object_name,
            "s3_directory": s3_directory,
        })
    }
    response = upload(event, {})
    assert(response['statusCode']==HTTPStatus.FORBIDDEN)


def test_upload_info_image_bad_channel():
    object_name = 'tst-inst-20201231-00000001-EX00.txt'
    s3_directory = 'info-images'
    event = {
        "body": json.dumps({
            "object_name": object_name,
            "s3_directory": s3_directory,
            "info_channel": 4
        })
    }
    response = upload(event, {})
    print(response)
    assert(response['statusCode']==HTTPStatus.FORBIDDEN)


def test_upload_info_image_no_channel():
    object_name = 'tst-inst-20201231-00000002-EX00.txt'
    base_filename = get_base_filename_from_full_filename(object_name)
    site = object_name.split('-')[0]
    s3_directory = 'info-images'
    event = {
        "body": json.dumps({
            "object_name": object_name,
            "s3_directory": s3_directory,
        })
    }
    response = upload(event, {})
    print(response)
    ddb_entry = get_info_image_site_metadata(site)
    print(ddb_entry)
    assert('Item' in ddb_entry.keys())
    assert(ddb_entry['Item']['channel1'] == base_filename)  # default channel should be 1
    assert(response['statusCode']==HTTPStatus.OK)


def test_upload_info_image_good():
    object_name = 'tst-inst-20201231-00000003-EX00.txt'
    base_filename = get_base_filename_from_full_filename(object_name)
    site = object_name.split('-')[0]
    s3_directory = 'info-images'
    info_channel = 2
    event = {
        "body": json.dumps({
            "object_name": object_name,
            "s3_directory": s3_directory,
            "info_channel": info_channel
        })
    }
    response = upload(event, {})
    print(response)
    ddb_entry = get_info_image_site_metadata(site)
    print(ddb_entry)
    assert('Item' in ddb_entry.keys())
    assert(ddb_entry['Item'][f'channel{info_channel}'] == base_filename)
    assert(response['statusCode']==HTTPStatus.OK)

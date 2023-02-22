import pytest
import json
from http import HTTPStatus

from api.helpers import get_base_filename_from_full_filename

from api.info_images import get_info_image_package
from api.info_images import info_images_table


##### Helper Methods #####
def create_info_image_entry(site, channel, base_filename, data_type, header=None, 
        include_fits_01=False, include_fits_10=False, include_jpg_10=False, 
        include_jpg_11=False, include_txt_00=False):

    optional_attributes = {}
    if include_fits_01: 
        optional_attributes['fits_01_exists'] = True
        optional_attributes['fits_01_file_path'] = f"info-images/{base_filename}-{data_type}00.fits.fz"
    if include_fits_10: 
        optional_attributes['fits_10_exists'] = True
        optional_attributes['fits_10_file_path'] = f"info-images/{base_filename}-{data_type}10.fits.fz"
    if include_jpg_10: 
        optional_attributes['jpg_10_exists'] = True
        optional_attributes['jpg_10_path'] = f"info-images/{base_filename}-{data_type}10.jpg"
    if include_jpg_11:
        optional_attributes['jpg_11_exists'] = True
        optional_attributes['jpg_11_path'] = f"info-images/{base_filename}-{data_type}11.jpg"
    if type(header) is dict:
        optional_attributes['header'] = header

    info_images_table.put_item(
        Item={
            'pk': f"{site}#{channel}",
            'base_filename': base_filename,
            'file_date': base_filename.split('-')[2],
            'data_type': data_type,
            **optional_attributes
        }
    )


def remove_info_image_entry(pk):
    """ Remove the entry specified by the pk from the dynamodb info-images table """
    info_images_table.delete_item(Key={'pk': pk})


def build_request_event(site, channel):
    """ Build a dict that resembles the 'event' passed from api gateway to the lambda handler """
    event = {
        'pathParameters': {
            'site': site,
            'channel': channel
        }
    }
    return event


@pytest.fixture 
def setup_teardown():
    pk = 'testdata#1'
    remove_info_image_entry(pk)
    yield
    remove_info_image_entry(pk)


##### Tests #####
def test_get_info_image_package_success(setup_teardown):

    # add test data to the info-images dynamodb table
    site = 'testdata'
    channel = 1
    base_filename = 'tst-inst-20201122-01234567'
    data_type = 'EX'
    header = {'HEADKEY': 'header val'}
    create_info_image_entry(site, channel, base_filename, data_type, header, True, False)

    # simulate a request to get the info image that we sent above
    event = build_request_event(site, channel)

    # run the method we want to test
    response = get_info_image_package(event, {})
    response_body = json.loads(response['body'])
    print(response_body.keys())
    print(response_body)

    assert(response['statusCode'] == HTTPStatus.OK)
    assert(response_body['base_filename'] == base_filename)
    assert(response_body['fits_01_exists'] == True)
    assert(response_body['fits_10_exists'] == False)
    assert(response_body['site'] == site)
    assert(response_body['channel'] == channel)


def test_get_info_image_package_no_image(setup_teardown):

    # don't add test data to the info-images dynamodb table
    site = 'testdata'
    channel = 1

    # simulate a request to get the info image that we sent above
    event = build_request_event(site, channel)

    # run the method we want to test
    response = get_info_image_package(event, {})

    assert(response['statusCode'] == HTTPStatus.NO_CONTENT)


def test_get_info_image_package_check_file_urls(setup_teardown):

    # don't add test data to the info-images dynamodb table
    site = 'testdata'
    channel = 1
    base_filename = 'tst-inst-20201122-01234567'
    data_type = 'EX'
    header = {'HEADKEY': 'header val'}
    # include the fits_10 as the only file
    create_info_image_entry(site, channel, base_filename, data_type, header, False, True)

    # simulate a request to get the info image that we sent above
    event = build_request_event(site, channel)

    # run the method we want to test
    response = get_info_image_package(event, {})
    response_body = json.loads(response['body'])

    assert(response['statusCode'] == HTTPStatus.OK)
    assert(response_body['fits_10_exists'] == True)
    assert('fits_10_url' in response_body.keys())

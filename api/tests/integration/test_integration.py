import requests
import json
import pytest
import os
from urllib.parse import urlencode
from http import HTTPStatus

# These env vars are normally configured from serverless.yml.
# Create them here manually for tests. Required in api/helpers.py.
os.environ['S3_BUCKET_NAME'] = 'photonranch-001'
os.environ['REGION'] = 'us-east-1'

from api import handler

VALID_FILTER_REQUEST_EVENT = {
    "queryStringParameters": {
        "site": "mrc",
        "filter": "up",
        "start_date": "2020-08-30+12",
        "filename": "-"
    }
}
INVALID_FILTER_REQUEST_EVENT = {
    "queryStringParameters": {
        "bad filter key": "bad filter value",
    }
}


@pytest.fixture
def base_url():
    return "https://api.photonranch.org/test"


@pytest.mark.skip(reason="Haven't added a way to add auth in tests.")
def test_dummy_requires_auth(base_url):
    url = f"{base_url}/ping/hello"
    response = requests.post(url)
    assert response.status_code == HTTPStatus.OK


def test_home(base_url):
    url = f"{base_url}/"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.skip(reason="Not built yet.")
def test_upload(base_url):
    assert False


@pytest.mark.skip(reason="Not built yet.")
def test_download(base_url):
    assert False


def test_get_image_by_filename(base_url):
    base_filename = "saf-sq01-20200830-00001258"
    url = f"{base_url}/image/{base_filename}/"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


def test_get_image_invalid_filename(base_url):
    base_filename = "invalid_filename"
    url = f"{base_url}/image/{base_filename}/"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.NOT_FOUND


def test_latest_images_no_user(base_url):
    site = "mrc"
    url = f"{base_url}/{site}/latest_images/1"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


def test_latest_images_fake_user(base_url):
    site = "mrc"
    query_params = {
        "userid": "fake user id"
    }
    url = f"{base_url}/{site}/latest_images/1"
    response = requests.get(url, params=query_params)
    assert response.status_code == HTTPStatus.OK


def test_filtered_image_query(base_url):
    url = f"{base_url}/filtered_images"
    params = {
        "site": "mrc",
        "filter": "up",
        "start_date": "2020-08-30+12",
    }
    response = requests.get(url, params=params)
    assert response.status_code == HTTPStatus.OK


def test_get_fits_header_from_db(base_url):
    base_filename = "saf-sq01-20200830-00001258"
    url = f"{base_url}/fitsheader/{base_filename}"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


def test_get_config(base_url):
    site = "mrc"
    url = f"{base_url}/{site}/config"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.skip(reason="Not built yet.")
def test_put_config(base_url):
    site = "test-site"
    url = f"{base_url}/{site}/config"
    response = requests.put(url)
    assert False


@pytest.mark.skip(reason="Not built yet.")
def test_delete_config(base_url):
    """Warning: do not test on an actual site. Config will be deleted."""
    site = "test-site"
    url = f"{base_url}/{site}/config"
    response = requests.delete(url)
    assert False


def test_all_config(base_url):
    url = f"{base_url}/all/config"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.skip(reason="Not built yet.")
def test_example_query(base_url):
    url = f"{base_url}/example-query"
    response = requests.post(url)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.skip(reason="Not built yet.")
def test_weather_graph_query(base_url):
    url = f"{base_url}/weather/graph-data"
    response = requests.post(url)
    assert False


@pytest.mark.skip(reason="Not built yet.")
def test_add_weather_status(base_url):
    url = f"{base_url}/weather/write"
    response = requests.post(url)
    assert False


def test_site_events(base_url):
    site = "mrc"
    url = f"{base_url}/events?site={site}"
    response = requests.get(url)
    assert response.status_code == HTTPStatus.OK

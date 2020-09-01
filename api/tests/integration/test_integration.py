import requests
import json
import pytest
import os

# These env vars are normally configured from serverless.yml.
# Create them here manually for tests. Required in api/helpers.py.
os.environ['S3_BUCKET_NAME'] = 'photonranch-001'
os.environ['REGION'] = 'us-east-1'

from api import handler


@pytest.fixture
def base_url():
    return "https://api.photonranch.org/test"

# need auth
#def test_ping(base_url):
    #url = f"{base_url}/ping/hello"
    #response = requests.post(url)
    #assert response.status_code == 200

def test_home(base_url):
    url = f"{base_url}/"
    response = requests.get(url)
    assert response.status_code == 200


#def test_upload(base_url):
    #assert False

#def test_download(base_url):
    #assert False

def test_latest_images(base_url):
    site = "wmd"
    url = f"{base_url}/{site}/latest_images/1"
    response = requests.get(url)
    assert response.status_code == 200

def test_get_config(base_url):
    site = "wmd"
    url = f"{base_url}/{site}/config"
    response = requests.get(url)
    assert response.status_code == 200

#def test_put_config(base_url):
    #site = "test-site"
    #url = f"{base_url}/{site}/config"
    #response = requests.put(url)
    #assert False

#def test_delete_config(base_url):
    #"""Warning: do not test on an actual site. Config will be deleted."
    #site = "test-site"
    #url = f"{base_url}/{site}/config"
    #response = requests.delete(url)
    #assert False

def test_all_config(base_url):
    url = f"{base_url}/all/config"
    response = requests.get(url)
    assert response.status_code == 200

def test_get_fits_header(base_url):
    base_filename = "saf-sq01-20200830-00001258"
    url = f"{base_url}/fitsheader/{base_filename}"
    response = requests.get(url)
    assert response.status_code == 200

#def test_filtered_image_query(base_url):
    #url = f"{base_url}/filtered_images"
    #response = requests.get(url)
    #assert False

#def test_example_query(base_url):
    #url = f"{base_url}/example-query"
    #response = requests.post(url)
    #assert response.status_code == 200

#def test_weather_graph_query(base_url):
    #url = f"{base_url}/weather/graph-data"
    #response = requests.post(url)
    #assert False

#def test_add_weather_status(base_url):
    #url = f"{base_url}/weather/write"
    #response = requests.post(url)
    #assert False

def test_site_events(base_url):
    site = "wmd"
    url = f"{base_url}/events?site={site}"
    response = requests.get(url)
    assert response.status_code == 200

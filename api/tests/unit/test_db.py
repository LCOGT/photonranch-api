import pytest
import os
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.exc import ArgumentError

# These env vars are normally configured from serverless.yml.
# Create them here manually for tests. Required in api/helpers.py.
os.environ['S3_BUCKET_NAME'] = 'photonranch-001'
os.environ['REGION'] = 'us-east-1'

from api import db
from api.db import Image
from api.helpers import _get_secret

VALID_USER_ID = "google-oauth2|100354044221813550027"
INVALID_USER_ID = "invalid-user-id"

VALID_BASE_FILENAME = "tst-test-20200922-00000039"
INVALID_BASE_FILENAME = "invalid-base-filename"

VALID_QUERY_FILTERS = [
    Image.username == "Tim Beccue",
    Image.site == "wmd",
    Image.filter_used == "air",
    Image.exposure_time >= "0.1",
    Image.exposure_time <= "60",
    Image.capture_date >= "2010-08-30+12",
    Image.capture_date <= "2030-08-30+12",
]
INVALID_QUERY_FILTERS = [
    "invalid query filter",
]


@pytest.fixture 
def db_address():
    return _get_secret('db-url')


def test_get_latest_site_images(db_address):
    site = "wmd"
    number_of_images = 5
    images = db.get_latest_site_images(db_address, site, number_of_images)
    assert len(images) == 5


def test_get_latest_site_images_includes_valid_user(db_address):
    site = "wmd"
    number_of_images = 1
    images = db.get_latest_site_images(db_address, site, number_of_images, 
            user_id=VALID_USER_ID)
    assert images[0]["user_id"] == VALID_USER_ID


def test_get_latest_site_images_includes_invalid_user(db_address):
    site = "wmd"
    number_of_images = 1
    images = db.get_latest_site_images(db_address, site, number_of_images, 
            user_id=INVALID_USER_ID)
    assert len(images) == 0


def test_get_fits_header_from_db_valid_input(db_address):
    header = db.get_fits_header_from_db(db_address, VALID_BASE_FILENAME)
    assert "EXPTIME" in header.keys()


def test_get_fits_header_from_db_invalid_input(db_address):
    with pytest.raises(NoResultFound):
        header = db.get_fits_header_from_db(db_address, INVALID_BASE_FILENAME)


def test_filtered_images_query_valid_input(db_address):
    images = db.filtered_images_query(db_address, VALID_QUERY_FILTERS)
    assert images

def test_filtered_images_query_invalid_input(db_address):
    with pytest.raises(ArgumentError):
        images = db.filtered_images_query(db_address, INVALID_QUERY_FILTERS)


def test_get_image_by_filename_valid_input(db_address):
    image = db.get_image_by_filename(db_address, VALID_BASE_FILENAME)
    assert len(image.keys()) > 0


def test_get_image_by_filename_invalid_input(db_address):
    with pytest.raises(NoResultFound):
        image = db.get_image_by_filename(db_address, INVALID_BASE_FILENAME)

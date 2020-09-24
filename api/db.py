import logging
import json
import boto3
from datetime import datetime
from http import HTTPStatus
from contextlib import contextmanager
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy.engine.url import URL # don't need if we get the db-address from aws ssm.
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.exc import ArgumentError

from api.helpers import _get_secret, http_response
from api.helpers import get_s3_image_path, get_s3_file_url

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

Base = declarative_base()
DB_ADDRESS = _get_secret('db-url')

@contextmanager
def get_session(db_address):
    """ Get a connection to the database.

    Returns:
        session: SQLAlchemy Database Session
    """
    engine = create_engine(db_address)
    db_session = sessionmaker(bind=engine)
    session = db_session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class Image(Base):
    __tablename__ = 'images'

    image_id         = Column(Integer, primary_key=True)
    base_filename    = Column(String)
    site             = Column(String)
    capture_date     = Column(DateTime, default=datetime.utcnow)
    sort_date        = Column(DateTime, default=datetime.utcnow)
    right_ascension  = Column(Float)
    declination      = Column(Float)
    ex00_fits_exists = Column(Boolean)
    ex01_fits_exists = Column(Boolean)
    ex10_fits_exists = Column(Boolean)
    ex13_fits_exists = Column(Boolean)
    ex10_jpg_exists  = Column(Boolean)
    ex13_jpg_exists  = Column(Boolean)
    altitude         = Column(Float)
    azimuth          = Column(Float)
    filter_used      = Column(String)
    airmass          = Column(Float)
    exposure_time    = Column(Float)
    username         = Column(String)
    user_id          = Column(String)
    header           = Column(String)

    def __init__(self, base_filename):
        self.base_filename = base_filename

    def get_image_pkg(self):
        """ A dictionary representation of common image metadata.

        This is the format that is used and expected by the frontend when it 
        queries this api for images. 

        Notably missing from this is the entire fits header, for smaller 
        payload sizes. 
        
        """

        package = {
            "image_id": self.image_id,
            "base_filename": self.base_filename,
            "site": self.site, 

            "exposure_time": self.exposure_time,
            "filter_used": self.filter_used,
            "right_ascension": self.right_ascension, 
            "declination": self.declination, 
            "azimuth": self.azimuth,
            "altitude": self.altitude,
            "airmass": self.airmass,

            "ex01_fits_exists": self.ex01_fits_exists,
            "ex10_fits_exists": self.ex10_fits_exists,
            "ex10_jpg_exists": self.ex10_jpg_exists,
            "ex13_jpg_exists": self.ex13_jpg_exists,
            "ex00_fits_exists": self.ex00_fits_exists,

            "username": self.username,
            "user_id": self.user_id,
        }

        # Convert to timestamp in milliseconds
        package["capture_date"] = int(1000 * self.capture_date.timestamp())
        package["sort_date"] = int(1000 * self.sort_date.timestamp())

        # Include a url to the jpg
        package["jpg_url"] = ""
        if self.ex10_jpg_exists:
            path = get_s3_image_path(self.base_filename, "EX10", "jpg")
            url = get_s3_file_url(path)
            package["jpg_url"] = url

        return package


def get_latest_site_images(db_address, site, number_of_images, user_id=None):
    """ Get the n latest images from a site. 

    Note: only returns sucessfully if the jpg preview exists. 

    Args: 
        db_address (str): address for the database to query
        site (str): 3-letter site code
        number_of_images(int): number of images to return
        user_id (str): optional, filters out any images not taken by the user. 
                Still returns `number_of_images` images.

    Returns:
        list[dict]: list of dicts, each representing one image with metadata.

    """
    # Filter by site, and by user_id if provided.
    query_filters = [
        Image.site==site,
        Image.ex10_jpg_exists.is_(True) # the jpg preview must exist
    ]
    if user_id:
        query_filters.append(Image.user_id==user_id)

    with get_session(db_address=db_address) as session:
        images = session.query(Image)\
            .order_by(Image.sort_date.desc())\
            .filter(*query_filters)\
            .limit(number_of_images)\
            .all()
        session.expunge_all()
    image_pkgs = [image.get_image_pkg() for image in images]
    return image_pkgs


def get_fits_header_from_db(db_address, base_filename):
    """ Return the fits header as a dictionary for the given fits file.

    Args: 
        db_address (str): address for the database to query
        base_filename (str): the filename (without the ex-version or .extension)
                for identifying the header we want. 

    Returns:
        dict: the fits header as a dictionary.

    """
    with get_session(db_address=db_address) as session:
        header = session.query(Image.header)\
            .filter(Image.base_filename==base_filename)\
            .one()
    header_dict = json.loads(header[0])
    return header_dict


def filtered_images_query(db_address: str, query_filters: list): 
    """ Get images that satisfy the specified filters. 

    Common query filters include exposure duration, site, capture date, 
            image filter, etc...

    Args: 
        db_address (str): address for the database to query
        query_filters (list): all the filter expressions. These will be 
                sent in the sqlalchemy filter method as .filter(*query_filters)

    Returns:
        list[dict]: list of dicts, each representing an image with metadata.

    """
    # Add the condition that the jpg must exist
    query_filters.append(Image.ex10_jpg_exists.is_(True))
    with get_session(db_address=db_address) as session:
        images = session.query(Image)\
            .order_by(Image.sort_date.desc())\
            .filter(*query_filters)\
            .limit(100)\
            .all()
        session.expunge_all()
    image_pkgs = [image.get_image_pkg() for image in images]
    return image_pkgs


def get_image_by_filename(db_address, base_filename):
    """ Get the image package for the image specified by the filename. 

    Note: only returns sucessfully if the jpg preview exists. 

    Args: 
        db_address (str): address for the database to query
        base_filename (str): the filename (without the ex-version or .extension)
                for identifying the header we want. 

    Returns:
        dict: the image package representing the image with common metadata.

    """
    query_filters = [
        Image.base_filename == base_filename, # match filenames
        Image.ex10_jpg_exists.is_(True)       # the jpg must exist
    ]
    with get_session(db_address=db_address) as session:
        image = session.query(Image)\
            .filter(*query_filters)\
            .one()
        return image.get_image_pkg()


#####################################################
##############    Endpoint Handlers    ##############
#####################################################

def get_latest_site_images_handler(event, context):

    # Parse the arguments passed in the http request.
    site = event['pathParameters']['site']
    number_of_images = event['pathParameters']['number_of_images']

    # Feed these args into the db query function
    query_args = {
        "db_address": DB_ADDRESS,
        "site": site,
        "number_of_images": number_of_images,
    }

    # If a user_id is provided, then our query should include a user_id filter.
    query_params = event['queryStringParameters']
    if query_params and "userid" in query_params.keys():
        query_args["user_id"] = query_params["userid"]

    images = get_latest_site_images(**query_args)
    return http_response(HTTPStatus.OK, images)


def get_fits_header_from_db_handler(event, context):
    base_filename = event['pathParameters']['base_filename']

    try:
        header = get_fits_header_from_db(DB_ADDRESS, base_filename)
    except NoResultFound:
        error_msg = f"No fits header found in the db for {base_filename}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)
    return http_response(HTTPStatus.OK, header)


def get_image_by_filename_handler(event, context):
    base_filename = event['pathParameters']['base_filename']

    try: 
        image = get_image_by_filename(DB_ADDRESS, base_filename)
    except NoResultFound:
        error_msg = f"No results found for {base_filename}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)
    except MultipleResultsFound:
        error_msg = f"Multiple images found for {base_filename}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

    return http_response(HTTPStatus.OK, image)


def filtered_images_query_handler(event, context):
    filter_params = event['queryStringParameters']

    # Get filter parameters:
    query_filters = []
    if "username" in filter_params:
        query_filters.append(Image.username==filter_params["username"])
    if "site" in filter_params:
        query_filters.append(Image.site==filter_params["site"])
    if "filter" in filter_params:
        query_filters.append(Image.filter_used==filter_params["filter"])
    if "exposure_time_min" in filter_params:
        query_filters.append(Image.exposure_time >= filter_params["exposure_time_min"])
    if "exposure_time_max" in filter_params:
        query_filters.append(Image.exposure_time <= filter_params["exposure_time_max"])
    if "start_date" in filter_params:
        query_filters.append(Image.capture_date >= filter_params["start_date"])
    if "end_date" in filter_params:
        query_filters.append(Image.capture_date <= filter_params["end_date"])
    if "filename" in filter_params:
        query_filters.append(Image.base_filename.like(filter_params["filename"]))

    try: 
        images = filtered_images_query(DB_ADDRESS, query_filters)
    except ArgumentError:
        error_msg = "Invalid query filter. "
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)
    except Exception as e:
        logger.exception("Error in filter images query. ")
        return http_response(HTTPStatus.NOT_FOUND, error_msg)

    return http_response(HTTPStatus.OK, images)

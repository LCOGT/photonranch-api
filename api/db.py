import logging
import json
import time
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

from api.helpers import get_secret, http_response
from api.helpers import get_s3_image_path, get_s3_file_url
from api.site_configs import get_all_sites

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

Base = declarative_base()
DB_ADDRESS = get_secret('db-url')

engine = create_engine(DB_ADDRESS)
db_session = sessionmaker(bind=engine)

@contextmanager
def get_session():
    """Gets a connection to the database.

    Returns:
        session: SQLAlchemy Database Session.
    """
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

    image_id          = Column(Integer, primary_key=True)
    base_filename     = Column(String)
    data_type         = Column(String)
    site              = Column(String)
    capture_date      = Column(DateTime, default=datetime.utcnow)
    sort_date         = Column(DateTime, default=datetime.utcnow)
    right_ascension   = Column(Float)
    declination       = Column(Float)

    fits_01_exists    = Column(Boolean)
    fits_10_exists    = Column(Boolean)
    jpg_medium_exists = Column(Boolean)
    jpg_small_exists  = Column(Boolean)

    altitude          = Column(Float)
    azimuth           = Column(Float)
    filter_used       = Column(String)
    airmass           = Column(Float)
    exposure_time     = Column(Float)
    username          = Column(String)
    user_id           = Column(String)
    header            = Column(String)


    def __init__(self, base_filename):
        self.base_filename = base_filename


    def get_image_pkg(self):
        """A dictionary representation of common image metadata.

        This is the format that is used and expected by the frontend when it
        queries this api for images.

        Notably missing from this is the entire fits header, for smaller
        payload sizes.
        """
        header_dictionary = json.loads(self.header) if self.header is not None else None

        # Attempt to reconstruct the fits filename and archive file path from the header data
        fits_filename = ''
        fits_path = ''
        if header_dictionary:
            fits_path = header_dictionary.get('SITEID', '') + '/' + header_dictionary.get('INSTRUME', '')
            fits_path += '/' + header_dictionary.get('DAY-OBS', '') + '/raw'
            fits_filename = header_dictionary.get('ORIGNAME', '')

        package = {
            "image_id": self.image_id,
            "base_filename": self.base_filename,
            "data_type": self.data_type,
            "site": self.site,

            "exposure_time": self.exposure_time,
            "filter_used": self.filter_used,
            "right_ascension": self.right_ascension,
            "declination": self.declination,
            "azimuth": self.azimuth,
            "altitude": self.altitude,
            "airmass": self.airmass,

            "fits_01_exists": self.fits_01_exists,
            "fits_10_exists": self.fits_10_exists,
            "jpg_medium_exists": self.jpg_medium_exists,
            "jpg_small_exists": self.jpg_small_exists,

            "s3_directory": "data",

            "username": self.username,
            "user_id": self.user_id,
            "fits_filename": fits_filename,
            "fits_path": fits_path,
            "SMARTSTK": header_dictionary.get("SMARTSTK", '') if header_dictionary is not None else '',
            "SSTKNUM": header_dictionary.get("SSTKNUM", '') if header_dictionary is not None else ''
        }

        # Convert to timestamp in milliseconds
        package["capture_date"] = int(1000 * self.capture_date.timestamp())
        package["sort_date"] = int(1000 * self.sort_date.timestamp())

        # Include a url to the jpg
        package["jpg_url"] = ""
        if self.jpg_medium_exists:
            path = get_s3_image_path(self.base_filename, self.data_type, "10", "jpg")
            url = get_s3_file_url(path)
            package["jpg_url"] = url

        package["jpg_thumbnail_url"] = ""
        if self.jpg_small_exists:
            path = get_s3_image_path(self.base_filename, self.data_type, "11", "jpg")
            url = get_s3_file_url(path)
            package["jpg_thumbnail_url"] = url

        return package


    def get_jpg_url(self):
        """Returns the s3 URL to the medium jpg at AWS."""
        if self.jpg_medium_exists:
            path = get_s3_image_path(self.base_filename, self.data_type, "10", "jpg")
            return get_s3_file_url(path)
        return ''


    def get_small_fits_filename(self):
        return f"{self.base_filename}-{self.data_type}10.fits.fz"


    def get_large_fits_filename(self):
        return f"{self.base_filename}-{self.data_type}01.fits.fz"


    def get_best_fits_filename(self):
        """Returns the full filename for the largest fits version stored in s3.

        If there is no fits file available, return an empty string.
        """

        if self.fits_01_exists:
            return f"{self.base_filename}-{self.data_type}01.fits.fz"

        elif self.fits_10_exists:
            return f"{self.base_filename}-{self.data_type}10.fits.fz"

        else: return ''


def get_latest_site_images(db_address, site, number_of_images, user_id=None):
    """Gets the n latest images from a site.

    Note: Only returns sucessfully if the jpg preview exists.

    Args:
        db_address (str): Address for the database to query.
        site (str): 3-letter site code.
        number_of_images (int): Number of images to return.
        user_id (str):
            Optional, filters out any images not taken by the user.
            Still returns `number_of_images` images.

    Returns:
        list[dict]: List of dicts, each representing one image with metadata.
    """

    # Filter by site, and by user_id if provided.
    query_filters = [
        Image.site==site,
        Image.jpg_medium_exists.is_(True)  # The jpg preview must exist
    ]
    if user_id:
        query_filters.append(Image.user_id==user_id)

    with get_session() as session:
        images = session.query(Image)\
            .order_by(Image.sort_date.desc())\
            .filter(*query_filters)\
            .limit(number_of_images)\
            .all()
        session.expunge_all()
    image_pkgs = [image.get_image_pkg() for image in images]
    return image_pkgs


def get_latest_image_all_sites():
    """Gets the latest images at all sites."""

    start = time.time()
    sites = get_all_sites()
    print(time.time() - start)
    print(sites)
    results = {}

    with get_session() as session:
        for site in sites:
            print(time.time() - start)
            site_image = session.query(Image)\
                .filter(Image.site == site)\
                .filter(Image.jpg_medium_exists == True)\
                .order_by(Image.sort_date.desc())\
                .limit(1)\
                .first()
            if site_image:
                results[site] = site_image.get_jpg_url()
        print(results)
        session.expunge_all()
        print('final time: ', time.time() - start)
    return results


def get_fits_header_from_db(db_address, base_filename):
    """Returns the fits header as a dictionary for the given fits file.

    Args:
        db_address (str): Address for the database to query.
        base_filename (str):
            The filename (without the ex-version or .extension)
            for identifying the header we want.

    Returns:
        dict: The fits header as a dictionary.
    """

    with get_session() as session:
        header = session.query(Image.header)\
            .filter(Image.base_filename==base_filename)\
            .one()
    header_dict = json.loads(header[0]) if header[0] is not None else {}
    return header_dict


def filtered_images_query(db_address: str, query_filters: list):
    """Gets images that satisfy the specified filters.

    Common query filters include exposure duration, site, capture date,
    image filter, etc...

    Args:
        db_address (str): Address for the database to query.
        query_filters (list):
            All the filter expressions. These will be sent in the
            sqlalchemy filter method as .filter(*query_filters).

    Returns:
        list[dict]: List of dicts, each representing an image with metadata.
    """

    # Add the condition that the jpg must exist
    query_filters.append(Image.jpg_medium_exists.is_(True))
    with get_session() as session:
        images = session.query(Image)\
            .order_by(Image.sort_date.desc())\
            .filter(*query_filters)\
            .all()
        session.expunge_all()
    image_pkgs = [image.get_image_pkg() for image in images]
    image_pkgs = filter_img_pkgs_final_sstack(image_pkgs)
    return image_pkgs

# Filter out intermediate smart stacks to reduce the size of ui payload
def filter_img_pkgs_final_sstack(image_pkgs):
    # dict containing max stknum for each unique smartstack
    max_sstk_nums = {}

    for img_pkg in image_pkgs:
        if not img_pkg.get('SSTKNUM', 0).isdigit():
            continue

        smart_stk = img_pkg.get('SMARTSTK')
        sstk_num = int(img_pkg.get('SSTKNUM', 0))

        if smart_stk is None or smart_stk == 'no':
            continue
        
        if smart_stk not in max_sstk_nums or sstk_num > max_sstk_nums[smart_stk]:
            max_sstk_nums[smart_stk] = sstk_num
    
    # keep non intermediate img_pkgs, non smart stack img_pkgs, and img_pkgs missing smart stack keys
    filtered_arr = [
        img_pkg for img_pkg in image_pkgs
        if img_pkg.get('SMARTSTK') is None
        or img_pkg.get('SSTKNUM') is None
        or img_pkg.get('SMARTSTK') == 'no'
        or not img_pkg.get('SMARTSTK').isdigit()
        or int(img_pkg.get('SSTKNUM', 0)) >= max_sstk_nums.get(img_pkg.get('SMARTSTK'), 0)
    ]

    return filtered_arr

def get_image_by_filename(db_address, base_filename):
    """Gets the image package for the image specified by the filename.

    Note: Only returns sucessfully if the jpg preview exists.

    Args:
        db_address (str): Address for the database to query.
        base_filename (str):
            The filename (without the ex-version or .extension)
            for identifying the header we want.

    Returns:
        dict: The image package representing the image with common metadata.
    """

    query_filters = [
        Image.base_filename == base_filename,  # Match filenames
        Image.jpg_medium_exists.is_(True)      # The jpg must exist
    ]
    with get_session() as session:
        image = session.query(Image)\
            .filter(*query_filters)\
            .one()
        return image.get_image_pkg()


def remove_image_by_filename(base_filename):
    """Removes an entire row represented by the data's base filename.

    Args:
        base_filename (str):
            Identifies what to delete. Example: saf-ea03-20190621-00000007.
    """

    with get_session() as session:
        Image.query\
            .filter(Image.base_filename == base_filename)\
            .delete()
        session.commit()


def get_files_within_date_range(site: str, start_timestamp_s: int,
        end_timestamp_s: int, fits_size: str):
    """Queries for files at a given site within a date range.

    Args:
        site (str): Sitecode (eg. "mrc").
        start_timestamp_s (int): Timestamp in seconds, early bound.
        end_timestamp_s (int): Timestamp in seconds, later bound.
        fits_size (str):
            "small" | "large" | "best": choose whether to only select
            small fits files, only large fits files, or best available.

    Returns:
        list: List of filenames (str) that match the query.
    """

    fits_size = fits_size.lower()
    if not fits_size in ['small', 'large', 'best']:
        raise ValueError('fits_size must be either "small", "large", or "best".')

    start_datetime = datetime.fromtimestamp(start_timestamp_s)
    end_datetime = datetime.fromtimestamp(end_timestamp_s)
    query_filters = [
        Image.site == site,
        Image.capture_date >= start_datetime,
        Image.capture_date <= end_datetime,
    ]
    if fits_size == "small":
        query_filters.append(Image.fits_10_exists.is_(True))
    elif fits_size == "large":
        query_filters.append(Image.fits_01_exists.is_(True))

    with get_session() as session:
        images = session.query(Image)\
            .filter(*query_filters)\
            .all()
        session.expunge_all()

    if fits_size == "small":
        return [image.get_small_fits_filename() for image in images]

    elif fits_size == "large":
        return [image.get_large_fits_filename() for image in images]

    elif fits_size == "best":
        return [image.get_best_fits_filename() for image in images]


#####################################################
##############    Endpoint Handlers    ##############
#####################################################

def get_latest_site_images_handler(event, context):
    """Handler for getting the latest images at a site.

    Args:
        event.body.site: Sitecode (eg. "saf").
        event.body.number_of_images: Number of images to return.

    Returns:
        200 status code with latest site image data.
    """

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


def get_latest_images_all_sites_handler(event, context):
    images = get_latest_image_all_sites()
    return http_response(HTTPStatus.OK, images)


def get_fits_header_from_db_handler(event, context):
    """Handler for retrieving the header from a specified fits file.

    Args:
        event.body.base_filename:
            The filename (without the ex-version or .extension)
            for identifying the header we want.

    Returns:
        200 status code with header info if successful.
        404 status code if no header found with given base_filename.
    """

    base_filename = event['pathParameters']['base_filename']

    try:
        header = get_fits_header_from_db(DB_ADDRESS, base_filename)
    except NoResultFound:
        error_msg = f"No fits header found in the db for {base_filename}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, error_msg)
    return http_response(HTTPStatus.OK, header)


def get_image_by_filename_handler(event, context):
    """Handler for retrieving an image given the base filename.

    Args:
        event.body.base_filename (str):
            Filename (without the 'EX' or .extension).

    Returns:
        200 status code with requested image if successful.
        404 status code if:
            - No files found with given base filename.
            - Multiple files found with given base filename.
    """

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
    """Handler for querying images based on specified filters.

    Requests may query based on username, user_id, site, filter
    (as in imaging), min and max exposure times, start and end
    dates, or filename.

    Returns:
        200 status code with matching images if successful.
        400 status code if ArgumentError results in a bad request.
        404 status code if other exception occurs during query.
    """

    filter_params = event['queryStringParameters']

    # Get filter parameters:
    query_filters = []
    if "username" in filter_params:
        query_filters.append(Image.username==filter_params["username"])
    if "user_id" in filter_params:
        query_filters.append(Image.user_id==filter_params["user_id"])
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
        return http_response(HTTPStatus.BAD_REQUEST, error_msg)
    except Exception as e:
        logger.exception("Error in filter images query. ")
        return http_response(HTTPStatus.NOT_FOUND, e)

    return http_response(HTTPStatus.OK, images)


def remove_image_by_filename_handler(event, context):
    """Handler for removing an image given the base filename.

    Args:
        event.body.base_filename: Filename (without the 'EX' or .extension).

    Returns:
        200 status code with successful removal of image.
        404 status code if exception occurs during attempted removal.
    """

    base_filename = event['pathParameters']['base_filename']

    try:
        remove_image_by_filename(base_filename)
    except Exception as e:
        error_msg = f"Could not delete {base_filename}. Error: {e}"
        logger.exception(error_msg)
        return http_response(HTTPStatus.NOT_FOUND, e)

    return http_response(HTTPStatus.OK, f'Successfully removed {base_filename}')

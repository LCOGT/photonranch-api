import boto3
import uuid
from astropy.io import fits
import numpy
import tifffile
import logging
import bz2
import os

s3_client = boto3.client('s3')
log = logging.getLogger()
log.setLevel(logging.INFO)

def save_tiff_to_s3(bucket, s3_source_key, stretch):
    tmpkey = s3_source_key.replace('/', '')
    local_source_file_path = f"/tmp/{uuid.uuid4()}{tmpkey}"
    local_tiff_file_path = f"/tmp/tiff-{tmpkey}.tif"
    local_tiff_file_path_bz2 = f"/tmp/tiff-{tmpkey}.tif.bz2"

    s3_client.download_file(bucket, s3_source_key, local_source_file_path)
    image_metadata = create_tiff(local_source_file_path, local_tiff_file_path, stretch)

    # generate the name for the item in s3, also the name of the downloaded file
    source_filename = s3_source_key.split('/')[-1]
    tif_filename = f"{source_filename.split('.')[0]}.tif.bz2"
    tif_filename = f"{image_metadata['FILTER']}-{stretch}-{tif_filename}"
    s3_destination_key = f"downloads/tif/{tif_filename}"

    s3_client.upload_file(local_tiff_file_path_bz2, bucket, s3_destination_key)
    return s3_destination_key


def save_fz_to_fits(bucket, s3_source_key, stretch):
    tmpkey = s3_source_key.replace('/', '')
    local_source_file_path = f"/tmp/{uuid.uuid4()}{tmpkey}"
    local_fits_file_path = f"/tmp/fits-{tmpkey}.fits"
    local_fits_file_path_fz = f"/tmp/fits-{tmpkey}.fits.fz"

    s3_client.download_file(bucket, s3_source_key, local_source_file_path)
    image_metadata = create_fitsfromfz(local_source_file_path, local_tiff_file_path)

    # generate the name for the item in s3, also the name of the downloaded file
    source_filename = s3_source_key.split('/')[-1]
    fits_filename = f"{source_filename.split('.')[0]}.fits"    
    s3_destination_key = f"downloads/fits/{fits_filename}"

    s3_client.upload_file(local_fits_file_path, bucket, s3_destination_key)
    return s3_destination_key

def create_tiff(local_source_file_path, local_tiff_file_path, stretch):
    with fits.open(local_source_file_path) as hdulist:
        prihdr = hdulist[0].header

        metadata = {
            'PTRName': 'thename',
            'FILTER': prihdr['FILTER']
        }

        # Linear 16bit tif
        ts = numpy.asarray(hdulist[0].data)

        # Arcsinh 16bit tif (It is an artificial stretch so there is some massaging to get it into a 16 bit tif)
        if stretch == "arcsinh":
            ts = numpy.arcsinh(ts)
            ts = ts - numpy.min(ts)
            # rescale it to take all of the integer range
            ts = ts * (65535.0/(numpy.max(ts)))
            ts = ts.astype(numpy.uint16)

        tifffile.imwrite(local_tiff_file_path, ts, metadata=metadata)
        to_bz2(local_tiff_file_path)
        return metadata

def create_fitsfromfz(local_source_file_path, local_fits_file_path):
    with fits.open(local_source_file_path) as hdulist:
        hdulist.verify('fix')
        # Pull out the original non-compressed fits and header
        cleanhdu=fits.PrimaryHDU()
        cleanhdu.data = numpy.asarray(hdulist[1].data)
        cleanhdu.header = hdulist[1].header
        
        cleanhdu.writeto(local_fits_file_path)

        return True

def to_bz2(filename, delete=False):
    try:
        uncomp = open(filename, 'rb')
        comp = bz2.compress(uncomp.read())
        uncomp.close()
        if delete:
            try:
                os.remove(filename)
            except:
                pass
        target = open(filename + '.bz2', 'wb')
        target.write(comp)
        target.close()
        return True
    except:
        log.info('to_bz2 failed.')
        return False

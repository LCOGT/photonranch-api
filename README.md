# Photon Ranch API

[![Coverage Status](https://coveralls.io/repos/github/LCOGT/photonranch-api/badge.svg?branch=master)](https://coveralls.io/github/LCOGT/photonranch-api?branch=master)

This is the API used to talk with Photon Ranch Services running in AWS. Communication between observatory sites and the web interface take place here, including sending/receiving commands, status, and handling data.

This is a serverless API, deployed with the Serverless framework which creates Python functions running in AWS Lambda behind endpoints in an API Gateway.

## Description

This repository is home to the backend services for several APIs as opposed to a single service. The repository name is an artifact of early development. The services maintained here include:

- **api**: Handles uploads, downloads, and zipping of files, as well as retrieval of recently uploaded images.
- **info_images**: For retrieving the info image package for a single image at a given site.
- **db**: Handles image database queries, such as retrieving the latest images at a site or across all sites, retrieving FITS headers, and filtering images.
- **site_configs**: Handles uploading, retrieving, or deleting a site config file, as well as getting all site config files.
- **remotehq**: Handles creating, getting, restarting, and deleting RemoteHQ control rooms.
- **night_log**: Creates and retrieves night log notes at a given site.
- **events**: Retrieves events such as moonrise, moonset, sunrise, observing windows, and other information about nightly events at a given site.

For more on the multifile zipping and downloading process, see the [photonranch-downloads](https://github.com/LCOGT/photonranch-downloads) repository.
## Dependencies

This application currently runs under Python 3.9. Dependencies for the Python Lambda functions are zipped with the `serverless-python-requirements` plugin. Special note for psycopg2 (Python postgres library): make sure `requirements.txt` lists 'psycopg2-binary', and not 'psycopg2'. This is required for the dependency to run in the Lambda environment.

To update npm dependencies, run `npm update`. This will update the package versions in `package-lock.json`.

## Local Development

Clone the repository to your local machine:

```
git clone https://github.com/LCOGT/photonranch-api.git
cd photonranch-api
```

### Requirements

You will need the [Serverless Framework](https://www.serverless.com/framework/docs/getting-started) installed locally for development. For manual deployment to AWS as well as for updating dependencies, you will need to install [Node](https://nodejs.org/en/), [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm), and [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), configuring with your own AWS credentials.

### Deployment

Changes pushed to the test, dev, and main branches are automatically deployed to the corresponding test, dev, and production stages with Github Actions. For manual deployment on your local machine, you'll first need to fill out the `public_key` and `secrets.json` with the required information, as well as install packages:

```
npm install
serverless plugin install --name serverless-python-requirements
```

To deploy, run:

```
serverless deploy --stage {stage}
```

In the case that a Serverless or AWS key has been reset, you will need to update these manually in this repository's settings for Github Actions to continue deploying. You must be a repository collaborator to edit these.

### Testing
Integration tests as well as unit tests for db, events, handler, and info images are automatically run before each deployment with Github Actions. Deployment will fail if any tests are not passed. To manually run tests on your machine, run the following in your photonranch-api directory:

`python -m pytest`

## API endpoints

Requests for all services in this repository are handled at the base URL `https://api.photonranch.org/{stage}`.

- POST `/upload`
  - Description: Generates a presigned URL to upload files at AWS. 
  - Authorization required: No.
  - Request body:
    - s3_directory (string): Name of the S3 directory to upload to in ["data", "info-images", "allsky", "test"].
    - filename (string): Name of the file to upload to AWS.
  - Responses:
    - 204: Successfully generated URL.
    - 403: Invalid S3 directory or info channel supplied.
- POST `/download`
  - Description: Downloads individual files from AWS.
  - Authorization required: No.
  - Request body:
    - s3_directory (string): Name of the S3 directory to download from.
    - object_name (string): Full filename of file to download.
    - image_type (string): Type of image in ["tif", "fits"].
    - stretch (string): Stretch parameters used for TIF files in ["linear", "arcsinh"].
  - Responses:
    - 200: Successfully generated URL.
    - 403: Invalid S3 directory supplied.
- POST `/downloadzip`
  - Description: Returns a link to download a zip of multiple FITS images.
  - Authorization required: No.
  - Request body:
    - start_timestamp_s (string): UTC datestring of starting time to query.
    - end_timestamp_s (string): UTC datestring of ending time to query.
    - fits_size (string): Size of the FITS file in (ex. "small", "large").
    - site (string): Sitecode (ex. "saf").
  - Responses:
    - 200: Successfully generated URL.
    - 404: No images match the supplied query.
- GET `/recentuploads`
  - Description: Queries for a list of files recently uploaded to S3.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode to query images from (ex. "saf").
  - Responses:
    - 200: Successfully retrieved recent images.
    - 404: Sitecode missing in request.
- GET `/infoimage/{site}/{channel}`
  - Description: Retrieves the full info image package for a specified site.
  - Authorization required: No.
  - Query parameters:
    - site (string): Sitecode to query images from (ex. "saf").
    - channel (int): Info channel in [1, 2, 3].
  - Responses:
    - 200: Successfully retrieved info image package.
    - 404: No info image found for given sitecode.
- GET `/image/{base_filename}`
  - Description: Retrieves an image from the database given the base filename.
  - Authorization required: No.
  - Query parameters: base_filename (string): Filename without the 'EX' or .extension included.
  - Responses:
    - 200: Successfully retrieved image.
    - 404: No files found.
    - 404: Multiple files found.
- GET `/{site}/latest_images/{number_of_images}`
  - Description: Gets the latest images at a site.
  - Authorization required: No.
  - Query parameters:
    - site (string): Sitecode.
    - number_of_images (int): Number of latest images to return.
  - Responses:
    - 200: Successfully retrieved latest images.
- GET `/latest_image_all_sites/`
  - Description: Gets the latest images at all sites.
  - Authorization required: No.
  - Responses:
    - 200: Successfully retrieved latest images at all sites.
- GET `/fitsheader/{base_filename}`
  - Description: Retrieves the header from a specified FITS file.
  - Authorization required: No.
  - Query parameters
    -  base_filename (string): Filename without the 'EX' or .extension included.
  - Responses:
    - 200: Succesfully retrieved header.
    - 404: No file with base_filename found.
- GET `/filtered_images`
  - Description: Queries the database based on specified filters.
  - Authorization required: No.
  - Request body:
    - Filter parameters ("username", "user_id", "site", "filter", "exposure_time_min", "exposure_time_max", "start_date", "end_date", "filename")
  - Responses:
    - 200: Successfully queried database.
    - 400: Bad request.
    - 404: Exception during query.
- GET `/{site}/config`
  - Description: Retrieves the config file details from a specified site.
  - Authorization required: No.
  - Query parameters: 
    - site (string): Sitecode.
  - Responses: 
    - 200: Successfully retrieved config file.
- PUT `/{site}/config`
  - Description: Adds a new config file to a specified site.
  - Authorization required: No.
  - Query parameters: 
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully added site config file.
- DELETE `/{site}/config`
  - Description: Deletes the config details for a specified site.
  - Authorization required: No.
  - Query parameters: 
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully deleted config file.
- GET `/all/config`
  - Description: Retrieves a list of all site configs.
  - Authorization required: No.
  - Responses:
    - 200: Successfully retrieved all site config files.
- POST `/new_remotehq_browser`
  - Description: Queries RemoteHQ API to create an embeddable remote browser instance.
  - Authorization required: Yes.
  - Responses:
    - 200: Successfully created browser instance.
- GET `/control_room/{site}`
  - Description: Creates or retrieves the details of a RemoteHQ room at a specified site.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully retrieved RHQ room details.
    - 200: Successfully created RHQ room (if not found).
    - 500: Failed to create or retrieve room details.
- DELETE `/control_room/{site}`
  - Description: Deletes a RemoteHQ control room from a specified site.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode.
  - Responses:
    - 200: Room successfully deleted.
    - 200: No such room found.
- GET `/control_room/{site}/restart`
  - Description: Restarts a RemoteHQ control room at a specified site.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully restarted requested room.
    - 404: Requested room cannot be found.
    - 500: Internal server error during room modification.
- GET `/nightlog/{site}`
  - Description: Retrieves a note (log) from a specified site.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully retrieved log.
- POST `/nightlog/{site}`
  - Description: Creates a note (log) at a specified site.
  - Authorization required: No.
  - Request body:
    - site (string): Sitecode.
    - note_data (str): Body of note to be logged.
  - Responses:
    - 200: Successfully created note.
- GET `/events`
  - Description: Retrieves a dictionary of site events at a given site and time.
  - Authorization required: No.
  - Request body:
    - when (float): Unix timestamp within the 24hr block (local noon-noon) when we want to get events.
    - site (string): Sitecode.
  - Responses:
    - 200: Successfully returned dictionary of site events.
    - 400: Sitecode missing from request.
    - 500: Sitecode does not match any existing site.
    - 500: Invalid timezone name supplied in site config.
    - 500: Request missing a required parameter.
- GET `/events/moon/rise-set-illum`
  - Description: Gets the moon rise and set times and illumination for a site.
  - Authorization required: No.
  - Request body:
    - lat (float): Latitude of the observing location in degrees N.
    - lng (float): Longitude of the observing location in degrees E.
    - start (string): UTC ISO starting time string (eg. "2022-12-31T01:00:00Z").
    - end (str): UTC ISO ending time string.
  - Responses:
    - 200: Successfully calculated site events.
    - 404: Incorrect datestring format supplied.
    - 404: Exception during calculation.

### Examples

To retrieve a list of site events at a specific site:

```python
import requests
sitecode = "saf"
url = f"https://api.photonranch.org/api/events?site={sitecode}"
events = requests.get(url).json()
```

To retrieve a list of yesterday's site events:
```python
import requests, time
sitecode = "saf"
yesterday = time.time() - 86400  # Subtract a day in seconds
url = f"https://api.photonranch.org/api/events?site={sitecode}&when={yesterday}"
events = requests.get(url).json()
```

#### Site Events Service

It is often useful to know when the sky is in certain states at an observatory. These may include:

- Sunset/sunrise
- Moonset/moonrise
- Twilight times
- Operations start/end times
- Calibration acquisition start/end times

The full JSON of site events is a dictionary with the following contents and syntax:

```json
{
    "Eve Bias Dark": <julian-days>,
    "End Eve Bias Dark": <julian-days>,
    "Eve Scrn Flats": <julian-days>,
    "End Eve Scrn Flats": <julian-days>,
    "Ops Window Start": <julian-days>,
    "Observing Begins": <julian-days>,
    "Observing Ends": <julian-days>,
    "Cool Down, Open": <julian-days> ,
    "Eve Sky Flats": <julian-days>,
    "Sun Set": <julian-days>,
    "Civil Dusk": <julian-days>,
    "End Eve Sky Flats": <julian-days>,
    "Clock & Auto Focus": <julian-days> ,
    "Naut Dusk": <julian-days>,
    "Astro Dark": <julian-days>,
    "Middle of Night": <julian-days>,
    "End Astro Dark": <julian-days>,
    "Final Clock & Auto Focus": <julian-days>,
    "Naut Dawn": <julian-days>,
    "Morn Sky Flats": <julian-days>,
    "Civil Dawn": <julian-days>,
    "End Morn Sky Flats": <julian-days>,
    "Ops Window Closes": <julian-days>,
    "Sunrise": <julian-days>,
    "Moon Rise": <julian-days>,
    "Moon Set": <julian-days>,
}
```

where `<julian-days>` is a float representing the TAI time in Julian days. These details can be retrieved at the GET `/events` endpoint following the previously specified details.

## License

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
- **night_log**: Creates and retrieves night log notes at a given site.
- **events**: Retrieves events such as moonrise, moonset, sunrise, observing windows, and other information about nightly events at a given site.
- **pipe queue**: Handles the job queue for PIPE machines processing observatory data

For more on the multifile zipping and downloading process, see the [photonranch-downloads](https://github.com/LCOGT/photonranch-downloads) repository.

## Dependencies

This application currently runs under Python 3.9. Dependencies for the Python Lambda functions are zipped with the `serverless-python-requirements` plugin. Special note for psycopg2 (Python postgres library): make sure `requirements.txt` lists 'psycopg2-binary', and not 'psycopg2'. This is required for the dependency to run in the Lambda environment.

To update npm dependencies, run `npm update`. This will update the package versions in `package-lock.json`.

## Local Development

Clone the repository to your local machine:

```bash
git clone https://github.com/LCOGT/photonranch-api.git
cd photonranch-api
```

### Requirements

You will need the [Serverless Framework](https://www.serverless.com/framework/docs/getting-started) installed locally for development. For manual deployment to AWS as well as for updating dependencies, you will need to install [Node](https://nodejs.org/en/), [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm), and [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html), configuring with your own AWS credentials.

### Deployment

Changes pushed to the test, dev, and main branches are automatically deployed to the corresponding test, dev, and production stages with Github Actions. For manual deployment on your local machine, you'll first need to fill out the `public_key` and `secrets.json` with the required information, as well as install packages:

```bash
npm install
serverless plugin install --name serverless-python-requirements
```

To deploy, run:

```bash
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
    - base_filename (string): Filename without the 'EX' or .extension included.
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

## PIPE Queue Service

The PIPE Queue service provides FIFO (First-In-First-Out) queues and status tracking for PIPE computers that process observatory data. This service allows the observatory to notify PIPE machines of new jobs and enables PIPE machines to communicate processing results back to the observatory.

### Queue and Status Management

- Multiple FIFO queues can be created and managed
- Each PIPE machine's status (online/offline) can be tracked
- RESTful API for all queue and status operations
- Single DynamoDB table for both queues and status tracking

### Endpoints

#### Queue Operations

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/pipe/queue` | Create a new queue | `{"queue_name": "string"}` | `{"message": "Queue created: queue_name"}` |
| POST | `/pipe/enqueue` | Add item to a queue | `{"queue_name": "string", "payload": {}, "sender": "string"}` | Item details |
| GET | `/pipe/queue/{queue_name}?limit=10` | View items without removing | N/A | Array of queue items |
| POST | `/pipe/queue/{queue_name}/dequeue` | Remove and return oldest item | N/A | Dequeued item |
| DELETE | `/pipe/queue/{queue_name}` | Delete a queue and all its items | N/A | `{"message": "Queue deleted: queue_name"}` |
| GET | `/pipe/queues` | List all queues with item counts | N/A | `{"queue1": count, "queue2": count, ...}` |

#### Status Operations

| Method | Endpoint | Description | Request Body | Response |
|--------|----------|-------------|--------------|----------|
| POST | `/pipe/status` | Set status for a PIPE machine | `{"pipe_id": "string", "status": "string", "details": {}}` | Status details |
| GET | `/pipe/status/{pipe_id}` | Get status of a specific PIPE machine | N/A | Status details |
| GET | `/pipe/statuses` | Get status of all PIPE machines | N/A | Array of statuses |
| DELETE | `/pipe/status/{pipe_id}` | Delete status of a specific PIPE machine | N/A | `{"message": "Status deleted for PIPE: pipe_id"}` |

### Example Usage

Recall the base url depends on the environment:

- prod: https://api.photonranch.org/api
- dev: https://api.photonranch.org/dev

#### Creating a Queue

```python
def create_queue(queue_name):
    """Create a new queue."""
    url = f"{BASE_URL}/pipe/queue"
    payload = {"queue_name": queue_name}

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print(f"Queue created: {queue_name}")
        return response.json()
    else:
        print(f"Error creating queue: {response.status_code}")
        print(response.text)
        return None
```

#### Enqueuing an Item

```python
def enqueue_item(queue_name, payload, sender="python-client"):
    """Add an item to a queue."""
    url = f"{BASE_URL}/pipe/enqueue"
    data = {
        "queue_name": queue_name,
        "payload": payload,
        "sender": sender
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        print(f"Item added to queue: {queue_name}")
        return response.json()
    else:
        print(f"Error adding item to queue: {response.status_code}")
        print(response.text)
        return None
```

#### Viewing Queue Items

```python
def peek_queue(queue_name, limit=5):
    """View items in a queue without removing them."""
    url = f"{BASE_URL}/pipe/queue/{queue_name}"
    params = {"limit": limit}

    response = requests.get(url, params=params)

    if response.status_code == 200:
        items = response.json()
        print(f"Found {len(items)} items in queue: {queue_name}")
        return items
    else:
        print(f"Error viewing queue: {response.status_code}")
        print(response.text)
        return None
```

#### Dequeuing an Item

```python
def dequeue_item(queue_name):
    """Remove and return the oldest item from a queue."""
    url = f"{BASE_URL}/pipe/queue/{queue_name}/dequeue"

    response = requests.post(url)

    if response.status_code == 200:
        print(f"Item dequeued from: {queue_name}")
        return response.json()
    elif response.status_code == 404:
        print(f"Queue is empty or not found: {queue_name}")
        return None
    else:
        print(f"Error dequeuing item: {response.status_code}")
        print(response.text)
        return None
```

#### Setting PIPE Status

```python
def set_pipe_status(pipe_id, status, details=None):
    """Set the status of a PIPE machine."""
    url = f"{BASE_URL}/pipe/status"
    data = {
        "pipe_id": pipe_id,
        "status": status,
        "details": details or {}
    }

    response = requests.post(url, json=data)

    if response.status_code == 200:
        print(f"Status set for PIPE: {pipe_id}")
        return response.json()
    else:
        print(f"Error setting status: {response.status_code}")
        print(response.text)
        return None
```

#### Getting PIPE Status

```python
def get_pipe_status(pipe_id):
    """Get the status of a specific PIPE machine."""
    url = f"{BASE_URL}/pipe/status/{pipe_id}"

    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"PIPE not found: {pipe_id}")
        return None
    else:
        print(f"Error getting status: {response.status_code}")
        print(response.text)
        return None
```

#### Getting Status of All PIPE Machines

```python
def get_all_pipe_statuses():
    """Get the status of all PIPE machines."""
    url = f"{BASE_URL}/pipe/statuses"

    response = requests.get(url)

    if response.status_code == 200:
        statuses = response.json()
        print(f"Found {len(statuses)} PIPE machines")
        return statuses
    else:
        print(f"Error getting statuses: {response.status_code}")
        print(response.text)
        return None
```

### DynamoDB Table Design

The service uses a single DynamoDB table with the following structure:

- **Table Name**: `pipe-queue-table`
- **Primary Key**: Composite key of `pk` (partition key) and `sk` (sort key)
- **Queue Items**:
  - `pk`: `"QUEUE#{queue_name}"`
  - `sk`: `"ITEM#{item_id}"`
  - Additional attributes: `id`, `item_type`, `payload`, `created_at`, `sender`
- **Queue Metadata**:
  - `pk`: `"QUEUE#{queue_name}"`
  - `sk`: `"METADATA"`
  - Additional attributes: `item_type`, `created_at`, `queue_name`
- **Status Items**:
  - `pk`: `"STATUS#{pipe_id}"`
  - `sk`: `"INFO"`
  - Additional attributes: `item_type`, `status`, `last_updated`, `details`

### Misc. Notes

- Queue items use timestamp-prefixed IDs to ensure FIFO ordering
- Ensure the queue has been created before trying to enqueue or dequeue
- The dequeue operation will return a 404 error if the queue is empty

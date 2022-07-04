# Photon Ranch API

[![Build Status](https://travis-ci.com/LCOGT/photonranch-api.svg?branch=master)](https://travis-ci.com/LCOGT/photonranch-api)
[![Coverage Status](https://coveralls.io/repos/github/LCOGT/photonranch-api/badge.svg?branch=master)](https://coveralls.io/github/LCOGT/photonranch-api?branch=master)

This is the API used to talk with Photon Ranch Services running in AWS. Communication between observatory sites and the web interface take place here, including sending/receiving commands, status, and handling data.

This is a Serverless API, deployed with the Serverless framework which creates Python functions running in AWS Lambda behind endpoints in an API Gateway.

## Description



## Dependencies

This application currently runs under Python 3.9. Dependencies for the Python Lambda functions are zipped with the `serverless-python-requirements` plugin. Special note for psycopg2 (Python postgres library): make sure `requirements.txt` lists 'psycopg2-binary', and not 'psycopg2'. This is required for the dependency to run in the Lambda environment.

To update npm dependencies, run `npm update`. This will update the package versions in `package-lock.json`.

## Local Development

Clone the repository to your local machine:

```
git clone https://github.com/LCOGT/photonranch-api.git
cd photonranch-calendar
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


## API endpoints


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

## License



---

**Site Events Service**
----

It is often useful to know when the sky is in certain states at an observatory. These ones, to be specific:

sunset/sunrise
moonset/moonrise
twilight times
operations start/end times
calibration acquisition start/end times

* **URL**

  /events

* **Method:**
  
  `GET`
  
* **Query Params**

   **Required:**

   `site=[str]`: site abbreviation, used to specify the site config containing required data (lat, lng, etc...)

   **Optional:**

   `when=[float]`: unix timestamp (seconds) for the 24 hr period that events are calculated. Default behavior uses the current time.

* **Success Response:**
  
  * **Code:** 200 SUCCESS <br />
    **Content:**

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

    where `<julian-days>` is a float representing the TAI time in julian days.

* **Error Response:**

  * **Code:** 500 <br />
    **Content:** `{ error : "Site config missing required parameters..." }`

  OR

  * **Code:** 500 <br />
    **Content:** `{ error : "The specified sitecode did not match any config file." }`

  OR

  * **Code:** 400 <br />
    **Content:** `{ error : "Missing 'site' query string request parameter" }`

# Photon Ranch API

[![Build Status](https://travis-ci.com/LCOGT/photonranch-api.svg?branch=master)](https://travis-ci.com/LCOGT/photonranch-api)
[![Coverage Status](https://coveralls.io/repos/github/LCOGT/photonranch-api/badge.svg?branch=feature/add-travis)](https://coveralls.io/github/LCOGT/photonranch-api?branch=feature/add-travis)


This is the api used to talk with photon ranch services running in AWS. All communication between observatory sites and the web interface take place here, including sending/receiving commands, status, and handling data.

This is a serverless api, deployed with the Serverless framework which creates python functions running in AWS Lambda behind endpoints in an API Gateway.

Dependencies for the python lambda functions are zipped with the serverless-python-requirements plugin. Special note for psycopg2 (python postgres library): make sure `requirements.txt` lists 'psycopg2-binary', and not 'psycopg2'. This is required for the dependency to run in the lambda environment.

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

* **Sample Calls:**

```python
import requests
sitecode = "saf"
url = f"https://api.photonranch.org/api/events?site={sitecode}"
events = requests.get(url).json()
```

Or to get yesterday's events:

```python
import requests, time
sitecode = "saf"
yesterday = time.time() - 86400 # subtract a day in seconds
url = f"https://api.photonranch.org/api/events?site={sitecode}&when={yesterday}"
events = requests.get(url).json()
```

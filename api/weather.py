import logging
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import random, datetime, json, time, requests
from helpers import _get_secret, http_response, _get_body, DecimalEncoder

log = logging.getLogger()
log.setLevel(logging.INFO)

bucket = _get_secret('influxdb-testbucket')
weather_bucket = _get_secret('influxdb-bucket-weather')
org = _get_secret('influxdb-org') 
token = _get_secret('influxdb-token-serverless_api_fullaccess_token')

client = influxdb_client.InfluxDBClient(
    url="https://us-west-2-1.aws.cloud2.influxdata.com",
    token=token,
    org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


def exampleWrite1(event, context):

    example_record = influxdb_client \
        .Point("weather") \
        .tag("location", "saf") \
        .field("temperature", random.random()*10) \
        .field("wind", random.randint(0,10)) \
        .time(datetime.datetime.utcnow())

    write_api.write(bucket=bucket, org=org, record=example_record)
    return http_response(200, 'success')

def exampleWrite2():
    bucket_name = "weather"
    precision = "s"

    url = f"https://us-west-2-1.aws.cloud2.influxdata.com/api/v2/write"\
        f"?org={org}"\
        f"&bucket={bucket_name}"\
        f"&precision={precision}"

    header = {
        "Authorization": f"Token {token}",
    }

    for i in range(500):
        measurement = "weather"
        tagDict = { "site": "tst" }
        fieldDict = {
            "calc_HSI_lux": "0.002",
            "calc_sky_mpsas": "1.99",
            "dewpoint_C": -5*random.random(),
            "humidity_": random.randint(0,100),
            "last_sky_update_s": "5",
            "meas_sky_mpsas": "1.9",
            "open_ok": True,
            "pressure_mbar": "784.0",
            "rain_rate": "0",
            "sky_temp_C": "-36",
            "solar_flux_w/m^2": "NA",
            "temperature_C": random.randint(-5,25),
            "wind_m/s": random.randint(0,10),
            "wx_ok": "Yes"
        }
        entry_time = int(time.time())
        line_data = _formatLineProtocol(measurement, tagDict, fieldDict, entry_time)
        res = requests.post(url=url, data=line_data, headers=header)
        log.info(f"url: {url}")
        log.info(f"line_data: {line_data}")
        log.info(f"response: {res}")
        time.sleep(10)

def writeWeather(event,context):
    '''
    Write a single weather data entry into the InfluxDB time-series database
    Args:
        event.body.site (str): 3-character site code (eg. "saf")
        event.body.timestamp_s (int): unix timestamp in seconds
        event.body.fieldDict (dict): weather data with correct types (int, float, str, bool)
    '''
    body = _get_body(event)

    site = body["site"]
    fieldDict = body["weatherData"]
    timestamp = body["timestamp_s"]

    bucket_name = "weather"
    precision = "s"

    # HTTP Parameters
    url = f"https://us-west-2-1.aws.cloud2.influxdata.com/api/v2/write"\
        f"?org={org}"\
        f"&bucket={bucket_name}"\
        f"&precision={precision}"
    header = {
        "Authorization": f"Token {token}",
    }

    # We need measurementName, tags, fields, and timestamp for a valid 
    # InfluxDB entry
    measurementName = "weather" # note: not related to the bucket name.
    tagDict = { "site": body["site"] }
    fieldDict = body["weatherData"]
    timestamp = body["timestamp_s"]

    # Create a valid Line Protocol format to send to InfluxDB
    # Docs: https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_reference/
    line_data = _formatLineProtocol(measurementName, tagDict, fieldDict, timestamp)

    # Send the data
    res = requests.post(url=url, data=line_data, headers=header)

    if res.status_code == 204:
        return http_response(200, "Success")
    
    else:
        error_msg = f"Could not write to database. Error code {res.status_code}."
        return http_response(400, error_msg)

def _formatLineProtocol(measurementName, tagDict, fieldDict, timestamp):
    line = measurementName
    for key in tagDict:
        line = f"{line},{key}={tagDict[key]}"
    line += " "
    for key in fieldDict:
        if type(fieldDict[key])==str:
            line = f'{line}{key}="{fieldDict[key]}",'
        else:
            line = f'{line}{key}={fieldDict[key]},'
    line = line[:-1] # remove last trailing comma
    line = f"{line} {timestamp}"
    return line

def weatherGraphQuery(event, context):
    body = _get_body(event)

    time_range = body["time_range"] #ie. '-24h' or '-15m'
    aggregate_window = body["aggregate_window"] #ie. '6m' or '15s'
    measurement_field = body["measurement_field"] #ie. 'temperature_C'
    site = body ["site"]

    query1 = f'from(bucket: "weather")\
    |> range(start: {time_range})\
    |> filter(fn: (r) => r["_measurement"] == "weather")\
    |> filter(fn: (r) => r["_field"] == "{measurement_field}")\
    |> filter(fn: (r) => r["site"] == "{site}")\
    |> aggregateWindow(every: {aggregate_window}, fn: mean)'

    result = query_api.query(org=org, query=query1)
    #results = []
    values = []
    timestamps = []
    field = ''

    for table in result:
        for record in table.records:
            values.append(record.get_value())
            timestamps.append(record.get_time().timestamp())
            if not field: field = record.get_field()
            #results.append([record.get_value(), record.get_field(), record.get_time().timestamp()])

    data = {
        "values": values,
        "timestamps": timestamps,
        "field_name": field
    }
    res = json.dumps(data, cls=DecimalEncoder)
    log.debug(res)
    return http_response(200, res)

def weatherQuery(event, context):
    body = _get_body(event)
    flux_query = body['flux_query']
    result = query_api.query(org=org, query=flux_query)
    results = []

    for table in result:
        for record in table.records:
            results.append([record.get_value(), record.get_field()])


def exampleQuery(event, context):
    query = f'from(bucket:"weather")\
    |> range(start: -48h)\
    |> filter(fn:(r) => r._measurement == "weather")\
    |> filter(fn:(r) => r._field == "wind")'

    result = query_api.query(org=org, query=query)
    results = []

    for table in result:
        for record in table.records:
            results.append([record.get_value(), record.get_field()])

    log.info(results)
    res = json.dumps(results, cls=DecimalEncoder)
    return http_response(200, res)

if __name__=="__main__": 
    import requests
    url = "https://api.photonranch.org/test/weather/write"

    data = json.dumps({
        "weatherData": {
            "calc_HSI_lux": 0.002,
            "calc_sky_mpsas": 1.99,
            "dewpoint_C": -3.3,
            "humidity_%": 50,
            "last_sky_update_s": 5,
            "meas_sky_mpsas": 1.9,
            "open_ok": "Yes",
            "pressure_mbar": 784.0,
            "rain_rate": 0,
            "sky_temp_C": -36,
            "solar_flux_w/m^2": "NA",
            "temperature_C": 25,
            "wind_m/s": 3,
            "wx_ok": "Yes"
        },
        "site": "tst",
        "timestamp_s": int(time.time())
    })

    query = f'from(bucket:"weather")\
    |> range(start: -24h)\
    |> filter(fn:(r) => r._measurement == "weather")\
    |> filter(fn:(r) => r._field == "wind_m/s")\
    |> aggregateWindow(every: 10m, fn: mean)\
    '#|> limit(n: 5)'

    query1 = f'from(bucket: "weather")\
    |> range(start: -24h)\
    |> filter(fn: (r) => r["_measurement"] == "weather")\
    |> filter(fn: (r) => r["_field"] == "temperature_C" or r["_field"] == "wind_m/s")\
    |> filter(fn: (r) => r["site"] == "saf")\
    |> aggregateWindow(every: 2h, fn: mean)'



    #weatherQuery({"body": json.dumps({
        #"time_range": "-24h",
        #"aggregate_window": "60m",
        #"measurement_field": "temperature_C",
        #"site": "saf",
    #})}, {})

    result = query_api.query(org=org, query=query1)
    results = {} 
    for table in result:
        for record in table.records:
            field = record.get_field()
            if not results.get(field, False): 
                results[field] = {
                    "val": [],
                    "time": [],
                }
            results[field]['val'].append(record.get_value())
            results[field]['time'].append(record.get_time().timestamp())

    log.info(json.dumps(results))

import pytest

from skyfield import api, almanac
from skyfield.nutationlib import iau2000b

import datetime, time
from datetime import datetime
import pytz

import events
from legacy_events import Events


@pytest.fixture
def ts():
    '''Get the skyfield timescale for building Time objects'''
    ts = api.load.timescale(builtin=True)
    return ts 

@pytest.fixture
def ok_time_err():
    ''' Define 5 minutes as an acceptable error in event times '''
    return (5/60)/24

def test_get_calibration_frame_durations_structure():
    cal_frame_durations = events._get_calibration_frame_durations()
    required_keys = set(["screen_flat_duration", 
                       "bias_dark_duration", 
                       "morn_bias_dark_duration",
                       "longest_screen",
                       "longest_dark"])
    assert set(cal_frame_durations.keys()) == required_keys

def test_add_time_positive(ts):
    julian_date = 2458800
    time_obj = ts.tai_jd(julian_date)
    assert events._add_time(time_obj, 1).tai == julian_date + 1

def test_add_time_negative(ts):
    julian_date = 2458800
    time_obj = ts.tai_jd(julian_date)
    assert events._add_time(time_obj, -1).tai == julian_date - 1

def test_sort_dict_of_time_objects(ts):
    # Create dicts of Skyfield time objects
    unsorted_dict = {
        "two": ts.tai_jd(2),
        "three": ts.tai_jd(3),
        "one": ts.tai_jd(1),
    }
    sorted_dict = {
        "one": ts.tai_jd(1),
        "two": ts.tai_jd(2),
        "three": ts.tai_jd(3),
    }
    assert events._sort_dict_of_time_objects(unsorted_dict).keys() == sorted_dict.keys()

def test_build_site_context_structure():
    args = {
        "lat": 34,
        "lng": -119,
        "time": 2458800,
    }
    site_context = events._build_site_context(**args)
    required_keys = set(["eph", 
                       "observatory", 
                       "day_end",
                       "day_start"
    ])
    assert set(site_context.keys()) == required_keys

def test_get_tz_offset_withDST():
    timezone = 'America/Los_Angeles'
    offset_when = datetime(2020,6,1).timestamp()
    offset_solution_with_dst = -7
    assert events._get_tz_offset(timezone, offset_when) == offset_solution_with_dst

def test_get_tz_offset_no_DST():
    timezone = 'America/Los_Angeles'
    offset_when = datetime(2020,1,1).timestamp()
    offset_solution_no_dst = -8
    assert events._get_tz_offset(timezone, offset_when) == offset_solution_no_dst
def test_get_tz_offset_no_DST_2():
    timezone = 'Australia/Perth'
    offsetWhen = datetime(2020,1,1).timestamp()
    offset_solution_no_dst = 8
    assert events._get_tz_offset(timezone, offsetWhen) == offset_solution_no_dst

def test_get_local_noon_1159(ts):
    tz_name="Australia/Perth"
    tz = pytz.timezone(tz_name)
    time = tz.localize(datetime(2020, 6, 5, 11, 59)).timestamp()
    local_noon = ts.tai_jd(events._get_local_noon(tz_name, time))
    assert local_noon.tai_calendar()[2] == 4 # should be previous calendar day

def test_get_local_noon_1200(ts):
    tz_name="Australia/Perth"
    tz = pytz.timezone(tz_name)
    time = tz.localize(datetime(2020, 6, 5, 12 )).timestamp()
    local_noon = ts.tai_jd(events._get_local_noon(tz_name, time))
    assert local_noon.tai_calendar()[2] == 5 # should keep same calendar day

def test_get_rise_set_times(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 19, 56)))
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 6, 8)))

    site_context = events._build_site_context(34, -119, start, timezone="America/Los_Angeles")
    horizon_angle = 0.5 # half degree sun diameter
    rise_set_times = events.get_rise_set_times(site_context, horizon_angle)

    # difference between calculated and actual
    rise_err = abs(rise_set_times[0].tai - rise_time.tai)
    set_err = abs(rise_set_times[1].tai - set_time.tai)
    print(rise_err, set_err)
    assert rise_err < ok_time_err and set_err < ok_time_err

def test_get_rise_set_times_2(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz_name = 'Australia/Perth'
    tz = pytz.timezone(tz_name)

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 17, 24)))
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 6, 55)))

    site_context = events._build_site_context(-34, 119, start, timezone=tz_name)
    horizon_angle = 0.5 # half degree sun diameter
    riseSetTimes = events.get_rise_set_times(site_context, horizon_angle)

    # difference between calculated and actual
    rise_err = abs(riseSetTimes[0].tai - rise_time.tai)
    set_err = abs(riseSetTimes[1].tai - set_time.tai)
    print(rise_err, set_err)
    assert rise_err < ok_time_err and set_err < ok_time_err

def test_calc_flat_vals_1(ts): 
    # calcMornFlatValues

    # Acceptable threshold: 1 hour
    # Justification: this is not a high precision task. Significant errors
    # will produce an error greater than this anyways. 
    threshold = 1

    # Values acquired from Wayne's code
    tz_name = 'America/Los_Angeles'
    tz = pytz.timezone(tz_name)
    startTime = tz.localize(datetime(2020, 8, 10, 17, 55)).timestamp()
    site_context = events._build_site_context(34,-119, startTime, timezone=tz_name)
    flat_start_ra = 1.4729577575946526
    flat_start_dec = 32.471636109223944
    flat_end_ra = 1.5794818193745246
    flat_end_dec = 28.236392134703863
    ra_dot = 1.7587
    dec_dot = -4.6616

    t0 = ts.tai_jd(2415020 + 44053.01140300775) # morn_skyFlatBegin
    t1 = ts.tai_jd(2415020 + 44053.0492590291) # sunrise

    flat_vals = events.calc_flat_vals(site_context, t0, t1)
    print(flat_vals)

    assert abs(flat_vals['flat_start_ra'] - flat_start_ra) < threshold
    assert abs(flat_vals['flat_start_dec'] - flat_start_dec) < threshold
    assert abs(flat_vals['flat_end_ra'] - flat_end_ra) < threshold
    assert abs(flat_vals['flat_end_dec'] - flat_end_dec) < threshold

def test_calc_flat_vals_2(ts): 
    # calcEveFlatValues

    # Acceptable threshold: 1 hour
    # Justification: this is not a high precision task. Significant errors
    # will produce an error greater than this anyways. 
    threshold = 1

    # Values acquired from Wayne's code
    tz_name = 'America/Los_Angeles'
    tz = pytz.timezone(tz_name)
    start_time = tz.localize(datetime(2020, 8, 10, 13, 45)).timestamp()
    site_context = events._build_site_context(34,-119, start_time, timezone=tz_name)
    flat_start_ra = 17.104991872570437
    flat_start_dec = 25.784461955928407
    flat_end_ra = 17.372109786045947
    flat_end_dec = 32.583239202840886
    ra_dot = 2.0996
    dec_dot = 3.5626

    t0 = ts.tai_jd(2415020 + 44052.5776083735) # ops_win_begin
    t1 = ts.tai_jd(2415020 + 44052.657123179306) # eve_skyFlatEnd

    flat_vals = events.calc_flat_vals(site_context, t0, t1)

    assert abs(flat_vals['flat_start_ra'] - flat_start_ra) < threshold
    assert abs(flat_vals['flat_start_dec'] - flat_start_dec) < threshold
    assert abs(flat_vals['flat_end_ra'] - flat_end_ra) < threshold
    assert abs(flat_vals['flat_end_dec'] - flat_end_dec) < threshold

def test_get_moon_events_1(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 18, 53)))
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 4, 58)))

    site_context = events._build_site_context(34, -119, start, timezone="America/Los_Angeles")
    moon_events = events.get_moon_events(site_context)

    # difference between calculated and actual
    rise_err = abs(moon_events['moonrise'].tai - rise_time.tai)
    set_err = abs(moon_events['moonset'].tai - set_time.tai)
    assert rise_err < ok_time_err and set_err < ok_time_err

def test_get_moon_events_2(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2025, 12, 1, 12, 1)).timestamp()
    rise_time = ts.from_datetime(tz.localize(datetime(2025, 12, 1, 14, 10)))
    set_time = ts.from_datetime(tz.localize(datetime(2025, 12, 2, 4, 3)))

    site_context = events._build_site_context(34, -119, start, timezone="America/Los_Angeles")
    moon_events = events.get_moon_events(site_context)

    # difference between calculated and actual
    rise_err = abs(moon_events['moonrise'].tai - rise_time.tai)
    set_err = abs(moon_events['moonset'].tai - set_time.tai)
    assert rise_err < ok_time_err and set_err < ok_time_err

def test_make_site_events():
    required_keys = set(["Eve Bias Dark", 
                       "End Eve Bias Dark", 
                       "Eve Scrn Flats",
                       "End Eve Scrn Flats",
                       "Ops Window Start",
                       "Observing Begins",
                       "Observing Ends",
                       "Cool Down, Open",
                       "Eve Sky Flats",
                       "Sun Set",
                       "Civil Dusk",
                       "End Eve Sky Flats",
                       "Clock & Auto Focus",
                       "Naut Dusk",
                       "Astro Dark",
                       "Middle of Night",
                       "End Astro Dark",
                       "Final Clock & Auto Focus",
                       "Naut Dawn",
                       "Morn Sky Flats",
                       "Civil Dawn",
                       "End Morn Sky Flats",
                       "Ops Window Closes",
                       "Sunrise",
                       ])
    now = time.time()
    timezone = 'America/Los_Angeles'
    site_events = events.make_site_events(34, -119, now, timezone)
    assert required_keys.issubset(set(site_events.keys()))

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

def test_getCalibrationFrameDurations_structure():
    calFrameDurations = events._getCalibrationFrameDurations()
    requiredKeys = set(["screenFlatDuration", 
                       "biasDarkDuration", 
                       "mornBiasDarkDuration",
                       "longestScreen",
                       "longestDark"])
    assert set(calFrameDurations.keys()) == requiredKeys

def test_addTime_positive(ts):
    julian_date = 2458800
    time_obj = ts.tai_jd(julian_date)
    assert events._addTime(time_obj, 1).tai == julian_date + 1

def test_addTime_negative(ts):
    julian_date = 2458800
    time_obj = ts.tai_jd(julian_date)
    assert events._addTime(time_obj, -1).tai == julian_date - 1

def test_sortDictOfTimeObjects(ts):
    # Create dicts of Skyfield time objects
    unsortedDict = {
        "two": ts.tai_jd(2),
        "three": ts.tai_jd(3),
        "one": ts.tai_jd(1),
    }
    sortedDict = {
        "one": ts.tai_jd(1),
        "two": ts.tai_jd(2),
        "three": ts.tai_jd(3),
    }
    assert events._sortDictOfTimeObjects(unsortedDict).keys() == sortedDict.keys()

def test_buildSiteContext_structure():
    args = {
        "lat": 34,
        "lng": -119,
        "time": 2458800,
    }
    siteContext = events._buildSiteContext(**args)
    requiredKeys = set(["eph", 
                       "observatory", 
                       "dayEnd",
                       "dayStart"
    ])
    assert set(siteContext.keys()) == requiredKeys

def test_getTzOffset_withDST():
    timezone = 'America/Los_Angeles'
    offsetWhen = datetime(2020,6,1).timestamp()
    offsetSolutionWithDST = -7
    assert events._getTzOffset(timezone, offsetWhen) == offsetSolutionWithDST

def test_getTzOffset_noDST():
    timezone = 'America/Los_Angeles'
    offsetWhen = datetime(2020,1,1).timestamp()
    offsetSolutionNoDST = -8
    assert events._getTzOffset(timezone, offsetWhen) == offsetSolutionNoDST
def test_getTzOffset_noDST2():
    timezone = 'Australia/Perth'
    offsetWhen = datetime(2020,1,1).timestamp()
    offsetSolutionNoDST = 8
    assert events._getTzOffset(timezone, offsetWhen) == offsetSolutionNoDST

def test_getLocalNoon_1159(ts):
    tzName="Australia/Perth"
    tz = pytz.timezone(tzName)
    time = tz.localize(datetime(2020, 6, 5, 11, 59)).timestamp()
    localNoon = ts.tai_jd(events._getLocalNoon(tzName, time))
    assert localNoon.tai_calendar()[2] == 4 # should be previous calendar day

def test_getLocalNoon_1200(ts):
    tzName="Australia/Perth"
    tz = pytz.timezone(tzName)
    time = tz.localize(datetime(2020, 6, 5, 12 )).timestamp()
    localNoon = ts.tai_jd(events._getLocalNoon(tzName, time))
    assert localNoon.tai_calendar()[2] == 5 # should keep same calendar day

#def test_daylength():
    #assert False

def test_getRiseSetTimes(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 19, 56)))
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 6, 8)))

    siteContext = events._buildSiteContext(34, -119, start, timezone="America/Los_Angeles")
    horizonAngle = 0.5 # half degree sun diameter
    riseSetTimes = events.getRiseSetTimes(siteContext, horizonAngle)

    # difference between calculated and actual
    riseErr = abs(riseSetTimes[0].tai - rise_time.tai)
    setErr = abs(riseSetTimes[1].tai - set_time.tai)
    print(riseErr, setErr)
    assert riseErr < ok_time_err and setErr < ok_time_err

def test_getRiseSetTimes_2(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tzName = 'Australia/Perth'
    tz = pytz.timezone(tzName)

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 17, 24)))
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 6, 55)))

    siteContext = events._buildSiteContext(-34, 119, start, timezone=tzName)
    horizonAngle = 0.5 # half degree sun diameter
    riseSetTimes = events.getRiseSetTimes(siteContext, horizonAngle)

    # difference between calculated and actual
    riseErr = abs(riseSetTimes[0].tai - rise_time.tai)
    setErr = abs(riseSetTimes[1].tai - set_time.tai)
    print(riseErr, setErr)
    assert riseErr < ok_time_err and setErr < ok_time_err

def test_calcFlatVals_1(ts): 
    # calcMornFlatValues

    # Acceptable threshold: 1 hour
    # Justification: this is not a high precision task. Significant errors
    # will produce an error greater than this anyways. 
    threshold = 1

    # Values acquired from Wayne's code
    tzName = 'America/Los_Angeles'
    tz = pytz.timezone(tzName)
    startTime = tz.localize(datetime(2020, 8, 10, 17, 55)).timestamp()
    siteContext = events._buildSiteContext(34,-119, startTime, timezone=tzName)
    flatStartRa = 1.4729577575946526
    flatStartDec = 32.471636109223944
    flatEndRa = 1.5794818193745246
    flatEndDec = 28.236392134703863
    raDot = 1.7587
    decDot = -4.6616

    t0 = ts.tai_jd(2415020 + 44053.01140300775) # morn_skyFlatBegin
    t1 = ts.tai_jd(2415020 + 44053.0492590291) # sunrise

    flatVals = events.calcFlatVals(siteContext, t0, t1)
    print(flatVals)

    assert abs(flatVals['flatStartRa'] - flatStartRa) < threshold
    assert abs(flatVals['flatStartDec'] - flatStartDec) < threshold
    assert abs(flatVals['flatEndRa'] - flatEndRa) < threshold
    assert abs(flatVals['flatEndDec'] - flatEndDec) < threshold
    #assert abs(flatVals['raDot'] - raDot) < threshold
    #assert abs(flatVals['decDot'] - decDot) < threshold

def test_calcFlatVals_2(ts): 
    # calcEveFlatValues

    # Acceptable threshold: 1 hour
    # Justification: this is not a high precision task. Significant errors
    # will produce an error greater than this anyways. 
    threshold = 1

    # Values acquired from Wayne's code
    tzName = 'America/Los_Angeles'
    tz = pytz.timezone(tzName)
    startTime = tz.localize(datetime(2020, 8, 10, 13, 45)).timestamp()
    siteContext = events._buildSiteContext(34,-119, startTime, timezone=tzName)
    flatStartRa = 17.104991872570437
    flatStartDec = 25.784461955928407
    flatEndRa = 17.372109786045947
    flatEndDec = 32.583239202840886
    raDot = 2.0996
    decDot = 3.5626

    t0 = ts.tai_jd(2415020 + 44052.5776083735) # ops_win_begin
    t1 = ts.tai_jd(2415020 + 44052.657123179306) # eve_skyFlatEnd

    flatVals = events.calcFlatVals(siteContext, t0, t1)

    assert abs(flatVals['flatStartRa'] - flatStartRa) < threshold
    assert abs(flatVals['flatStartDec'] - flatStartDec) < threshold
    assert abs(flatVals['flatEndRa'] - flatEndRa) < threshold
    assert abs(flatVals['flatEndDec'] - flatEndDec) < threshold
    #assert abs(flatVals['raDot'] - raDot) < threshold
    #assert abs(flatVals['decDot'] - decDot) < threshold

def test_getMoonEvents_1(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2020, 8, 1, 12, 1)).timestamp()
    rise_time = ts.from_datetime(tz.localize(datetime(2020, 8, 1, 18, 53)))
    set_time = ts.from_datetime(tz.localize(datetime(2020, 8, 2, 4, 58)))

    siteContext = events._buildSiteContext(34, -119, start, timezone="America/Los_Angeles")
    moonEvents = events.getMoonEvents(siteContext)

    # difference between calculated and actual
    riseErr = abs(moonEvents['moonRise'].tai - rise_time.tai)
    setErr = abs(moonEvents['moonSet'].tai - set_time.tai)
    assert riseErr < ok_time_err and setErr < ok_time_err

def test_getMoonEvents_2(ts, ok_time_err):
    # Test cases from https://www.timeanddate.com/moon/@34,-119
    tz = pytz.timezone('America/Los_Angeles')

    # Rise and set times for 24 hr span of local noon-noon
    start = tz.localize(datetime(2025, 12, 1, 12, 1)).timestamp()
    rise_time = ts.from_datetime(tz.localize(datetime(2025, 12, 1, 14, 10)))
    set_time = ts.from_datetime(tz.localize(datetime(2025, 12, 2, 4, 3)))

    siteContext = events._buildSiteContext(34, -119, start, timezone="America/Los_Angeles")
    moonEvents = events.getMoonEvents(siteContext)

    # difference between calculated and actual
    riseErr = abs(moonEvents['moonRise'].tai - rise_time.tai)
    setErr = abs(moonEvents['moonSet'].tai - set_time.tai)
    assert riseErr < ok_time_err and setErr < ok_time_err

def test_makeSiteEvents():
    requiredKeys = set(["Eve Bias Dark", 
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
    siteEvents = events.makeSiteEvents(34, -119, now, timezone)
    assert requiredKeys.issubset(set(siteEvents.keys()))
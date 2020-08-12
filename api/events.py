import skyfield
from skyfield import api, almanac
from skyfield.nutationlib import iau2000b

from datetime import datetime, timezone
import time
import pytz

from legacy_events import Events

def _getCalibrationFrameDurations():
    # Get these from config eventually
    return {
        "screenFlatDuration": 1.5/24,
        "biasDarkDuration": 8/24,
        "mornBiasDarkDuration": (1.5/60)/24,
        "longestScreen": (75/60)/1440,
        "longestDark": (385/60)/1440,
    }

def _addTime(timeObject, days:float):
    '''Return the skyfield Time object plus some number of days.'''
    ts = api.load.timescale(builtin=True)
    return ts.tai_jd(timeObject.tai + days)

def _sortDictOfTimeObjects(unsorted):
    '''Return dict with keys sorted according to the order of their time values.

    Though python dicts do not explicitly support order, they are typically 
    printed with the same order that keys were added. This method simply makes
    the dict print nicely on most systems.

    Args:
        unsorted(dict): dict where all values are skyfield time objects.

    Returns:
        dict: same keys and values as input, but ordered by increasing time value.
    '''
    unsortedList = [(x, unsorted[x]) for x in unsorted]
    sortedList = sorted(unsortedList, key=lambda x: x[1].tai)
    sortedDict = {}
    for i in sortedList:
        sortedDict[i[0]] = i[1]
    return sortedDict

def _buildSiteContext(lat:float, lng:float, time:float, timezone='America/Los_Angeles'):
    '''Return the geo information specific to the observatory.

    This information is used in many of the site-events-related functions.

    Args:
        lat (float): latitude in deg N
        lng (float): longitude in deg E
        time (float): unix time in s
        timezone (str): tz database timezone name (ie. 'America/Los_Angeles')

    Returns: 
        dict: skyfield objects for the start/end of day times, observatory, and 
                ephemeris file. 
    '''

    ts = api.load.timescale(builtin=True)
    eph = api.load('de421.bsp')

    time = _getLocalNoon(timezone,time)

    t0 = ts.tai_jd(time)
    t1 = ts.tai_jd(time + 1)
    observatory = api.Topos(latitude_degrees=lat, longitude_degrees=lng)
    siteContext = {
        "dayStart": t0,
        "dayEnd": t1,
        "observatory": observatory,
        "eph": eph
    }
    return siteContext

def _getTzOffset(timezone:str, timestamp:float) -> float:
    '''Gets the current UTC offset (hours) for the given timezone.
    
    Args:
        timezone (str): timezone name, ie. 'America/Los_Angeles'
        timestamp (float): unix time (s) defining when the offset is applied.
            Note: this determines whether to include daylight savings time.

    Returns:
        float: hours (+ or -) from UTC time
    ''' 
    tz = pytz.timezone(timezone)
    utc_offset = datetime.fromtimestamp(timestamp, tz=tz).utcoffset()
    offset = ((utc_offset.days * 86400) + (utc_offset.seconds)) / 3600
    return offset

def _getLocalNoon(timezone:str, time:float) -> float:
    '''Gets the local noon preceeding the given time, in julian days 
    
    May show unexpected behavior around DST transitions.

    Args:
        timezone (str): timezone name, ie. 'America/Los_Angeles'
        time (float): unix time in seconds

    Returns:
        float: TAI in julian days denoting local noon.
    '''
    ts = api.load.timescale(builtin=True)
    #unix_time = ts.tai_jd(time).utc_datetime().timestamp()
    timeObj = ts.from_datetime(datetime.fromtimestamp(time, tz=pytz.timezone('utc')))
    offset_days = _getTzOffset(timezone, time) / 24
    localNoon = int(timeObj.tai + offset_days) - offset_days
    return localNoon

def daylength(ephemeris, topos, degrees):
    """Build a function of time that returns the daylength.

    The function that this returns will expect a single argument that is a 
    :class:`~skyfield.timelib.Time` and will return ``True`` if the sun is up
    or twilight has started, else ``False``.
    """
    sun = ephemeris['sun']
    topos_at = (ephemeris['earth'] + topos).at

    def is_sun_up_at(t):
        """Return `True` if the sun has risen by time `t`."""
        t._nutation_angles = iau2000b(t.tt)
        return topos_at(t).observe(sun).apparent().altaz()[0].degrees > -degrees

    is_sun_up_at.rough_period = 0.5  # twice a day
    return is_sun_up_at

def getRiseSetTimes(siteContext, horizonAngle=0):

    riseSet, isRise = almanac.find_discrete(
        siteContext['dayStart'],
        siteContext['dayEnd'],
        daylength(siteContext['eph'], siteContext['observatory'], horizonAngle)
    )
    
    riseSetList = list(riseSet)

    # order list so rise comes before set. 
    if isRise[1]: riseSetList.reverse()
    return riseSetList

def calcFlatVals(siteContext, t0, t1):
    '''Get the flattest spots in the sky.

    Args:
        siteContext: dict containing site information. See _buildSiteContext().
        t0 (skyfield time obj): time for calculating the starting flat spot.
        t1 (skyfield time obj): time for calculatign the end flat spot. 

    Returns:
        dict: flat start/end ra/dec values, with ra in hours an dec in deg. 
    '''
    eph = api.load('de421.bsp')
    sun, earth = eph['sun'], eph['earth']

    obs = earth + siteContext['observatory']

    sun_alt_0, sun_az_0, _ = obs.at(t0).observe(sun).apparent().altaz()
    sun_az_0 = sun_az_0.degrees
    sun_alt_0 = sun_alt_0.degrees + 105
    if sun_alt_0 > 90:
        sun_alt_0 = 180 - sun_alt_0
        sun_az_0 -= 180
    
    flat_start = obs.at(t0).from_altaz(alt_degrees=sun_alt_0, az_degrees=sun_az_0)
    flat_start_ra, flat_start_dec, _ = flat_start.radec()

    sun_alt_1, sun_az_1, _ = obs.at(t1).observe(sun).apparent().altaz()
    sun_az_1 = sun_az_1.degrees
    sun_alt_1 = sun_alt_1.degrees + 105
    if sun_alt_1 > 90:
        sun_alt_1 = 180 - sun_alt_1
        sun_az_1 -= 180

    flat_end = obs.at(t1).from_altaz(alt_degrees=sun_alt_1, az_degrees=sun_az_1)
    flat_end_ra, flat_end_dec, _ = flat_end.radec()

    span = 24 * (t1.tai - t0.tai) # duration in hours
    ra_dot = round((flat_end_ra._degrees - flat_start_ra._degrees) / span, 4)
    dec_dot = round((flat_end_dec._degrees - flat_start_dec._degrees) / span, 4)

    flatVals = {
        "flatStartRa": flat_start_ra.hours,
        "flatStartDec": flat_start_dec._degrees,
        "flatEndRa": flat_end_ra.hours,
        "flatEndDec": flat_end_dec._degrees,
        "raDot": ra_dot,
        "decDot": dec_dot,
    }
    return flatVals

def getMoonEvents(siteContext):

    t0 = siteContext['dayStart']
    t1 = siteContext['dayEnd']
    eph = siteContext['eph']
    moon = eph['Moon']

    f = almanac.risings_and_settings(eph, moon, siteContext['observatory'])
    times, isRise = almanac.find_discrete(t0, t1, f)

    moonEvents = {}
    for t, r in zip(times, isRise):
        if r:
            moonEvents['moonRise'] = t
        else:
            moonEvents['moonSet'] = t

    return moonEvents

def makeSiteEvents(lat:float, lng:float, time:float, timezone:str) -> dict:
    ''' Compile all the events in to a single dictionary.

    Args:
        lat (float): site latitude in deg N
        lng (float): site longitude in deg E
        time (float): unix timestamp within the 24hr block (local noon-noon) 
            when we want to get events.
        timezone (str): tz database timezone name (ie. 'America/Los_Angeles')

    Returns:
        dict: event name as key, tai julian days (float) as value. 
    '''

    site_context = _buildSiteContext(lat, lng, time, timezone)

    cal_frame_durations = _getCalibrationFrameDurations()
    screen_flat_duration = cal_frame_durations['screenFlatDuration']
    bias_dark_duration = cal_frame_durations['biasDarkDuration']
    morn_bias_dark_duration = cal_frame_durations['mornBiasDarkDuration']
    longest_screen = cal_frame_durations['longestScreen']
    longest_dark = cal_frame_durations['longestDark']

    sunrise, sunset = getRiseSetTimes(site_context, 0.25)
    civil_dawn, civil_dusk = getRiseSetTimes(site_context, 6)
    nautical_dawn, nautical_dusk = getRiseSetTimes(site_context, 12)
    astro_dawn, astro_dusk = getRiseSetTimes(site_context, 18)

    ops_win_begin = _addTime(sunset, -1/24)

    # Skyflat Times
    morn_sky_flat_end, _ = getRiseSetTimes(site_context, 1.5)
    eve_sky_flat_begin = _addTime(sunset, -0.5/24)
    morn_sky_flat_begin, eve_sky_flat_end = getRiseSetTimes(site_context, 11.75)

    morn_flat_vals = calcFlatVals(site_context, ops_win_begin, eve_sky_flat_end)
    eve_flat_vals = calcFlatVals(site_context, morn_sky_flat_begin, sunrise)

    end_eve_screenflats = _addTime(ops_win_begin, -longest_screen)
    begin_eve_screenflats = _addTime(end_eve_screenflats, -screen_flat_duration)
    end_eve_bias_dark = _addTime(begin_eve_screenflats, -longest_dark)
    begin_eve_bias_dark = _addTime(end_eve_bias_dark, -bias_dark_duration)

    begin_morn_screenflats = _addTime(sunrise, 4/1440)
    end_morn_screenflats = _addTime(begin_morn_screenflats, screen_flat_duration)
    begin_morn_bias_dark = _addTime(end_morn_screenflats, longest_screen)
    end_morn_bias_dark = _addTime(begin_morn_bias_dark, morn_bias_dark_duration)
    begin_reductions = _addTime(end_morn_bias_dark, longest_dark)

    observing_begins = _addTime(nautical_dusk, 5/1440)
    observing_ends = _addTime(nautical_dawn, -5/1440)

    moon_events = getMoonEvents(site_context)

    midnight = _addTime(sunset, 0.5 * (sunrise.tai - sunset.tai))  

    siteEvents = {

        "Eve Bias Dark": begin_eve_bias_dark,
        "End Eve Bias Dark": end_eve_bias_dark,
        "Eve Scrn Flats": begin_eve_screenflats,
        "End Eve Scrn Flats": end_eve_screenflats,

        "Ops Window Start": ops_win_begin,

        "Observing Begins": observing_begins,
        "Observing Ends": observing_ends,

        "Cool Down, Open": _addTime(ops_win_begin, 0.5/1440),

        "Eve Sky Flats": eve_sky_flat_begin,
        "Sun Set": sunset,
        "Civil Dusk": civil_dusk,
        "End Eve Sky Flats": eve_sky_flat_end,
        "Clock & Auto Focus": _addTime(eve_sky_flat_end, 1/1440),
        "Naut Dusk": nautical_dusk,
        
        "Astro Dark": astro_dusk,
        
        "Middle of Night": midnight,

        "End Astro Dark": astro_dawn,
        "Final Clock & Auto Focus": _addTime(nautical_dawn, -4/1440),
        "Naut Dawn": nautical_dawn,
        "Morn Sky Flats": morn_sky_flat_begin,
        "Civil Dawn": civil_dawn,
        "End Morn Sky Flats": morn_sky_flat_end,
        "Ops Window Closes": _addTime(morn_sky_flat_end, 0.5/1440), # margin time to close
        "Sunrise": sunrise,
    }

    # Add these events conditionally because they might not exist.
    if 'moonRise' in moon_events:
        siteEvents['Moon Rise'] = moon_events['moonRise']
    if 'moonSet' in moon_events:
        siteEvents['Moon Set'] = moon_events['moonSet']

    siteEvents = _sortDictOfTimeObjects(siteEvents)

    # Convert all times to TAI julian days
    siteEvents = {k:t.tai for k, t in siteEvents.items()}


    #for i in siteEvents:
        #print(i,(25-len(i))*' ','\t', siteEvents[i].astimezone(pytz.timezone('America/Los_Angeles')))

    return siteEvents

if __name__=="__main__":

    ts = api.load.timescale(builtin=True)
    print(_getLocalNoon('America/Los_Angeles', time.time()))
    #_getTwilightTimes(34, -119, ts.now().tai)
    makeSiteEvents(34, -119, time.time())
    e = Events(34, -119, 0,0,0)
    e.display_events()
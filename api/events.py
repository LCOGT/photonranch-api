import skyfield
from skyfield import api, almanac
from skyfield.nutationlib import iau2000b

from datetime import datetime, timezone
import time
import pytz

from legacy_events import Events


def _get_calibration_frame_durations():

    # Get these from config eventually
    return {
        "screen_flat_duration": 1.5/24,
        "bias_dark_duration": 8/24,
        "morn_bias_dark_duration": (1.5/60)/24,
        "longest_screen": (75/60)/1440,
        "longest_dark": (385/60)/1440,
    }


def _add_time(timeObject, days: float):
    '''Return the skyfield Time object plus some number of days.'''
    timescale = api.load.timescale(builtin=True)
    return timescale.tai_jd(timeObject.tai + days)


def _sort_dict_of_time_objects(unsorted):
    '''Return dict with items sorted by the order of their time values.

    Though python dicts do not explicitly support order, they are typically
    printed with the same order that keys were added. This method simply makes
    the dict print nicely on most systems.

    Args:
        unsorted(dict): dict where all values are skyfield time objects.

    Returns:
        dict: same keys and values as input, but ordered by increasing
            time value.
    '''
    unsortedList = [(x, unsorted[x]) for x in unsorted]
    sortedList = sorted(unsortedList, key=lambda x: x[1].tai)
    sortedDict = {}
    for item in sortedList:
        sortedDict[item[0]] = item[1]
    return sortedDict


def _build_site_context(lat: float, lng: float, time: float, timezone: str):
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

    timescale = api.load.timescale(builtin=True)
    eph = api.load('de421.bsp')

    time = _get_local_noon(timezone, time)

    t0 = timescale.tai_jd(time)
    t1 = timescale.tai_jd(time + 1)
    observatory = api.Topos(latitude_degrees=lat, longitude_degrees=lng)
    site_context = {
        "day_start": t0,
        "day_end": t1,
        "observatory": observatory,
        "eph": eph
    }
    return site_context


def _get_tz_offset(timezone: str, timestamp: float) -> float:
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


def _get_local_noon(timezone: str, time: float) -> float:
    '''Gets the local noon preceeding the given time, in julian days

    May show unexpected behavior around DST transitions.

    Args:
        timezone (str): timezone name, ie. 'America/Los_Angeles'
        time (float): unix time in seconds

    Returns:
        float: TAI in julian days denoting local noon.
    '''
    ts = api.load.timescale(builtin=True)
    utc_timezone = pytz.timezone('utc')
    time_obj = ts.from_datetime(datetime.fromtimestamp(time, tz=utc_timezone))
    offset_days = _get_tz_offset(timezone, time) / 24
    local_noon = int(time_obj.tai + offset_days) - offset_days
    return local_noon


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


def get_rise_set_times(site_context, horizonAngle=0):

    rise_set, is_rise = almanac.find_discrete(
        site_context['day_start'],
        site_context['day_end'],
        daylength(site_context['eph'], site_context['observatory'],
                  horizonAngle)
    )
    rise_set_list = list(rise_set)

    # order list so rise comes before set.
    if is_rise[1]:
        rise_set_list.reverse()

    return rise_set_list


def calc_flat_vals(site_context, t0, t1):
    '''Get the flattest spots in the sky.

    Args:
        site_context: dict with site information. See _build_site_context().
        t0 (skyfield time obj): time for calculating the starting flat spot.
        t1 (skyfield time obj): time for calculatign the end flat spot.

    Returns:
        dict: flat start/end ra/dec values, with ra in hours an dec in deg.
    '''
    eph = api.load('de421.bsp')
    sun, earth = eph['sun'], eph['earth']

    obs = earth + site_context['observatory']

    sun_alt_0, sun_az_0, _ = obs.at(t0).observe(sun).apparent().altaz()
    sun_az_0 = sun_az_0.degrees
    sun_alt_0 = sun_alt_0.degrees + 105
    if sun_alt_0 > 90:
        sun_alt_0 = 180 - sun_alt_0
        sun_az_0 -= 180

    flat_start = obs.at(t0).from_altaz(alt_degrees=sun_alt_0,
                                       az_degrees=sun_az_0)
    flat_start_ra, flat_start_dec, _ = flat_start.radec()

    sun_alt_1, sun_az_1, _ = obs.at(t1).observe(sun).apparent().altaz()
    sun_az_1 = sun_az_1.degrees
    sun_alt_1 = sun_alt_1.degrees + 105
    if sun_alt_1 > 90:
        sun_alt_1 = 180 - sun_alt_1
        sun_az_1 -= 180

    flat_end = obs.at(t1).from_altaz(alt_degrees=sun_alt_1,
                                     az_degrees=sun_az_1)
    flat_end_ra, flat_end_dec, _ = flat_end.radec()

    span = 24 * (t1.tai - t0.tai)  # duration in hours
    ra_dot = round((flat_end_ra._degrees - flat_start_ra._degrees) / span, 4)
    dec_dot = round((flat_end_dec._degrees - flat_start_dec._degrees) / span, 4)

    flat_vals = {
        "flat_start_ra": flat_start_ra.hours,
        "flat_start_dec": flat_start_dec._degrees,
        "flat_end_ra": flat_end_ra.hours,
        "flat_end_dec": flat_end_dec._degrees,
        "ra_dot": ra_dot,
        "dec_dot": dec_dot,
    }
    return flat_vals


def get_moon_events(site_context):

    t0 = site_context['day_start']
    t1 = site_context['day_end']
    eph = site_context['eph']
    moon = eph['Moon']

    f = almanac.risings_and_settings(eph, moon, site_context['observatory'])
    times, is_rise = almanac.find_discrete(t0, t1, f)

    moon_events = {}
    for t, r in zip(times, is_rise):
        if r:
            moon_events['moonrise'] = t
        else:
            moon_events['moonset'] = t

    return moon_events


def make_site_events(lat: float, lng: float, time: float, timezone: str):
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

    site_context = _build_site_context(lat, lng, time, timezone)

    cal_frame_durations = _get_calibration_frame_durations()
    screen_flat_duration = cal_frame_durations['screen_flat_duration']
    bias_dark_duration = cal_frame_durations['bias_dark_duration']
    morn_bias_dark_duration = cal_frame_durations['morn_bias_dark_duration']
    longest_screen = cal_frame_durations['longest_screen']
    longest_dark = cal_frame_durations['longest_dark']

    sunrise, sunset = get_rise_set_times(site_context, 0.25)
    civil_dawn, civil_dusk = get_rise_set_times(site_context, 6)
    nautical_dawn, nautical_dusk = get_rise_set_times(site_context, 12)
    astro_dawn, astro_dusk = get_rise_set_times(site_context, 18)

    ops_win_begin = _add_time(sunset, -1/24)

    # Skyflat Times
    morn_sky_flat_end, _ = get_rise_set_times(site_context, 1.5)
    eve_sky_flat_begin = _add_time(sunset, -0.5/24)
    morn_sky_flat_begin, eve_sky_flat_end = get_rise_set_times(site_context, 11.75)

    morn_flat_vals = calc_flat_vals(site_context, ops_win_begin, eve_sky_flat_end)
    eve_flat_vals = calc_flat_vals(site_context, morn_sky_flat_begin, sunrise)

    end_eve_screenflats = _add_time(ops_win_begin, -longest_screen)
    begin_eve_screenflats = _add_time(end_eve_screenflats, -screen_flat_duration)
    end_eve_bias_dark = _add_time(begin_eve_screenflats, -longest_dark)
    begin_eve_bias_dark = _add_time(end_eve_bias_dark, -bias_dark_duration)

    begin_morn_screenflats = _add_time(sunrise, 4/1440)
    end_morn_screenflats = _add_time(begin_morn_screenflats, screen_flat_duration)
    begin_morn_bias_dark = _add_time(end_morn_screenflats, longest_screen)
    end_morn_bias_dark = _add_time(begin_morn_bias_dark, morn_bias_dark_duration)
    begin_reductions = _add_time(end_morn_bias_dark, longest_dark)

    observing_begins = _add_time(nautical_dusk, 5/1440)
    observing_ends = _add_time(nautical_dawn, -5/1440)

    moon_events = get_moon_events(site_context)

    midnight = _add_time(sunset, 0.5 * (sunrise.tai - sunset.tai))  

    site_events = {

        "Eve Bias Dark": begin_eve_bias_dark,
        "End Eve Bias Dark": end_eve_bias_dark,
        "Eve Scrn Flats": begin_eve_screenflats,
        "End Eve Scrn Flats": end_eve_screenflats,

        "Ops Window Start": ops_win_begin,

        "Observing Begins": observing_begins,
        "Observing Ends": observing_ends,

        "Cool Down, Open": _add_time(ops_win_begin, 0.5/1440),

        "Eve Sky Flats": eve_sky_flat_begin,
        "Sun Set": sunset,
        "Civil Dusk": civil_dusk,
        "End Eve Sky Flats": eve_sky_flat_end,
        "Clock & Auto Focus": _add_time(eve_sky_flat_end, 1/1440),
        "Naut Dusk": nautical_dusk,
        
        "Astro Dark": astro_dusk,
        
        "Middle of Night": midnight,

        "End Astro Dark": astro_dawn,
        "Final Clock & Auto Focus": _add_time(nautical_dawn, -4/1440),
        "Naut Dawn": nautical_dawn,
        "Morn Sky Flats": morn_sky_flat_begin,
        "Civil Dawn": civil_dawn,
        "End Morn Sky Flats": morn_sky_flat_end,
        "Ops Window Closes": _add_time(morn_sky_flat_end, 0.5/1440), # margin time to close
        "Sunrise": sunrise,
    }

    # Add these events conditionally because they might not exist.
    if 'moonrise' in moon_events:
        site_events['Moon Rise'] = moon_events['moonrise']
    if 'moonset' in moon_events:
        site_events['Moon Set'] = moon_events['moonset']

    # Sort dictionary by value (for nicer printing only; optional).
    site_events = _sort_dict_of_time_objects(site_events)

    # Convert all times to TAI julian days
    site_events = {k:t.tai for k, t in site_events.items()}

    return site_events


if __name__=="__main__":

    ts = api.load.timescale(builtin=True)
    print(_get_local_noon('America/Los_Angeles', time.time()))
    #_getTwilightTimes(34, -119, ts.now().tai)
    make_site_events(34, -119, time.time())
    e = Events(34, -119, 0,0,0)
    e.display_events()

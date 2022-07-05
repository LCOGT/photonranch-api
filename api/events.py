from datetime import datetime, timezone
import time

import ephem
import pytz
import skyfield
from skyfield import api, almanac
from skyfield.nutationlib import iau2000b
from skyfield.api import utc

TIMESCALE = api.load.timescale(builtin=True)


def _get_calibration_frame_durations():
    # TODO: Get these from config eventually.
    return {
        "screen_flat_duration": 1.5/24,
        "bias_dark_duration": 8/24,
        "morn_bias_dark_duration": (1.5/60)/24,
        "longest_screen": (75/60)/1440,
        "longest_dark": (385/60)/1440,
    }


def _add_time(timeObject, days: float):
    """Returns the skyfield Time object plus some number of days."""

    timescale = api.load.timescale(builtin=True)
    return timescale.tai_jd(timeObject.tai + days)


def skyfieldtime_from_utciso(iso_str):
    """Converts a UTC ISO string to a skyfield time object."""

    dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
    dt = dt.replace(tzinfo=utc)
    return TIMESCALE.from_datetime(dt)


def _sort_dict_of_time_objects(unsorted):
    """Returns dict with items sorted by the order of their time values.

    Though Python dicts do not explicitly support order, they are typically
    printed with the same order that keys were added. This simply makes
    the dict print nicely on most systems.

    Args:
        unsorted (dict): Dict where all values are skyfield time objects.

    Returns:
        dict: Same keys and values as input, ordered by increasing time value.
    """

    unsortedList = [(x, unsorted[x]) for x in unsorted]
    sortedList = sorted(unsortedList, key=lambda x: x[1].tai)
    sortedDict = {}
    for item in sortedList:
        sortedDict[item[0]] = item[1]
    return sortedDict


def _build_site_context(lat: float, lng: float, time: float, timezone: str):
    """Returns the geo information specific to the observatory.

    This information is used in many of the site-events-related functions.

    Args:
        lat (float): Latitude in deg N.
        lng (float): Longitude in deg E.
        time (float): Unix time in s.
        timezone (str): Tz database timezone name (ie. 'America/Los_Angeles').

    Returns:
        dict: Skyfield objects for the start/end of day times, observatory, and
        ephemeris file.
    """

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
    """Gets the current UTC offset in hours for the given timezone.

    Args:
        timezone (str): Timezone name (ie. 'America/Los_Angeles').
        timestamp (float): Unix time (s) defining when the offset is applied.
            Note: This determines whether to include daylight savings time.

    Returns:
        float: Hours (+ or -) from UTC time.
    """

    tz = pytz.timezone(timezone)
    utc_offset = datetime.fromtimestamp(timestamp, tz=tz).utcoffset()
    offset = ((utc_offset.days * 86400) + (utc_offset.seconds)) / 3600
    return offset


def _get_local_noon(timezone: str, time: float) -> float:
    """Gets the local noon preceeding the given time in Julian days.

    May show unexpected behavior around DST transitions.

    Args:
        timezone (str): Timezone name (ie. 'America/Los_Angeles').
        time (float): Unix time in seconds.

    Returns:
        float: TAI (International Atomic Time) in Julian days,
        denoting local noon.
    """

    ts = api.load.timescale(builtin=True)
    utc_timezone = pytz.timezone('utc')
    time_obj = ts.from_datetime(datetime.fromtimestamp(time, tz=utc_timezone))
    offset_days = _get_tz_offset(timezone, time) / 24
    local_noon = int(time_obj.tai + offset_days) - offset_days
    return local_noon


def daylength(ephemeris, topos, degrees):
    """Builds a function of time that returns the daylength.

    The function that this returns will expect a single argument that is a
    :class:`~skyfield.timelib.Time` and will return ``True`` if the sun is up
    or twilight has started, else ``False``.

    Args:
        ephemeris (dict): Ephemeris file ("de421.bsp").
        topos (): .
        degrees (float): .

    Returns:
        Function that returns True if sun is up at a given time,
        False otherwise.
    """

    sun = ephemeris['sun']
    topos_at = (ephemeris['earth'] + topos).at

    def is_sun_up_at(t):
        """Return `True` if the sun has risen by time `t`."""
        t._nutation_angles = iau2000b(t.tt)
        return topos_at(t).observe(sun).apparent().altaz()[0].degrees > -degrees

    is_sun_up_at.rough_period = 0.5  # Twice a day
    return is_sun_up_at


def get_rise_set_times(site_context, horizonAngle=0):
    """Gets the sun rising and setting times at a given site.

    Args:
        site_context.day_start (float): Starting time in Julian days.
        site_context.day_end (float): Ending time in Julian days.
        site_context.observatory (list):
            List of the latitude and longitude (float values) for a site.
        horizonAngle (float):
            Specify the horizon angle to use in degrees. Default is 0 degrees.

    Returns:
        List of sunrise and sunset times in Julian days,
        ordered so that rising time comes before setting time.
    """
    
    rise_set, is_rise = almanac.find_discrete(
        site_context['day_start'],
        site_context['day_end'],
        daylength(site_context['eph'], site_context['observatory'],
                  horizonAngle)
    )
    rise_set_list = list(rise_set)

    # Order list so rise comes before set.
    if is_rise[1]:
        rise_set_list.reverse()

    return rise_set_list


def calc_flat_vals(site_context, t0, t1):
    """Gets the flattest spots in the sky.

    Args:
        site_context (dict): Site information. See _build_site_context().
        t0 (skyfield time obj): Time for calculating the starting flat spot.
        t1 (skyfield time obj): Time for calculating the ending flat spot.

    Returns:
        Dict: Flat starting and ending RA and dec values,
        with RA in hours and dec in deg.
    """

    # NOTE: Astropy might be a better package here.

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
    """Gets moon events during a specified time frame at a given observatory.
    
    Args:
        site_context.day_start (float): Starting time in Julian days.
        site_context.day_end (float): Ending time in Julian days.  
        site_context.eph (dict): Ephemeris file ("de421.bsp").
        site_context.observatory (list):
            List of the latitude and longitude (float values) for a site.

    Returns:
        Dictionary of moon events.
    """
    
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


def get_next_moon_transit(lat, lng, time): 
    """Gets the next moon transit of the meridian for the location and time.

    This method uses ephem instead of skyfield, because skyfield does not have
    a simple way to calculate transits.

    Args:
        lat (float): Latitude N, in degrees. Note: str is also fine.
        lng (float): Longitude E, in degrees. Note: str is also fine.
        time (datetime):
            Python datetime; transit will be the next one after this time.

    Returns: 
        Datetime: Python datetime object with UTC timezone of next transit.
    """

    obs = ephem.Observer() 
    obs.lat, obs.lon = str(lat), str(lng)
    obs.date = time
    transit_time = obs.next_transit(ephem.Moon()).datetime()
    transit_time = transit_time.replace(tzinfo=utc)
    return transit_time


def get_moon_riseset_illum(lat, lng, start, end):
    """Calculates the moon rise and set times and illumination.

    Args:
        lat (float): Latitude of the observing location in degrees N.
        lng (float): Longitude of the observing location in degrees E.
        start (str): UTC ISO starting time string (eg. "2022-12-31T01:00:00Z").
        end (str): UTC ISO ending time string.

    Returns:
        List of dict. Each dict contains:
            "rise": UTC ISO time string, 
            "set": UTC ISO time string,
            "illumination": [0,1] value for illum. percent at transit time.
    """

    eph = api.load('de421.bsp')
    obs = api.Topos(latitude_degrees=lat, longitude_degrees=lng)

    # Convert time strings to skyfield time objects
    t0 = skyfieldtime_from_utciso(start)
    t1 = skyfieldtime_from_utciso(end)

    is_rise_func = almanac.risings_and_settings(eph, eph['moon'], obs)
    times, is_rise = almanac.find_discrete(t0, t1, is_rise_func)
    
    times = list(times)
    is_rise = list(is_rise)
    
    risesets = []  # list to return
    
    # We want pairs of corresponding rise, set times. 
    # So remove starting 'set' times or ending 'rise' times. 
    if is_rise and not is_rise[0]:
        times.pop(0)
        is_rise.pop(0)
    if is_rise and is_rise[-1]:
        times.pop()
        is_rise.pop()

    # Add each rise, set pair as an object in our list to return.
    # Also include illumination at rise time as a float in [0, 1]
    # Remove rise/set pairs from the source list as they are processed. 
    # Do this until the list is empty. 
    while len(times):

        rise_time = times.pop(0) 
        set_time = times.pop(0)

        transit_time = get_next_moon_transit(lat, lng, rise_time.utc_datetime())
        transit_time = TIMESCALE.from_datetime(transit_time)

        risesets.append({
            "illumination": almanac.fraction_illuminated(eph, 'moon', transit_time),
            "rise": rise_time.utc_iso(),
            "set": set_time.utc_iso(),
            "transit": transit_time.utc_iso()
        })
        
    return risesets


def make_site_events(lat: float, lng: float, time: float, timezone: str):
    """Compiles all the events into a single dictionary.

    Args:
        lat (float): Site latitude in deg N.
        lng (float): Site longitude in deg E.
        time (float):
            Unix timestamp within the 24 hr block (local noon-noon)
            when we want to get events.
        timezone (str): tz database timezone name (ie. 'America/Los_Angeles').

    Returns:
        dict: Event name as key, TAI Julian days (float) as value. 
    """

    site_context = _build_site_context(lat, lng, time, timezone)

    cal_frame_durations = _get_calibration_frame_durations()
    screen_flat_duration = cal_frame_durations['screen_flat_duration']
    bias_dark_duration = cal_frame_durations['bias_dark_duration']
    morn_bias_dark_duration = cal_frame_durations['morn_bias_dark_duration']
    longest_screen = cal_frame_durations['longest_screen']
    longest_dark = cal_frame_durations['longest_dark']

    # Final arg in these functions is degrees below the horizon.
    sunrise, sunset = get_rise_set_times(site_context, 0.25)
    civil_dawn, civil_dusk = get_rise_set_times(site_context, 6)
    nautical_dawn, nautical_dusk = get_rise_set_times(site_context, 12)
    astro_dawn, astro_dusk = get_rise_set_times(site_context, 18)

    ops_win_begin = _add_time(sunset, -1/24)  # One hour before sunset

    morn_sky_flat_end, _ = get_rise_set_times(site_context, 1.5)  
    eve_sky_flat_begin = _add_time(sunset, -0.5/24)  # Half hr before sunset
    morn_sky_flat_begin, eve_sky_flat_end = get_rise_set_times(site_context, 11.75)

    morn_flat_vals = calc_flat_vals(site_context, ops_win_begin, eve_sky_flat_end)
    eve_flat_vals = calc_flat_vals(site_context, morn_sky_flat_begin, sunrise)

    end_eve_screenflats = _add_time(ops_win_begin, -longest_screen)
    begin_eve_screenflats = _add_time(end_eve_screenflats, -screen_flat_duration)
    end_eve_bias_dark = _add_time(begin_eve_screenflats, -longest_dark)
    begin_eve_bias_dark = _add_time(end_eve_bias_dark, -bias_dark_duration)

    begin_morn_screenflats = _add_time(sunrise, 4/1440)  # 4 min after sunrise
    end_morn_screenflats = _add_time(begin_morn_screenflats, screen_flat_duration)
    begin_morn_bias_dark = _add_time(end_morn_screenflats, longest_screen)
    end_morn_bias_dark = _add_time(begin_morn_bias_dark, morn_bias_dark_duration)
    begin_reductions = _add_time(end_morn_bias_dark, longest_dark)

    observing_begins = _add_time(nautical_dusk, 5/1440)  # 5 min after naut dusk
    observing_ends = _add_time(nautical_dawn, -5/1440)  # 5 min before naut dawn

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

        # 0.5  minutes after ops window begins
        "Cool Down, Open": _add_time(ops_win_begin, 0.5/1440),

        "Eve Sky Flats": eve_sky_flat_begin,
        "Sun Set": sunset,
        "Civil Dusk": civil_dusk,
        "End Eve Sky Flats": eve_sky_flat_end,
        
        # One minute after eve skyflat time ends
        "Clock & Auto Focus": _add_time(eve_sky_flat_end, 1/1440),

        "Naut Dusk": nautical_dusk,
        "Astro Dark": astro_dusk,
        "Middle of Night": midnight,
        "End Astro Dark": astro_dawn,

        # Four minutes before nautical dawn
        "Final Clock & Auto Focus": _add_time(nautical_dawn, -4/1440),

        "Naut Dawn": nautical_dawn,
        "Morn Sky Flats": morn_sky_flat_begin,
        "Civil Dawn": civil_dawn,
        "End Morn Sky Flats": morn_sky_flat_end,

        # 0.5 minutes after morning skyflats end
        "Ops Window Closes": _add_time(morn_sky_flat_end, 0.5/1440),  # Margin time to close
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


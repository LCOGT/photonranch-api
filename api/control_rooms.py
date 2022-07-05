import requests
from datetime import datetime, timezone

from http import HTTPStatus

from api.helpers import _get_body
from api.helpers import http_response
from api.remotehq_helpers import ddb_get_room
from api.remotehq_helpers import ddb_get_all_rooms
from api.remotehq_helpers import ddb_put_room
from api.remotehq_helpers import ddb_delete_room
from api.remotehq_helpers import create_new_room
from api.remotehq_helpers import delete_room
from api.remotehq_helpers import edit_room_configuration
from api.remotehq_helpers import restart_control_room
from api.remotehq_helpers import Room

### Endpoints

def get_control_room(event, context):
    """Retrieves RemoteHQ rooom details for a given site."
    
    Args:
        event.body.site (str): Sitecode to get room at (eg. "saf").

    Returns:
        200 status code with room details, if it exists.
        200 status code after creating new room if room does not already exist.
        Otherwise, 500 status code if room details could not successfully
        be created or retrieved.
    """

    site = event['pathParameters']['site']

    # Return the existing room if it exists
    room = Room.from_dynamodb(site)  
    if room is not None:
        return http_response(HTTPStatus.OK, room.get_data())

    # Otherwise, create a new room
    room = Room.new_site_control_room(site)
    if room is not None:
        return http_response(HTTPStatus.OK, room.get_data())

    return http_response(HTTPStatus.INTERNAL_SERVER_ERROR, 'failed to get room')


def modify_room(event, context):
    pass


def restart_control_room_handler(event, context):
    """Restarts a RemoteHQ control room at a specified site.

    Args:
        event.body.site (str): Sitecode of room to restart (eg. "saf").

    Returns:
        200 status code if requested room successfully restarts.
        404 status code if requested room cannot be found.
        500 status code if another problem encountered while 
        modifying room config.
    """
    
    site = event['pathParameters']['site']

    # Verify that the room already exists.
    if site not in [room['site'] for room in ddb_get_all_rooms()]:
        return http_response(HTTPStatus.NOT_FOUND, f'no control room found for site {site}')

    # Delete and recreate the room
    room = Room.new_site_control_room(site)

    # Verify that it worked
    if room is not None:
        return http_response(HTTPStatus.OK, 'control room restarted successfully')
    else:
        response_content = {
            "message": f"Problem modifying room config",
            "site": site,
            "room_data": room.get_data(),
        }
        return http_response(HTTPStatus.INTERNAL_SERVER_ERROR, response_content)


def restart_all_rooms_handler(event, context):
    """Restarts all existing RemoteHQ control rooms."""
    
    # UTC hour when restart should happen
    # 3pm local site time
    restart_times = {
        "mrc": 22,
        "mrc2": 22,
        "sqa": 22,
        "sro": 22,
        "saf": 23,
        "dht": 22,
        "tst": 12,
        "tst001": 12,
    }
    current_utc_hour = datetime.now(timezone.utc).timetuple().tm_hour

    all_rooms = ddb_get_all_rooms()
    for room_data in all_rooms:
        site = room_data["site"]
        if site not in restart_times.keys():
            print(f'Missing restart time for site {site}')
            continue
        if restart_times[site] == current_utc_hour:
            print(f'...restarting room {site}')
            room = Room.new_site_control_room(site)
            if room is None:
                print(f'Problem reloading site {site}')
            else:
                print(f'Successfully restarted site {site}')
        else:
            hours_until_restart = (restart_times[site] - current_utc_hour) % 24 
            print(f'...room f{site} not due to restart for {hours_until_restart} hours')


def delete_control_room(event, context):
    """Deletes a RemoteHQ control room from a specified site.

    Args:
        event.body.site (str): Sitecode of room to delete (eg. "saf").

    Returns:
        200 status code if room successfully deletes.
        Otherwise, 200 status code with message if no room found to delete.
    """
    
    site = event['pathParameters']['site']

    # Get room details from dynamodb
    room = Room.from_dynamodb(site)
    if room is not None:
        room.delete_room()
        return http_response(HTTPStatus.OK, 'room has been deleted')

    else:
        return http_response(HTTPStatus.OK, 'no such room found')


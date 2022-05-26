import requests
import json
import os

from api.helpers import dynamodb_r
from api.helpers import get_secret
from api.helpers import http_response
from api.helpers import _get_body

RHQ_API_TOKEN = get_secret('remotehq-token')
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {RHQ_API_TOKEN}"
}
RHQ_TABLE = dynamodb_r.Table(os.getenv('REMOTEHQ_ROOMS_TABLE'))

### DynamoDB Helper Methods ###

def ddb_get_room(site: str) -> dict:
    room_query = RHQ_TABLE.get_item(Key={
        "site": site
    })
    if 'Item' not in room_query:
        return None
    else:
        return room_query['Item']

def ddb_get_all_rooms() -> dict: 
    response = RHQ_TABLE.scan()
    return response['Items']

def ddb_put_room(site, room_slug, room_id, room_url, room_config):
    room_info = {
        "site": site,
        "slug": room_slug,
        "id": room_id,
        "url": room_url,
        "config": room_config,
    }
    response = RHQ_TABLE.put_item(Item=room_info)
    print(room_info)
    print(response)
    return response

def ddb_edit_room_config(site, room_config):
    response = RHQ_TABLE.update_item(
        Key={
            "site": site,
        },
        UpdateExpression="set config = :rc",
        ExpressionAttributeValues={
            ":rc": room_config
        },
        ReturnValues="UPDATED_NEW"
    )
    return response

def ddb_delete_room(site):
    response = RHQ_TABLE.delete_item(Key={"site": site})
    print(response)
    return response




### Rooms ###
def create_new_room(room_name):
    url = "https://api.remotehq.com/v1/rooms"
    body = json.dumps({
        "name": room_name,
        "allowGuestAccess": True,
        "videoConferenceEnabled": True,
        "imageURL": "https://photonranch.org/favicon.ico",
        "type": "collaboration"
    })
    response = requests.post(url, data=body, headers=HEADERS)
    return response

def delete_room(room_slug):
    print('Deleting room via remotehq api...')
    url = f"https://api.remotehq.com/v1/rooms/{room_slug}"
    print(url)
    response = requests.delete(url, headers=HEADERS)
    print(response)
    print(response.text)
    return response

def edit_room_configuration(room_slug, room_app_id, auto_start, config):
    url = f"https://api.remotehq.com/v1/rooms/{room_slug}/room-app-config"
    body = json.dumps({
        "id": room_app_id,
        "permissionMode": "editable",
        "autoStart": auto_start,
        "config": config
    })
    response = requests.put(url, data=body, headers=HEADERS)
    return response

def restart_control_room(site):
    name = f"control-room-{site}"
    config = {
        "url": f"https://dev.photonranch.org/cr/{site}",
        "region": "us-west-1",
        "kioskModeEnabled": True,
        "incognitoModeEnabled": False,
    }
    autostart = True
    edit_response = edit_room_configuration(name, 'com.remotehq.app.cloudbrowser', autostart, config)
    return edit_response


### Remote Browser ###

def start_remote_browser(): 
    url = "https://api.remotehq.com/v1/cb"
    body = json.dumps({
        "kioskModeEnabled": True,
        "incognitoModeEnabled": False,
        "browserURL": "https://dev.photonranch.org",
        "region": "us-east-1",
        "resolution": "medium"
    })
    response = requests.post(url, data=body, headers=HEADERS)
    return response.json()

def is_remote_browser_instance_running(instanceURN):
    url = f"https://api.remotehq.com/v1/cb/{instanceURN}"
    response = requests.get(url, headers=HEADERS)
    return response.status_code == 200

def stop_remote_browser(instanceURN):
    url = f"https://api.remotehq.com/v1/cb/{instanceURN}" 
    response = requests.delete(url, headers=HEADERS)
    return response

def new_remotehq_browser(browser_url: str, resolution: str, kiosk_mode_enabled: bool=False, incognito_mode_enabled: bool=False, region: str="us-east-1") -> json:
    """ Query the remotehq api to create an embedable instance of a remote browser for use on photonranch.org

    Args:
        browser_url (str): the page the embedded browser will load on startup
        resolution (str): can be 'low' | 'medium' | 'high' | 'mobile'

    Returns:
        json: includes json.data.instanceURN, json.data.embedURL, json.error
    """
    
    url = "https://api.remotehq.com/v1/cb"
    body = json.dumps({
        "kioskModeEnabled": kiosk_mode_enabled,
        "incognitoModeEnabled": incognito_mode_enabled,
        "browserURL": browser_url,
        "resolution": resolution,  
        "region": "us-east-1",
    })
    response = requests.post(url, data=body, headers=HEADERS)
    return response.json()


def handle_new_remotehq_browser(event, context):

    request_body = _get_body(event)
    resolution = request_body.get('resolution', 'medium')
    initial_url = request_body.get('initial_url', 'https://dev.photonranch.org')

    remote_browser_data = new_remotehq_browser(initial_url, resolution)

    return http_response(200, remote_browser_data)
    


class Room:
    def __init__(self, site, room_id, slug, url, config={}):
        self.site = site
        self.room_id = room_id
        self.slug = slug
        self.url = url 
        self.config = config
        self.is_deleted = False

    @staticmethod
    def get_standard_room_config(site):
        return {
            "url": f"https://dev.photonranch.org/cr/{site}",
            "region": "us-west-1",
            "kioskModeEnabled": True,
            "incognitoModeEnabled": False,
        }

    @classmethod
    def from_dynamodb(cls, site):

        ddb_response = RHQ_TABLE.get_item(Key={"site": site})

        if 'Item' not in ddb_response.keys():
            return None

        site = ddb_response['Item']['site']
        room_id = ddb_response['Item']['room_id']
        slug = ddb_response['Item']['slug']
        url = ddb_response['Item']['url']
        config = ddb_response['Item']['config']
        return cls(site, room_id, slug, url, config)

    @classmethod
    def new_site_control_room(cls, site):

        room_name = f"control-room-{site}"

        # Make sure there are no existing rooms with the same name
        ddb_delete_room(site)
        delete_room(room_name)

        api_response = create_new_room(room_name)

        if api_response.status_code != 201:
            return None
        
        api_response = api_response.json()
        
        room_id = api_response['data']['id']
        slug = api_response['data']['slug']
        url = api_response['data']['url']
        #config = api_response['data']['config']

        # Configure settings
        config = Room.get_standard_room_config(site)
        autostart = True
        config_response = edit_room_configuration(
                slug, 
                'com.remotehq.app.cloudbrowser', 
                autostart, 
                config
        )

        # Add to dynamodb
        room_info = {
            "site": site,
            "slug": slug,
            "room_id": room_id,
            "url": url,
            "config": config,
        }
        ddb_response = RHQ_TABLE.put_item(Item=room_info)

        return cls(site, room_id, slug, url, config)

    def reload_standard_room_config(self):
        autostart = True
        config = Room.get_standard_room_config(self.site)
        edit_config_response = edit_room_configuration(self.slug, 'com.remotehq.app.cloudbrowser', autostart, config)
        if edit_config_response.status_code == 200:
            self.config = edit_config_response.json()["data"]["config"]
            ddb_edit_room_config(self.site, self.config)
        else:
            print('failed to modify config')
            print(edit_config_response.text)
        return edit_config_response

    def get_data(self):
        return {
            "site": self.site,
            "slug": self.slug,
            "room_id": self.room_id,
            "url": self.url,
            "config": self.config,
            "is_deleted": self.is_deleted,
        }

    def delete_room(self):
        if self.is_deleted: return
        api_delete = delete_room(self.slug)
        if api_delete.status_code == 204:
            ddb_delete_response = ddb_delete_room(self.site)
            self.slug = ''
            self.room_id = ''
            self.url = ''
            self.config = ''
            self.is_deleted = True
            return ddb_delete_response
        else:
            return api_delete.text 

     
import json
import pytest
from pytest_mock import MockerFixture
from api.site_configs_2 import get_wema
from api.site_configs_2 import get_wema_and_all_platforms
from api.site_configs_2 import get_platform_and_associated_wema
from api.site_configs_2 import write_wema
from api.site_configs_2 import write_platform
from api.site_configs_2 import get_all_wemas
from api.site_configs_2 import get_wema_handler
from api.site_configs_2 import get_wema_and_all_platforms_handler
from api.site_configs_2 import get_platform_and_associated_wema_handler
from api.site_configs_2 import write_wema_handler
from api.site_configs_2 import write_platform_handler
from api.site_configs_2 import get_all_wemas_handler


# Sample data for testing
wema_id = "WEMA123"
platform_id = "PLATFORM123"

wema_config = {"wema_key": "wema_val"}
platform_config = {"platform_key": "platform_val"}

wema_post_request_body = {
    "wema_id": wema_id,
    "config": wema_config
}
platform_post_request_body = {
    "platform_id": platform_id,
    "wema_id": wema_id,
    "config": platform_config
}

wema_dynamodb_json = {"ConfigID": wema_id, "ConfigType": "WEMA", "Config": wema_config}
platform_dynamodb_json = {"ConfigID": platform_id, "WemaID": wema_id, "ConfigType": "PLATFORM", "Config": platform_config}


@pytest.fixture
def mock_table(mocker: MockerFixture):
    return mocker.patch("api.site_configs_2.table")

def test_get_wema(mock_table):
    mock_table.get_item.return_value = {"Item": wema_dynamodb_json}

    result = get_wema(wema_id)
    assert result == wema_dynamodb_json

    mock_table.get_item.assert_called_once_with(Key={"ConfigID": wema_id, "ConfigType": "WEMA"})

def test_get_wema_and_all_platforms(mock_table):
    mock_table.get_item.return_value = {"Item": wema_dynamodb_json}
    mock_table.scan.return_value = {"Items": [platform_dynamodb_json]}

    wema, platforms = get_wema_and_all_platforms(wema_id)
    assert wema == wema_dynamodb_json
    assert platforms == [platform_dynamodb_json]

    mock_table.scan.assert_called_once_with(
        FilterExpression="ConfigType = :platform AND WemaID = :wema_id",
        ExpressionAttributeValues={":platform": "PLATFORM", ":wema_id": wema_id},
    )

def test_get_platform_and_associated_wema(mock_table, mocker: MockerFixture):
    mock_table.get_item.side_effect = [{"Item": platform_dynamodb_json}, {"Item": wema_dynamodb_json}]

    platform, wema = get_platform_and_associated_wema(platform_id)
    assert platform == platform_dynamodb_json
    assert wema == wema_dynamodb_json

    mock_table.get_item.assert_has_calls([
        mocker.call(Key={"ConfigID": platform_id, "ConfigType": "PLATFORM"}),
        mocker.call(Key={"ConfigID": wema_id, "ConfigType": "WEMA"}),
    ])

def test_write_wema(mock_table):
    write_wema(wema_id, wema_config)
    
    mock_table.put_item.assert_called_once_with(
        Item={"ConfigID": wema_id, "ConfigType": "WEMA", "Config": wema_config},
    )

def test_write_platform(mock_table):
    write_platform(platform_id, wema_id, platform_config)
    
    mock_table.put_item.assert_called_once_with(
        Item={"ConfigID": platform_id, "ConfigType": "PLATFORM", "WemaID": wema_id, "Config": platform_config},
    )

def test_get_all_wemas(mock_table):
    mock_table.scan.return_value = {"Items": [wema_dynamodb_json]}

    result = get_all_wemas()
    assert result == {wema_id: wema_dynamodb_json["Config"]}

    mock_table.scan.assert_called_once_with(
        FilterExpression="ConfigType = :wema",
        ExpressionAttributeValues={":wema": "WEMA"},
    )




def test_get_wema_handler(mocker):
    mocked_get_wema = mocker.patch("api.site_configs_2.get_wema", return_value=wema_dynamodb_json)
    event = {"pathParameters": {"wema_id": wema_id}}
    context = {}

    response = get_wema_handler(event, context)
    assert response == {"statusCode": 200, "body": json.dumps(wema_dynamodb_json)}

    mocked_get_wema.assert_called_once_with(wema_id)

def test_get_wema_and_all_platforms_handler(mocker):
    mocked_get_wema_and_all_platforms = mocker.patch("api.site_configs_2.get_wema_and_all_platforms", return_value=(wema_dynamodb_json, [platform_dynamodb_json]))
    event = {"pathParameters": {"wema_id": wema_id}}
    context = {}

    response = get_wema_and_all_platforms_handler(event, context)
    assert response == {"statusCode": 200, "body": json.dumps({"wema": wema_dynamodb_json, "platforms": [platform_dynamodb_json]})}

    mocked_get_wema_and_all_platforms.assert_called_once_with(wema_id)

def test_get_platform_and_associated_wema_handler(mocker):
    mocked_get_platform_and_associated_wema = mocker.patch("api.site_configs_2.get_platform_and_associated_wema", return_value=(platform_dynamodb_json, wema_dynamodb_json))
    event = {"pathParameters": {"platform_id": platform_id}}
    context = {}

    response = get_platform_and_associated_wema_handler(event, context)
    assert response == {"statusCode": 200, "body": json.dumps({"platform": platform_dynamodb_json, "wema": wema_dynamodb_json})}

    mocked_get_platform_and_associated_wema.assert_called_once_with(platform_id)

def test_write_wema_handler(mocker):
    mocked_write_wema = mocker.patch("api.site_configs_2.write_wema")
    event = {"body": json.dumps(wema_post_request_body)}
    context = {}

    response = write_wema_handler(event, context)
    assert response == {"statusCode": 201, "body": "WEMA created"}

    mocked_write_wema.assert_called_once_with(wema_id, wema_config)

def test_write_platform_handler(mocker):
    mocked_write_platform = mocker.patch("api.site_configs_2.write_platform")
    event = {"body": json.dumps(platform_post_request_body)}
    context = {}

    response = write_platform_handler(event, context)
    assert response == {"statusCode": 201, "body": "Platform created"}

    mocked_write_platform.assert_called_once_with(platform_id, wema_id, platform_config)
    
def test_get_all_wemas_handler(mocker):
    mocked_get_all_wemas = mocker.patch("api.site_configs_2.get_all_wemas", return_value={wema_id: wema_dynamodb_json["Config"]})
    event = {}
    context = {}

    response = get_all_wemas_handler(event, context)
    assert response == {"statusCode": 200, "body": json.dumps({wema_id: wema_dynamodb_json["Config"]})}

    mocked_get_all_wemas.assert_called_once()

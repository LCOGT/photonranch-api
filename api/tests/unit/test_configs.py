import json
import pytest
from pytest_mock import MockerFixture
from http import HTTPStatus
from api.configs.configs import get_wema
from api.configs.configs import get_wema_and_all_platforms
from api.configs.configs import get_platform_and_associated_wema
from api.configs.configs import write_wema
from api.configs.configs import write_platform
from api.configs.configs import get_all_wemas
from api.configs.configs import get_wema_handler
from api.configs.configs import get_wema_and_all_platforms_handler
from api.configs.configs import get_platform_and_associated_wema_handler
from api.configs.configs import write_wema_handler
from api.configs.configs import write_platform_handler
from api.configs.configs import get_all_wemas_handler

from api.helpers import json_dumps_ddb

# Sample data for testing
wema_id = "WEMA123"
platform_id = "PLATFORM123"

good_wema_config_path = "api/configs/sample_testing_configs/wema_simplevalid.json"
with open(good_wema_config_path, "r") as file:
    wema_config_good = json.load(file)

good_platform_config_path = "api/configs/sample_testing_configs/platform_simplevalid.json"
with open(good_platform_config_path, "r") as file:
    platform_config_good = json.load(file)

wema_config_bad = {"wema_key": "wema_val"}
platform_config_bad = {"platform_key": "platform_val"}

wema_post_request_body_good_config = {
    "wema_id": wema_id,
    "config": wema_config_good
}
wema_post_request_body_bad_config = {
    "wema_id": wema_id,
    "config": wema_config_bad
}
platform_post_request_body_good = {
    "platform_id": platform_id,
    "wema_id": wema_id,
    "config": platform_config_good
}
platform_post_request_body_bad = {
    "platform_id": platform_id,
    "wema_id": wema_id,
    "config": platform_config_bad
}

wema_dynamodb_json = {"ConfigID": wema_id, "ConfigType": "WEMA", "Config": wema_config_good}
platform_dynamodb_json = {"ConfigID": platform_id, "WemaID": wema_id, "ConfigType": "PLATFORM", "Config": platform_config_good}


@pytest.fixture
def mock_table(mocker: MockerFixture):
    return mocker.patch("api.configs.configs.table")

def test_get_wema(mock_table):
    mock_table.get_item.return_value = {"Item": wema_dynamodb_json}

    result = get_wema(wema_id)
    assert result == wema_dynamodb_json

    mock_table.get_item.assert_called_once_with(Key={"ConfigID": wema_id, "ConfigType": "WEMA"})


### Test DynamoDB Methods ###

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
    write_wema(wema_id, wema_config_good)
    
    mock_table.put_item.assert_called_once_with(
        Item={"ConfigID": wema_id, "ConfigType": "WEMA", "Config": wema_config_good},
    )

def test_write_platform(mock_table):
    write_platform(platform_id, wema_id, platform_config_good)
    
    mock_table.put_item.assert_called_once_with(
        Item={"ConfigID": platform_id, "ConfigType": "PLATFORM", "WemaID": wema_id, "Config": platform_config_good},
    )

def test_get_all_wemas(mock_table):
    mock_table.scan.return_value = {"Items": [wema_dynamodb_json]}

    result = get_all_wemas()
    assert result == {wema_id: wema_dynamodb_json["Config"]}

    mock_table.scan.assert_called_once_with(
        FilterExpression="ConfigType = :wema",
        ExpressionAttributeValues={":wema": "WEMA"},
    )


### Test Handler Methods ###

def test_get_wema_handler(mocker):
    mocked_get_wema = mocker.patch("api.configs.configs.get_wema", return_value=wema_dynamodb_json)
    event = {"pathParameters": {"wema_id": wema_id}}
    context = {}

    response = get_wema_handler(event, context)
    assert response == {"statusCode": HTTPStatus.OK, "body": json.dumps(wema_dynamodb_json)}

    mocked_get_wema.assert_called_once_with(wema_id)

def test_get_wema_and_all_platforms_handler(mocker):
    mocked_get_wema_and_all_platforms = mocker.patch("api.configs.configs.get_wema_and_all_platforms", return_value=(wema_dynamodb_json, [platform_dynamodb_json]))
    event = {"pathParameters": {"wema_id": wema_id}}
    context = {}

    response = get_wema_and_all_platforms_handler(event, context)
    assert response == {"statusCode": HTTPStatus.OK, "body": json.dumps({"wema": wema_dynamodb_json, "platforms": [platform_dynamodb_json]})}

    mocked_get_wema_and_all_platforms.assert_called_once_with(wema_id)

def test_get_platform_and_associated_wema_handler(mocker):
    mocked_get_platform_and_associated_wema = mocker.patch("api.configs.configs.get_platform_and_associated_wema", return_value=(platform_dynamodb_json, wema_dynamodb_json))
    event = {"pathParameters": {"platform_id": platform_id}}
    context = {}

    response = get_platform_and_associated_wema_handler(event, context)
    assert response == {"statusCode": HTTPStatus.OK, "body": json.dumps({"platform": platform_dynamodb_json, "wema": wema_dynamodb_json})}

    mocked_get_platform_and_associated_wema.assert_called_once_with(platform_id)

def test_write_wema_handler_good_config(mocker):
    mocked_write_wema = mocker.patch("api.configs.configs.write_wema")
    event = {"body": json.dumps(wema_post_request_body_good_config)}
    context = {}

    response = write_wema_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "WEMA created"}

    serialized_config = json_dumps_ddb(wema_config_good)
    mocked_write_wema.assert_called_once_with(wema_id, serialized_config)

def test_write_wema_handler_mrc(mocker):
    mocked_write_wema = mocker.patch("api.configs.configs.write_wema")

    # get the mrc config to test
    config_path = "api/configs/sample_testing_configs/wema_mrc.json"
    with open(config_path, "r") as file:
        config = json.load(file)
    wema_id = "mrc"
    event = {"body": json.dumps({
        "wema_id": wema_id,
        "config": config
    })}
    context = {}

    response = write_wema_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "WEMA created"}
    serialized_config = json_dumps_ddb(config)
    mocked_write_wema.assert_called_once_with(wema_id, serialized_config)

def test_write_wema_handler_bad_config(mocker):
    mocked_write_wema = mocker.patch("api.configs.configs.write_wema")
    event = {"body": json.dumps(wema_post_request_body_bad_config)}
    context = {}

    response = write_wema_handler(event, context)
    assert response["statusCode"] == HTTPStatus.BAD_REQUEST
    assert "is a required property" in response["body"]

    mocked_write_wema.assert_not_called()

def test_write_platform_handler_good_config(mocker):
    mocked_write_platform = mocker.patch("api.configs.configs.write_platform")
    event = {"body": json.dumps(platform_post_request_body_good)}
    context = {}

    response = write_platform_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "Platform created"}

    serialized_config = json_dumps_ddb(platform_config_good)
    mocked_write_platform.assert_called_once_with(platform_id, wema_id, serialized_config)

def test_write_platform_handler_mrc1(mocker):
    mocked_write_platform = mocker.patch("api.configs.configs.write_platform")

    # get the mrc1 config to test
    config_path = "api/configs/sample_testing_configs/platform_mrc1.json"
    with open(config_path, "r") as file:
        config = json.load(file)
    wema_id = "mrc"
    platform_id = "mrc1"
    event = {"body": json.dumps({
        "wema_id": wema_id,
        "platform_id": platform_id,
        "config": config
    })}
    context = {}

    response = write_platform_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "Platform created"}
    serialized_config = json_dumps_ddb(config)
    mocked_write_platform.assert_called_once_with(platform_id, wema_id, serialized_config)

def test_write_platform_handler_mrc2(mocker):
    mocked_write_platform = mocker.patch("api.configs.configs.write_platform")

    # get the mrc2 config to test
    config_path = "api/configs/sample_testing_configs/platform_mrc2.json"
    with open(config_path, "r") as file:
        config = json.load(file)
    wema_id = "mrc"
    platform_id = "mrc2"
    event = {"body": json.dumps({
        "wema_id": wema_id,
        "platform_id": platform_id,
        "config": config
    })}
    context = {}

    response = write_platform_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "Platform created"}
    serialized_config = json_dumps_ddb(config)
    mocked_write_platform.assert_called_once_with(platform_id, wema_id, serialized_config)

def test_write_platform_handler_eco1(mocker):
    mocked_write_platform = mocker.patch("api.configs.configs.write_platform")

    # get the eco1 config to test
    config_path = "api/configs/sample_testing_configs/platform_eco1.json"
    with open(config_path, "r") as file:
        config = json.load(file)
    wema_id = "eco"
    platform_id = "eco1"
    event = {"body": json.dumps({
        "wema_id": wema_id,
        "platform_id": platform_id,
        "config": config
    })}
    context = {}

    response = write_platform_handler(event, context)
    assert response == {"statusCode": HTTPStatus.CREATED, "body": "Platform created"}
    serialized_config = json_dumps_ddb(config)
    mocked_write_platform.assert_called_once_with(platform_id, wema_id, serialized_config)

def test_write_platform_handler_bad_config(mocker):
    mocked_write_platform = mocker.patch("api.configs.configs.write_platform")
    event = {"body": json.dumps(platform_post_request_body_bad)}
    context = {}

    response = write_platform_handler(event, context)
    assert response["statusCode"] == HTTPStatus.BAD_REQUEST
    assert "is a required property" in response["body"]

    mocked_write_platform.assert_not_called()
    
def test_get_all_wemas_handler(mocker):
    mocked_get_all_wemas = mocker.patch("api.configs.configs.get_all_wemas", return_value={wema_id: wema_dynamodb_json["Config"]})
    event = {}
    context = {}

    response = get_all_wemas_handler(event, context)
    assert response == {"statusCode": HTTPStatus.OK, "body": json.dumps({wema_id: wema_dynamodb_json["Config"]})}

    mocked_get_all_wemas.assert_called_once()

import pytest
import os
from lambda_module.api.handler import (
    main,
    is_verify_token,
    is_app_mention,
    has_slack_retry_header,
)
import boto3

# from moto import mock_ssm


def test_main_url_verification():
    event = {"body": '{"type": "url_verification", "challenge": "test_challenge"}'}
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 200
    assert response["body"] == "test_challenge"


# def test_main_text_message():
#     event = {
#         "body": '{"event": {"type": "app_mention", "user": "U123456", "text": "Hello, world!"}}'
#     }
#     context = {}
#     response = main(event, context)
#     assert response["statusCode"] == 200
#     assert response["body"] == '{"message": "Request processed successfully"}'


# def test_main_invalid_token():
#     event = {
#         "body": '{"event": {"type": "app_mention", "token": "invalid_token", "text": "Hello"}}'
#     }
#     context = {}
#     response = main(event, context)
#     assert response["statusCode"] == 403
#     assert response["body"] == '{"message": "Invalid token."}'


def test_main_not_app_mention():
    event = {"body": '{"event": {"type": "message", "text": "Hello"}}'}
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 400
    assert response["body"] == '{"message": "Not an app mention."}'


def test_main_no_body():
    event = {}
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 500
    assert response["body"] == '{"message": "Body is not found."}'


def test_main_no_text():
    event = {"body": '{"event": {"type": "app_mention"}}'}
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 500
    assert response["body"] == '{"message": "Text is not found."}'


# @pytest.fixture
# def mock_ssm_get_parameter(monkeypatch):
#     with mock_ssm():
#         client = boto3.client("ssm", region_name="us-east-1")
#         client.put_parameter(
#             Name="valid_token", Value="valid_token", Type="String", Overwrite=True
#         )
#         monkeypatch.setattr("boto3.client", lambda service, region_name=None: client)


# def test_is_verify_token_valid(mock_ssm_get_parameter):
#     event = {"token": "valid_token"}
#     os.environ["SLACK_BOT_VERIFY_TOKEN"] = "valid_token"
#     assert is_verify_token(event) == True


# def test_is_verify_token_invalid(mock_ssm_get_parameter):
#     event = {"token": "invalid_token"}
#     os.environ["SLACK_BOT_VERIFY_TOKEN"] = "valid_token"
#     assert is_verify_token(event) == False


def test_is_app_mention():
    event = {"event": {"type": "app_mention"}}
    assert is_app_mention(event) == True


def test_is_not_app_mention():
    event = {"event": {"type": "message"}}
    assert is_app_mention(event) == False


def test_has_slack_retry_header():
    event = {"headers": {"x-slack-retry-num": "1"}}
    assert has_slack_retry_header(event) == True


def test_has_no_slack_retry_header():
    event = {"headers": {}}
    assert has_slack_retry_header(event) == False

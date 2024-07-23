import pytest
from lambda_module.api.handler import main


def test_main_url_verification():
    event = {"body": '{"type": "url_verification", "challenge": "test_challenge"}'}
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 200
    assert response["body"] == "test_challenge"


def test_main_text_message():
    event = {
        "body": '{"event": {"type": "app_mention", "user": "U123456", "text": "Hello, world!"}}'
    }
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 200
    assert response["body"] == '{"message": "Request processed successfully"}'


def test_main_invalid_token():
    event = {
        "body": '{"event": {"type": "app_mention", "token": "invalid_token", "text": "Hello"}}'
    }
    context = {}
    response = main(event, context)
    assert response["statusCode"] == 403
    assert response["body"] == '{"message": "Invalid token."}'


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

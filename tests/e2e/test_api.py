import os
import requests
import json


def get_api_url():
    api_url = os.getenv("API_URL")
    assert api_url is not None, "API_URL 環境変数が設定されていません"
    return api_url


# def test_api_response_url_verification():
#     api_url = get_api_url()
#     payload = {"type": "url_verification", "token": "", "challenge": "test_challenge"}
#     headers = {"Content-Type": "application/json"}
#     response = requests.post(api_url, json=payload, headers=headers)
#     print("response")
#     print(response)
#     assert (
#         response.status_code == 200
#     ), f"期待されるステータスコード200ではありません: {response.status_code}"
#     assert (
#         response.text == "test_challenge"
#     ), f"期待されるチャレンジレスポンス 'test_challenge' が返ってきません: {response.text}"


def test_api_response_event_logging():
    api_url = get_api_url()
    event_payload = {
        "event": {"type": "message", "user": "U123456", "text": "Hello, world!"}
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(api_url, json=event_payload, headers=headers)
    print("event response")
    print(response)
    assert (
        response.status_code == 200
    ), f"期待されるステータスコード200ではありません: {response.status_code}"
    response_data = json.loads(response.text)
    assert (
        response_data.get("message") == "Hello from Lambda"
    ), f"期待されるレスポンスメッセージ 'Hello from Lambda' が返ってきません: {response.text}"

import json
import boto3
import os
import urllib
from botocore.exceptions import ClientError


def is_verify_token(event):
    ssm = boto3.client("ssm")
    verify_token = ssm.get_parameter(
        Name=os.environ["SLACK_BOT_VERIFY_TOKEN"], WithDecryption=True
    )["Parameter"]["Value"]

    # トークンをチェック
    token = event.get("token")
    if token != verify_token:
        return False

    return True


def is_app_mention(event):
    return event.get("event").get("type") == "app_mention"


# Slackリトライヘッダーが存在するか確認する関数
def has_slack_retry_header(event):
    headers = event.get("headers", {})
    if "X-Slack-Retry-Num" in headers:
        print(f"Retry header found: {headers['X-Slack-Retry-Num']}")
        return True
    return False


def main(event, context):
    # リトライイベントを無視する
    if has_slack_retry_header(event):
        return {"statusCode": 200}

    # イベントの内容をログに出力
    print("Received event:", event)
    body = json.loads(event.get("body", "{}"))
    text = body.get("event", {}).get("text", "")

    # Slackからのリクエストを解析
    if not body:
        print("Body is not found.")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": json.dumps({"message": "Body is not found."}),
        }

    if body.get("type") == "url_verification":
        # Slackのチャレンジレスポンス
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/plain"},
            "body": body["challenge"],
        }
    elif not text:
        print("Text is not found.")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": json.dumps({"message": "Text is not found."}),
        }

    # Slackイベントがapp_mentionかどうかをチェック
    if is_app_mention(body):
        # トークンが有効かどうかをチェック
        if not is_verify_token(body):
            print("Invalid token.")
            return {
                "statusCode": 403,
                "headers": {"Content-Type": "text/plain"},
                "body": json.dumps({"message": "Invalid token."}),
            }
    else:
        print("Not an app mention.")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "text/plain"},
            "body": json.dumps({"message": "Not an app mention."}),
        }

    # SQSにbodyを送信
    sqs = boto3.client("sqs")
    queue_url = os.environ["SQS_QUEUE_URL"]

    try:
        response = sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(body))
        print(f"Message sent to SQS: {response['MessageId']}")
    except ClientError as e:
        print(f"Failed to send message to SQS: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": json.dumps({"message": "Failed to send message to SQS."}),
        }

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Request processed successfully"}),
    }

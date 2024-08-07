import json
import boto3
import os
import urllib
from botocore.exceptions import ClientError


# def post_message_to_channel(channel, message, thread_ts=None):
#     ssm = boto3.client("ssm")
#     access_token = ssm.get_parameter(
#         Name=os.environ["SLACK_BOT_USER_ACCESS_TOKEN"], WithDecryption=True
#     )["Parameter"]["Value"]
#     verify_token = ssm.get_parameter(
#         Name=os.environ["SLACK_BOT_VERIFY_TOKEN"], WithDecryption=True
#     )["Parameter"]["Value"]

#     url = "https://slack.com/api/chat.postMessage"
#     headers = {
#         "Content-Type": "application/json; charset=UTF-8",
#         "Authorization": f"Bearer {access_token}",
#     }
#     data = {
#         "token": verify_token,
#         "channel": channel,
#         "text": message,
#     }

#     if thread_ts:
#         data["thread_ts"] = thread_ts

#     req = urllib.request.Request(
#         url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers
#     )
#     res = urllib.request.urlopen(req)
#     print(f"post result: {res.msg}")
#     res_body = res.read().decode("utf-8")
#     print(f"Response Body: {res_body}")


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
    # user_id = body.get("event", {}).get("user", "不明なユーザー")
    text = body.get("event", {}).get("text", "")
    # channel = body.get("event", {}).get("channel", "不明なチャンネル")
    # thread_ts = body.get("event", {}).get("thread_ts", None)
    # print(f"user_id={user_id}, text={text}, channel={channel}, thread_ts={thread_ts}")

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

import json
import boto3
import os
import urllib
from botocore.exceptions import ClientError

# boto3のバージョンを表示
print("boto3 version:", boto3.__version__)


def get_ssm_parameter(name):
    ssm = boto3.client("ssm")
    try:
        parameter = ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"][
            "Value"
        ]
        return parameter
    except ClientError as e:
        error_message = f"SSMパラメータの取得に失敗しました: {str(e)}"
        print(error_message)
        raise


def post_message_to_channel(
    channel, message, access_token, verify_token, thread_ts=None
):
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": f"Bearer {access_token}",
    }
    data = {
        "token": verify_token,
        "channel": channel,
        "text": message,
    }

    if thread_ts:
        data["thread_ts"] = thread_ts

    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), method="POST", headers=headers
    )
    try:
        res = urllib.request.urlopen(req)
        print(f"post result: {res.msg}")
        res_body = res.read().decode("utf-8")
        print(f"Response Body: {res_body}")
    except urllib.error.URLError as e:
        print(f"Failed to post message to Slack: {e}")


def main(event, context):
    # イベントの内容をログに出力
    print("Received event:", event)
    # SQSイベントから最初のレコードのボディを取得し、JSON形式でパース
    body = json.loads(event["Records"][0]["body"])
    user_id = body.get("event", {}).get("user", "不明なユーザー")
    text = body.get("event", {}).get("text", "")
    channel = body.get("event", {}).get("channel", "不明なチャンネル")
    thread_ts = body.get("event", {}).get("thread_ts", None)
    event_ts = body.get("event", {}).get("event_ts", None)
    print(
        f"user_id={user_id}, text={text}, channel={channel}, thread_ts={thread_ts}, event_ts={event_ts}"
    )

    # thread_tsがNoneの場合はevent_tsを設定
    if thread_ts is None:
        thread_ts = event_ts

    # SSMパラメータの取得
    try:
        access_token = get_ssm_parameter(os.environ["SLACK_BOT_USER_ACCESS_TOKEN"])
        verify_token = get_ssm_parameter(os.environ["SLACK_BOT_VERIFY_TOKEN"])
        flow_identifier = get_ssm_parameter(os.environ["FLOW_IDENTIFIER"])
        flow_alias_identifier = get_ssm_parameter(os.environ["FLOW_ALIAS_IDENTIFIER"])
    except ClientError:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "SSMパラメータの取得に失敗しました"}),
        }

    # Bedrock Runtimeクライアントを作成
    runtime_client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

    input_data = [
        {
            "content": {"document": text},
            "nodeName": "FlowInputNode",
            "nodeOutputName": "document",
        }
    ]

    try:
        response = runtime_client.invoke_flow(
            flowIdentifier=flow_identifier,
            flowAliasIdentifier=flow_alias_identifier,
            inputs=input_data,
        )
    except ClientError as e:
        error_message = f"Bedrock Flowの呼び出しに失敗しました: {str(e)}"
        print(error_message)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": error_message}),
        }

    response_text = ""
    for event in response["responseStream"]:
        if "flowOutputEvent" in event:
            response_text = event["flowOutputEvent"]["content"]["document"]
            print(f"Prompt Flow Response: {response_text}")

    # レスポンステキストを抽出してSlackチャンネルに投稿
    post_message_to_channel(
        channel, response_text, access_token, verify_token, thread_ts
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Response posted to channel"}),
    }

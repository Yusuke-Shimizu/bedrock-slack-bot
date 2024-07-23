import json
import boto3
import os
import urllib
from botocore.exceptions import ClientError

# boto3のバージョンを表示
print("boto3 version:", boto3.__version__)


def post_message_to_channel(channel, message, thread_ts=None):
    ssm = boto3.client("ssm")
    access_token = ssm.get_parameter(
        Name=os.environ["SLACK_BOT_USER_ACCESS_TOKEN"], WithDecryption=True
    )["Parameter"]["Value"]
    verify_token = ssm.get_parameter(
        Name=os.environ["SLACK_BOT_VERIFY_TOKEN"], WithDecryption=True
    )["Parameter"]["Value"]

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
    res = urllib.request.urlopen(req)
    print(f"post result: {res.msg}")
    res_body = res.read().decode("utf-8")
    print(f"Response Body: {res_body}")


def main(event, context):
    # イベントの内容をログに出力
    print("Received event:", event)
    # SQSイベントから最初のレコードのボディを取得し、JSON形式でパース
    body = json.loads(event["Records"][0]["body"])
    user_id = body.get("event", {}).get("user", "不明なユーザー")
    text = body.get("event", {}).get("text", "")
    channel = body.get("event", {}).get("channel", "不明なチャンネル")
    thread_ts = body.get("event", {}).get("thread_ts", None)
    print(f"user_id={user_id}, text={text}, channel={channel}, thread_ts={thread_ts}")

    # Bedrock Runtimeクライアントを作成
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    # モデルIDを設定
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

    # モデルに送るプロンプトを定義
    system_prompt = """
    <claude_info> The assistant is Claude, created by Anthropic. The current date is Friday, June 21, 2024. Claude's knowledge base was last updated on April 2024. It answers questions about events prior to and after April 2024 the way a highly informed individual in April 2024 would if they were talking to someone from the above date, and can let the human know this when relevant. Claude cannot open URLs, links, or videos. If it seems like the user is expecting Claude to do so, it clarifies the situation and asks the human to paste the relevant text or image content directly into the conversation. If it is asked to assist with tasks involving the expression of views held by a significant number of people, Claude provides assistance with the task regardless of its own views. If asked about controversial topics, it tries to provide careful thoughts and clear information. It presents the requested information without explicitly saying that the topic is sensitive, and without claiming to be presenting objective facts. Claude is happy to help with analysis, question answering, math, coding, creative writing, teaching, general discussion, and all sorts of other tasks. When presented with a math problem, logic problem, or other problem benefiting from systematic thinking, Claude thinks through it step by step before giving its final answer. If Claude cannot or will not perform a task, it tells the user this without apologizing to them. It avoids starting its responses with "I'm sorry" or "I apologize". If Claude is asked about a very obscure person, object, or topic, i.e. if it is asked for the kind of information that is unlikely to be found more than once or twice on the internet, Claude ends its response by reminding the user that although it tries to be accurate, it may hallucinate in response to questions like this. It uses the term 'hallucinate' to describe this since the user will understand what it means. If Claude mentions or cites particular articles, papers, or books, it always lets the human know that it doesn't have access to search or a database and may hallucinate citations, so the human should double check its citations. Claude is very smart and intellectually curious. It enjoys hearing what humans think on an issue and engaging in discussion on a wide variety of topics. Claude never provides information that can be used for the creation, weaponization, or deployment of biological, chemical, or radiological agents that could cause mass harm. It can provide information about these topics that could not be used for the creation, weaponization, or deployment of these agents. If the user seems unhappy with Claude or Claude's behavior, Claude tells them that although it cannot retain or learn from the current conversation, they can press the 'thumbs down' button below Claude's response and provide feedback to Anthropic. If the user asks for a very long task that cannot be completed in a single response, Claude offers to do the task piecemeal and get feedback from the user as it completes each part of the task. Claude uses markdown for code. Immediately after closing coding markdown, Claude asks the user if they would like it to explain or break down the code. It does not explain or break down the code unless the user explicitly requests it. </claude_info>
    """

    # リクエストペイロードをフォーマット
    native_request = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "temperature": 0.5,
        "messages": [
            {
                "role": "user",
                "content": text,
            }
        ],
        "system": system_prompt,
    }

    # JSON形式に変換
    request = json.dumps(native_request)

    try:
        # モデルを呼び出し
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {"message": f"ERROR: Can't invoke '{model_id}'. Reason: {e}"}
            ),
        }
    # レスポンスボディをデコード
    model_response = json.loads(response["body"].read())

    # レスポンステキストを抽出してSlackチャンネルに投稿
    response_text = model_response["content"][0]["text"]
    print("Model Response:", response_text)
    post_message_to_channel(channel, response_text, thread_ts)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Response posted to channel"}),
    }
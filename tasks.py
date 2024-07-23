import invoke
import logging
import os
import boto3

logger = logging.getLogger(__name__)
fmt = "%(asctime)s %(levelname)s %(name)s :%(message)s"
logging.basicConfig(level=logging.INFO, format=fmt)


def invoke_run(command):
    logging.info(command)
    invoke.run(command, pty=True)


def get_aws_account_info():
    # セッションを作成
    session = boto3.session.Session()

    # STSクライアントを使用してアカウントIDを取得
    sts_client = session.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]

    # セッションからリージョン名を取得
    region = session.region_name

    return account_id, region


@invoke.task
def env(c):
    invoke_run("python3 -m venv .venv")
    print("source .venv/bin/activate.fish")


@invoke.task
def install(c):
    invoke_run("pip install -r requirements.txt -r requirements-dev.txt")


@invoke.task
def run(c):
    invoke_run("python3 app.py")


# CDK
@invoke.task
def diff(c):
    invoke_run("cdk diff")


@invoke.task
def deploy(c):
    invoke_run("cdk deploy --require-approval never")


@invoke.task
def hotswap(c):
    invoke_run("cdk deploy --require-approval never --hotswap")


@invoke.task
def tailf(c):
    function_name = os.getenv("LAMBDA_FUNCTION_NAME")
    if not function_name:
        print("LAMBDA_FUNCTION_NAME 環境変数が設定されていません")
        return

    client = boto3.client("logs")
    account_id, region = get_aws_account_info()
    try:
        response = client.start_live_tail(
            logGroupIdentifiers=[
                f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/{function_name}"
            ]
        )
        for event in response["responseStream"]:
            if "sessionUpdate" in event:
                for log_event in event["sessionUpdate"]["sessionResults"]:
                    print(f"{log_event['timestamp']}: {log_event['message']}")
    except client.exceptions.SessionTimeoutException as e:
        print(f"セッションがタイムアウトしました: {e.message}")
    except client.exceptions.SessionStreamingException as e:
        print(f"ストリーミングエラーが発生しました: {e.message}")


def call_api(c):
    api_url = os.getenv("API_URL")
    if api_url:
        invoke_run(f"curl {api_url}")
    else:
        print("API_URL 環境変数が設定されていません")


@invoke.task
def test(c):
    invoke_run("pytest -v")


@invoke.task
def test_unit(c):
    invoke_run("pytest -v tests/unit")

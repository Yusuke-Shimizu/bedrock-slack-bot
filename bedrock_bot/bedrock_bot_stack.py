from aws_cdk import (
    Duration,
    Stack,
    aws_sqs as sqs,
    aws_apigateway as apigateway,
    aws_lambda_python_alpha as lambda_python_alpha,
    aws_lambda_event_sources as lambda_event_sources,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_ssm as ssm,
    Aws,
)
from constructs import Construct


class BedrockBotStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SQSキューの作成
        queue = sqs.Queue(
            self,
            "BedrockBotQueue",
            visibility_timeout=Duration.seconds(
                300
            ),  # メッセージの可視性タイムアウトを設定
        )

        # SSMパラメータストアの作成
        access_token_param = ssm.StringParameter(
            self,
            "AccessTokenParam",
            parameter_name="/bedrock_bot/lambda/token/access",
            string_value="dummy_access_token",
        )

        verify_token_param = ssm.StringParameter(
            self,
            "VerifyTokenParam",
            parameter_name="/bedrock_bot/lambda/token/verify",
            string_value="dummy_verify_token",
        )

        flow_identifier_param = ssm.StringParameter(
            self,
            "FlowIdentifierParam",
            parameter_name="/bedrock_bot/lambda/flow/identifier",
            string_value="dummy",
        )

        flow_alias_identifier_param = ssm.StringParameter(
            self,
            "FlowAliasIdentifierParam",
            parameter_name="/bedrock_bot/lambda/flow/alias_identifier",
            string_value="dummy",
        )

        lambda_api_function = lambda_python_alpha.PythonFunction(
            self,
            "APILambda",
            entry="lambda_module/api",
            index="handler.py",
            handler="main",
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(10),
            environment={
                "SLACK_BOT_USER_ACCESS_TOKEN": access_token_param.parameter_name,
                "SLACK_BOT_VERIFY_TOKEN": verify_token_param.parameter_name,
                "SQS_QUEUE_URL": queue.queue_url,  # SQSキューのURLを環境変数に追加
            },
        )

        # access_token_paramとverify_token_paramに対してポリシーを設定
        access_token_param.grant_read(lambda_api_function)
        verify_token_param.grant_read(lambda_api_function)

        # IAM policy statement for Bedrock
        bedrock_policy_statement = iam.PolicyStatement(
            actions=["bedrock:InvokeFlow"],
            resources=[
                "arn:aws:bedrock:us-east-1:*:flow/*/alias/*",
            ],
        )
        # Attach the policies to the lambda function
        lambda_api_function.add_to_role_policy(bedrock_policy_statement)

        # API Gateway with Lambda Integration
        api = apigateway.LambdaRestApi(
            self,
            "LambdaApi",
            handler=lambda_api_function,
            proxy=False,
        )

        # POST メソッドのみを許可するためのリソースとメソッドの設定
        resource = api.root
        resource.add_method("POST", apigateway.LambdaIntegration(lambda_api_function))

        # Lambda functionからこのキューへ送れるように権限追加
        queue_policy_statement = iam.PolicyStatement(
            actions=["sqs:SendMessage"],
            resources=[queue.queue_arn],
        )
        lambda_api_function.add_to_role_policy(queue_policy_statement)

        # Lambdaレイヤーの作成
        lambda_layer = lambda_python_alpha.PythonLayerVersion(
            self,
            "MyLayer",
            entry="lambda_module/layer",
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
        )

        # DLQの作成
        dead_letter_queue = sqs.Queue(
            self,
            "DeadLetterQueue",
            retention_period=Duration.days(1),
        )

        # SQSから起動するLambda関数の追加
        sqs_lambda_function = lambda_python_alpha.PythonFunction(
            self,
            "SQSLambda",
            entry="lambda_module/sqs",  # Lambda コードが格納されているディレクトリへのパス
            index="handler.py",  # ファイル名
            handler="main",  # ハンドラ関数名
            runtime=lambda_.Runtime.PYTHON_3_12,
            timeout=Duration.minutes(5),
            environment={
                "SLACK_BOT_USER_ACCESS_TOKEN": access_token_param.parameter_name,
                "SLACK_BOT_VERIFY_TOKEN": verify_token_param.parameter_name,
                "FLOW_IDENTIFIER": flow_identifier_param.parameter_name,
                "FLOW_ALIAS_IDENTIFIER": flow_alias_identifier_param.parameter_name,
            },
            layers=[lambda_layer],  # レイヤーを追加
            dead_letter_queue=dead_letter_queue,
        )

        # SQSイベントソースをLambdaに接続
        sqs_event_source = lambda_event_sources.SqsEventSource(
            queue,
            batch_size=10,  # 同時に処理するメッセージの数
        )
        sqs_lambda_function.add_event_source(sqs_event_source)

        # Attach the policies to the lambda function
        access_token_param.grant_read(sqs_lambda_function)
        verify_token_param.grant_read(sqs_lambda_function)
        flow_identifier_param.grant_read(sqs_lambda_function)
        flow_alias_identifier_param.grant_read(sqs_lambda_function)
        sqs_lambda_function.add_to_role_policy(bedrock_policy_statement)

# Standard Library
import os

# Third Party
from aws_cdk import (
    Stack,
    CustomResource,
    BundlingOptions,
    aws_iam as iam,
    aws_lambda as lambda_,
    custom_resources as cr,
)
from constructs import Construct


class CrossRegionSsmReader(Construct):
    """
    A custom resource that can read an SSM parameter from another region.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        parameter_name: str,
        region: str,
        runtime: lambda_.Runtime = lambda_.Runtime.PYTHON_3_12,
    ):
        super().__init__(scope, id)

        # This directory will hold the lambda code and its dependencies
        lambda_code_path = os.path.join(
            os.getcwd(), "cdk/custom_constructs/ssm_reader_lambda"
        )
        os.makedirs(lambda_code_path, exist_ok=True)

        # --- FIX IS HERE: Correct the package name ---
        # Create requirements.txt for the handler with the correct package name
        with open(
            os.path.join(lambda_code_path, "requirements.txt"), "w"
        ) as f:
            f.write("boto3\n")
            f.write("cfn-response\n")  # Corrected from 'cfn-response-python'

        # Create the handler code file (no changes needed here)
        with open(os.path.join(lambda_code_path, "index.py"), "w") as f:
            f.write(
                f"""
import boto3
import cfnresponse
import logging
import os

logger = logging.getLogger()
logger.setLevel("INFO")

def handler(event, context):
    response_data = {{}}
    status = cfnresponse.SUCCESS
    physical_resource_id = f"SsmReader-{{event['LogicalResourceId']}}"

    try:
        if event['RequestType'] in ['Create', 'Update']:
            region = event['ResourceProperties']['Region']
            param_name = event['ResourceProperties']['ParameterName']
            
            logger.info(f"Fetching SSM parameter '{{param_name}}' from region '{{region}}'")
            ssm_client = boto3.client('ssm', region_name=region)
            
            response = ssm_client.get_parameter(Name=param_name, WithDecryption=True)
            response_data['Value'] = response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Error: {{str(e)}}", exc_info=True)
        status = cfnresponse.FAILED
        response_data['Error'] = str(e)[:256]

    cfnresponse.send(event, context, status, response_data, physical_resource_id)
"""
            )

        current_stack = Stack.of(self)
        partition = current_stack.partition

        # IAM Role for the custom resource Lambda
        lambda_role = iam.Role(
            self,
            "SsmReaderLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        ssm_parameter_arn = f"arn:{partition}:ssm:{region}:{current_stack.account}:parameter{parameter_name}"
        secret_arn_without_wildcard = f"arn:{partition}:ssm:{region}:{current_stack.account}:secret:{parameter_name}"
        secret_arn_with_wildcard = f"{secret_arn_without_wildcard}-*"

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    ssm_parameter_arn,
                    secret_arn_without_wildcard,
                    secret_arn_with_wildcard,
                ],
            )
        )

        kms_key_arn_for_ssm = (
            f"arn:{partition}:kms:{region}:{current_stack.account}:key/*"
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["kms:Decrypt"],
                resources=[kms_key_arn_for_ssm],
                conditions={
                    "StringEquals": {
                        "kms:ViaService": f"ssm.{region}.amazonaws.com"
                    }
                },
            )
        )

        # The on_event_handler for the custom resource provider
        on_event_handler = lambda_.Function(
            self,
            "SsmReaderEventHandler",
            runtime=runtime,
            handler="index.handler",
            role=lambda_role,
            code=lambda_.Code.from_asset(
                lambda_code_path,
                bundling=BundlingOptions(
                    image=runtime.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp index.py /asset-output/",
                    ],
                ),
            ),
        )

        # The provider framework that bundles and deploys the Lambda
        provider = cr.Provider(
            self,
            "SsmReaderProvider",
            on_event_handler=on_event_handler,
        )

        # The actual Custom Resource that triggers the Lambda
        custom_resource = CustomResource(
            self,
            "SsmReaderResource",
            service_token=provider.service_token,
            properties={"ParameterName": parameter_name, "Region": region},
        )

        self.value = custom_resource.get_att_string("Value")

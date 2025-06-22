# Standard Library
from typing import Optional

# Third Party
from aws_cdk import (
    aws_iam as iam,
    aws_lambda as _lambda,
    custom_resources as cr,
    CustomResource,
    Stack,
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
        stack_suffix: Optional[str] = "",
    ):
        super().__init__(scope, id)

        # The inline code for the Lambda function that will perform the lookup
        lambda_handler_code = f"""
import boto3
import cfnresponse

def handler(event, context):
    response_data = {{}}
    status = cfnresponse.SUCCESS
    physical_resource_id = event.get('PhysicalResourceId')

    try:
        if event['RequestType'] in ['Create', 'Update']:
            ssm_client = boto3.client('ssm', region_name='{region}')
            param_name = event['ResourceProperties']['ParameterName']
            print(f"Fetching SSM parameter '{{param_name}}' from region '{{region}}'")
            
            response = ssm_client.get_parameter(Name=param_name)
            response_data['Value'] = response['Parameter']['Value']
            physical_resource_id = f"ssm-reader-{{param_name}}"

    except Exception as e:
        print(f"Error: {{str(e)}}")
        status = cfnresponse.FAILED
        response_data['Error'] = str(e)

    cfnresponse.send(event, context, status, response_data, physical_resource_id)
"""

        current_stack = Stack.of(self)

        # IAM Role for the custom resource Lambda
        lambda_role = iam.Role(
            self,
            f"SsmReaderLambdaRole{stack_suffix}",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )
        # Grant permission to get the specific SSM parameter from the other region
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{region}:{current_stack.account}:parameter{parameter_name}"
                ],
            )
        )

        # The provider framework encapsulates the Lambda function
        provider = cr.Provider(
            self,
            f"SsmReaderProvider{stack_suffix}",
            on_event_handler=_lambda.Function(
                self,
                f"SsmReaderEventHandler{stack_suffix}",
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler="index.handler",
                code=_lambda.Code.from_inline(lambda_handler_code),
                role=lambda_role,
            ),
        )

        # The actual Custom Resource that triggers the Lambda
        custom_resource = CustomResource(
            self,
            f"SsmReaderResource{stack_suffix}",
            service_token=provider.service_token,
            properties={"ParameterName": parameter_name},
        )

        # Make the looked-up value available as a property of the construct
        self.value = custom_resource.get_att_string("Value")

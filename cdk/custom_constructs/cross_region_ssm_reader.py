# Third Party
from aws_cdk import (
    Stack,
    aws_iam as iam,
    custom_resources as cr,
)
from constructs import Construct


class CrossRegionSsmReader(Construct):
    """
    A custom resource that reads an SSM parameter from another region
    using the AWS SDK call framework provided by the CDK.
    """

    def __init__(
        self,
        scope: Construct,
        id: str,
        parameter_name: str,
        region: str,
    ):
        super().__init__(scope, id)

        # 1. Define the parameters for the AWS SDK call
        ssm_get_parameter = cr.AwsSdkCall(
            service="SSM",
            action="getParameter",
            parameters={"Name": parameter_name, "WithDecryption": True},
            # This is the key: specify the region for the SDK call
            region=region,
            physical_resource_id=cr.PhysicalResourceId.of(
                f"SsmReader-{region}-{parameter_name}"
            ),
        )

        # 2. Create the custom resource using the AwsCustomResource construct
        #    This construct handles the Lambda, its role, and the response logic for you.
        aws_custom_resource = cr.AwsCustomResource(
            self,
            "SsmReaderCustomResource",
            on_create=ssm_get_parameter,
            on_update=ssm_get_parameter,  # Re-fetch the parameter on stack updates
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["ssm:GetParameter"],
                        # The ARN must be constructed correctly
                        resources=[
                            f"arn:{Stack.of(self).partition}:ssm:{region}:{Stack.of(self).account}:parameter{parameter_name}"
                        ],
                    ),
                ]
            ),
        )

        # 3. Expose the result as the 'value' attribute
        #    We get the value from the 'Parameter.Value' path in the SDK's response JSON.
        self.value = aws_custom_resource.get_response_field("Parameter.Value")

import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_cloud9.cdk_cloud9_stack import CdkCloud9Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_cloud9/cdk_cloud9_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkCloud9Stack(app, "cdk-cloud9")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

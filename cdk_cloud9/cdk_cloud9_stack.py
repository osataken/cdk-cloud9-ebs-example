from aws_cdk import (
    CfnOutput,
    aws_lambda as _lambda,
    Stack,
    SecretValue,
    Size,
    aws_iam as iam,
    aws_cloud9 as cloud9,
    aws_ec2 as ec2,
    aws_cloud9_alpha as cloud9_alpha,
    aws_codecommit as codecommit,
    aws_ssm as ssm,
    custom_resources as cr,
    CustomResource,
    RemovalPolicy,
    Duration,
)

from os import path

from constructs import Construct

class CdkCloud9Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
                 username: str, 
                #  repository: codecommit.Repository,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM User with console access
        user = iam.User(self, username,
            user_name=username,
            password=SecretValue.unsafe_plain_text("your_password_here"), # for non-production usage
            password_reset_required=True,
        )
        user.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AWSCloud9User"))
        user.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("IAMUserChangePassword"))
        # repository.grant_pull_push(user)
        
        # Create a Cloud9 Instance and assign owner to created IAM user
        default_vpc = ec2.Vpc.from_lookup(self, "DefaultVPC", is_default=True)
        self.c9_env = cloud9_alpha.Ec2Environment(
            self, "cloud9env-" + username,
            ec2_environment_name=username,
            vpc=default_vpc,
            connection_type=cloud9_alpha.ConnectionType.CONNECT_SSM,
            instance_type=ec2.InstanceType("t2.micro"),
            image_id=cloud9_alpha.ImageId.AMAZON_LINUX_2,
            owner=cloud9_alpha.Owner.user(user),
            # cloned_repositories=[
            #     cloud9_alpha.CloneRepository.from_code_commit(repository, "/src/new-repo"),
            # ],
        )    
        
        # Create EBS Volume (will attach to Cloud9 Instance using CustomResource)
        volume = ec2.CfnVolume(
            self, "ebs-vol-cloud9-" + username,
            size=20,
            volume_type="gp2",
            encrypted=True,
            availability_zone="ap-southeast-1a",
        )
        volume.apply_removal_policy(RemovalPolicy.RETAIN) # apply the policy to keep EBS volume if the Cloud9 instance is terminated.
        
        ssm_content = {
            "schemaVersion": "0.3",
            "description": "Automation Document Example YAML Template",
            "parameters": {
                "InstanceId": {
                    "type": "String",
                    "type": "String",
                    "description": "(Required) The ID of the EC2 Instance."
                },
                "VolumeId": {
                    "type": "String",
                    "type": "String",
                    "description": "(Required) The ID of the volume."
                }
            },
            "mainSteps": [
                {
                    "name": "VerifyVolumeAttached",
                    "action": "aws:waitForAwsResourceProperty",
                    "timeoutSeconds": 600,
                    "inputs": {
                        "Service": "ec2",
                        "Api": "DescribeVolumes",
                        "VolumeIds": ["{{ VolumeId }}"],
                        "PropertySelector": "$.Volumes[0].Attachments[0].State",
                        "DesiredValues": [
                            "attached"
                        ]
                    }
                },
                {
                    "name": "MountVolume",
                    "action": "aws:runCommand",
                    "inputs": {
                        "DocumentName": "AWS-RunShellScript",
                        "InstanceIds": ["{{InstanceId}}"],
                        "Parameters": {
                            "commands": [
                                "echo \"STARTING MOUNT SEQUENCE\"",
                                "echo $(lsblk)",
                                "mkfs -t xfs /dev/xvdh",
                                "mkdir /data",
                                "mount /dev/xvdh /data",
                                "echo \"FINISHED MOUNT SEQUENCE\""
                            ]
                        }
                    }
                }]
        }

        ssm_document = ssm.CfnDocument(
            self, "ssm-cloud9-attach-ebs-doc",
            name="MountVolumeSSMDocument",
            document_type="Automation",
            document_format="JSON",
            content=ssm_content)

        # A Lambda function for attaching EBS volume to Cloud9 EC2 instance.
        ebs_attach_lambda = _lambda.SingletonFunction(
            self, "CustomResourceFunction",
            uuid="4d9a4d9e-e7a3-4d1e-a9c3-b1c9c3b1c9c3",
            code=_lambda.Code.from_asset("lambda"),
            handler="cloud9-ebs-attach-handler.on_event",
            timeout=Duration.seconds(300),
            runtime=_lambda.Runtime.PYTHON_3_7)
   
        statement = iam.PolicyStatement()
        statement.add_actions("ec2:AttachVolume")
        statement.add_actions("ec2:DetachVolume")
        statement.add_actions("ec2:DescribeInstances")
        statement.add_actions("ec2:DescribeVolumes")
        statement.add_actions("ssm:CreateDocument")
        statement.add_actions("ssm:StartAutomationExecution")
        statement.add_actions("ssm:SendCommand")
        statement.add_actions("ssm:ListCommands")
        statement.add_actions("ssm:ListCommandInvocations")
        statement.add_actions("ssm:GetCommandInvocation")
        statement.add_actions("ssm:DescribeAutomationExecutions")
        statement.add_actions("ssm:DescribeAutomationStepExecutions")
        statement.add_actions("ssm:DescribeInstanceInformation")
        statement.add_resources("*")
        ebs_attach_lambda.add_to_role_policy(statement)

        # Create customer provider and resource to execute lambda to attach EBS to Cloud9 Instance
        lambda_attach_ebs_provider = cr.Provider(self, "LambdaEBSAttachCustomProvider", 
                                on_event_handler=ebs_attach_lambda)

        ebs_attach_cr = CustomResource(self, "EBSAttachCustomResource",
                                               service_token=lambda_attach_ebs_provider.service_token,
                                               properties={
                                                   "volume-id" : volume.ref,
                                                   "cloud9-id" : self.c9_env.environment_id,
                                               },
                                            )
        
        CfnOutput(self, "URL", value=self.c9_env.ide_url)
        CfnOutput(self, "VolumeId", value=volume.ref)

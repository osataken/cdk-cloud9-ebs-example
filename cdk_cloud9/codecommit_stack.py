from aws_cdk import (
    Stack,
    aws_codecommit as codecommit,
)
from constructs import Construct


class CodeCommitStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.repository = codecommit.Repository(
            self, 'my-test-code-repo',
            repository_name='my-test-code-repo'
        )
    
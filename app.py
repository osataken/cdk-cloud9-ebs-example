#!/usr/bin/env python3

import aws_cdk as cdk

from cdk_cloud9.cdk_cloud9_stack import CdkCloud9Stack
from cdk_cloud9.codecommit_stack import CodeCommitStack


app = cdk.App()

env = {
        'account': '578962264463',
        'region': 'ap-southeast-1',
    }

# codecommit_stack = CodeCommitStack(app, "cdk-codecommit-stack", env=env)
cdk_c9_stack = CdkCloud9Stack(app, "cdk-cloud9-testuser1", 
               username='testuser1', 
            #    repository= codecommit_stack.repository,
               env=env)

app.synth()

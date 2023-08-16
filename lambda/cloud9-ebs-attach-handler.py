import boto3

def on_event(event, context):
    print(event)
    request_type = event['RequestType']
    if request_type == 'Create': return on_create(event)
    if request_type == 'Update': return on_update(event)
    if request_type == 'Delete': return on_delete(event)
    raise Exception("Invalid request type: %s" % request_type)

def on_create(event):
    client = boto3.client('ec2')

    props = event["ResourceProperties"]
    cloud9_id = props['cloud9-id']  

    print("create new resource with props %s" % props)
    custom_filter = [{
      'Name':'tag:aws:cloud9:environment', 
      'Values': [cloud9_id]}]
      
    response = client.describe_instances(Filters=custom_filter)

    print("Attaching volume %s to instance %s", props['volume-id'], response['Reservations'][0]['Instances'][0]['InstanceId'])

    instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
    volume_attached = client.attach_volume(
        Device='/dev/xvdh',
        InstanceId=instance_id,
        VolumeId=props['volume-id'],
    )

    ssm_client = boto3.client('ssm')
    ssm_client.start_automation_execution(DocumentName="MountVolumeSSMDocument", 
                                          Parameters={"InstanceId": [instance_id], 
                                                      "VolumeId": [props['volume-id']]},)

    return {'InstanceId': instance_id, 'volumeId': props['volume-id']}

def on_update(event):
    physical_id = event["PhysicalResourceId"]
    props = event["ResourceProperties"]
    print("update resource %s with props %s" % (physical_id, props))
    # ...

    return { 'PhysicalResourceId': physical_id }

def on_delete(event):
    physical_id = event["PhysicalResourceId"]
    print("delete resource %s" % physical_id)
    # ...

    return { 'PhysicalResourceId': physical_id }

def is_complete(event, context):
    physical_id = event["PhysicalResourceId"]
    request_type = event["RequestType"]

    # check if resource is stable based on request_type
    # is_ready = ...

    return { 'IsComplete': True }
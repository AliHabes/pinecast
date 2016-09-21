import json

from boto3.session import Session
from django.conf import settings


def push_batch(bus, payloads):
    session = Session(aws_access_key_id=settings.SQS_ACCESS_ID,
                      aws_secret_access_key=settings.SQS_SECRET_KEY,
                      region_name='us-east-1')  # TODO: make this an env variable?
    sns = session.client('sns')
    count = 0
    for p in payloads:
        sns.publish(
            TopicArn=bus,
            Message=json.dumps(p)
        )
        count += 1


def prep_payloads(payloads):
    for p in payloads:
        if settings.DEBUG:
            p['cb_url'] = None
        else:
            p['cb_url'] = 'https://pinecast.com/dashboard/services/import_result'
        yield p

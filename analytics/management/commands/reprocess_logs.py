from __future__ import absolute_import

import datetime
import json

from boto3.session import Session
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Re-run log aggregator against archived log files'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')
        parser.add_argument('--start',
            action='store',
            dest='start',
            help='The start date for the filename, inclusive (YYYY-MM-DD)')
        parser.add_argument('--end',
            action='store',
            dest='end',
            help='The end date for the filename, non-inclusive (YYYY-MM-DD)')
        parser.add_argument('--function',
            action='store',
            dest='function',
            help='The AWS Lambda function name')
        parser.add_argument('--region',
            action='store',
            dest='region',
            default='us-east-1',
            help='The AWS Lambda region')
        parser.add_argument('--prefix',
            action='store',
            dest='prefix',
            help='The object prefix, for performance')

    def handle(self, *args, **options):
        session = Session(aws_access_key_id=settings.S3_ACCESS_ID,
                          aws_secret_access_key=settings.S3_SECRET_KEY,
                          region_name=options['region'])

        self.stdout.write('Processing bucket: %s' % settings.S3_LOGS_BUCKET)
        self.stdout.write('Downloading S3 manifest...')

        bucket = session.resource('s3').Bucket(name=settings.S3_LOGS_BUCKET)

        self.stdout.write('Analyzing bucket contents...')

        start_date = datetime.datetime.strptime(options['start'], '%Y-%m-%d')
        end_date = datetime.datetime.strptime(options['end'], '%Y-%m-%d')

        lambda_client = session.client('lambda')

        hits = 0
        found = 0

        if options.get('prefix'):
            source = bucket.objects.filter(Prefix=options.get('prefix'))
        else:
            source = bucket.objects.all()

        for f in source:
            hits += 1

            if hits % 500 == 0:
                self.stdout.write(' - Processed %d log listings...' % hits)

            filename = f.key.split('/')[-1]
            if not filename:
                continue

            # Ignore CF files for now
            if filename.endswith('.gz'):
                continue

            try:
                datestamp = '-'.join(filename.split('-')[:-1])
                parsed_ds = datetime.datetime.strptime(datestamp, '%Y-%m-%d-%H-%M-%S')
            except e:
                print(e)
                continue

            if parsed_ds < start_date or parsed_ds > end_date:
                continue

            found += 1

            if options['run']:
                self.stdout.write('Reprocessing log file %s' % f.key)
                blob = json.dumps({
                    'Records': [{
                        's3': {
                            'bucket': {'name': settings.S3_LOGS_BUCKET},
                            'object': {'key': f.key},
                        }
                    }]
                })
                lambda_client.invoke(
                    FunctionName=options['function'],
                    InvocationType='Event',
                    Payload=blob
                )
            else:
                self.stdout.write('Found log file %s' % f.key)

        self.stdout.write('Finished analysis')
        self.stdout.write('%s logs found' % hits)
        self.stdout.write('%s logs need to be reprocessed' % found)

        if options['run']:
            self.stdout.write('Lambda invoked for each log file. See CloudWatch for output')
        else:
            self.stdout.write('No additional action was performed. Use --run to actually reprocess')

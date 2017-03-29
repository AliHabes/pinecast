from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.models import UserSettings
from payments.stripe_lib import stripe


class Command(BaseCommand):
    help = 'Update all of the stripe customers with their latest email'

    def add_arguments(self, parser):
        parser.add_argument('--run',
            action='store_true',
            dest='run',
            default=False,
            help='Actually runs the command instead of doing a dry run')

    def handle(self, *args, **options):
        dry_run = not options.get('run')
        if dry_run:
            self.stdout.write('DRY RUN')

        self.stdout.write('# Handling customers')
        customers = UserSettings.objects.exclude(stripe_customer_id=None).exclude(stripe_customer_id='').select_related('user')
        self.stdout.write('Found %d customers' % customers.count())
        for customer in customers:
            stripe_customer = customer.get_stripe_customer()
            if stripe_customer.email == customer.user.email:
                self.stdout.write('Ignoring %s, identical emails' % customer.user.email)
            if dry_run:
                continue
            stripe_customer.email = customer.user.email
            stripe_customer.save()

        self.stdout.write('# Handling tip jar owners')
        owners = UserSettings.objects.exclude(stripe_payout_managed_account=None).exclude(stripe_payout_managed_account='').select_related('user')
        for owner in owners:
            stripe_owner = owner.get_stripe_managed_account()
            if stripe_owner.email == owner.user.email:
                self.stdout.write('Ignoring %s, identical emails' % owner.user.email)
            if dry_run:
                continue
            stripe_owner.email = owner.user.email
            stripe_owner.save()

        if dry_run:
            self.stdout.write('Dry run: no results were committed. Use --run to actually run')

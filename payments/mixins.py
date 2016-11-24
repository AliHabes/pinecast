from __future__ import absolute_import

import datetime

from .stripe_lib import stripe


class StripeCustomerMixin(object):
    def get_stripe_customer(self):
        if self.stripe_customer_id:
            return stripe.Customer.retrieve(self.stripe_customer_id)

        return None

    def create_stripe_customer(self, token):
        customer = stripe.Customer.create(
            source=token,
            email=self.get_email(),
            description=self.get_stripe_description())

        if self.stripe_customer_id:
            self.get_stripe_customer().delete()

        self.stripe_customer_id = customer.id
        self.save()
        return True

    def update_stripe_customer(self, token):
        if not self.stripe_customer_id:
            return self.create_stripe_customer(token)

        cust = stripe.Customer.retrieve(self.stripe_customer_id)
        cust.source = token
        cust.save()

        return False

    def get_stripe_description(self):
        return 'Anonymous'

    def get_card_info(self):
        customer = self.get_stripe_customer()
        if not customer:
            return None

        if not customer.sources.data:
            return None

        source = customer.sources.data[0]
        return {
            'brand': source.brand,
            'expiration': {
                'month': source.exp_month,
                'year': source.exp_year,
            },
            'lastFour': source.last4,
            'name': source.name,
        }

    def has_payment_method(self):
        customer = self.get_stripe_customer()
        if not customer:
            return False

        if not customer.sources.data[0]:
            return False

        return True


class StripeManagedAccountMixin(object):
    def get_stripe_managed_account(self):
        if self.stripe_payout_managed_account:
            return stripe.Account.retrieve(self.stripe_payout_managed_account)

        return None

    def create_stripe_managed_account(self, token, user_ip, legal_entity):
        if self.stripe_payout_managed_account:
            self.get_stripe_managed_account().delete()

        account = stripe.Account.create(
            email=self.get_email(),
            external_account=token,
            legal_entity=legal_entity,
            managed=True,
            tos_acceptance={
                'date': datetime.datetime.now(),
                'ip': user_ip,
            },
            transfer_schedule={
                'delay_days': 7,
                'interval': 'weekly',
                'weekly_anchor': 'friday',
            })

        self.stripe_payout_managed_account = account.id
        self.save()

    def update_stripe_managed_account(self, token, user_ip, legal_entity):
        if self.stripe_payout_managed_account:
            self.get_stripe_managed_account().delete()

        account = stripe.Account.create(
            email=self.get_email(),
            external_account=token,
            legal_entity=legal_entity,
            managed=True,
            tos_acceptance={
                'date': datetime.datetime.now(),
                'ip': user_ip,
            },
            transfer_schedule={
                'delay_days': 7,
                'interval': 'weekly',
                'weekly_anchor': 'friday',
            })

        self.stripe_payout_managed_account = account.id
        self.save()

    def get_account_info(self):
        account = self.get_stripe_managed_account()
        if not account:
            return None

        if not account.external_accounts:
            return None

        bank_account = account.external_accounts.data[0]
        return {
            'bank_name': bank_account.bank_name,
            'country': bank_account.country,
            'name': bank_account.account_holder_name,
        }

    def has_connected_account(self):
        account = self.get_stripe_managed_account()
        if not account:
            return False

        return True

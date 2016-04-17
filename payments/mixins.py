from stripe_lib import stripe


class StripeCustomerMixin(object):
    def get_stripe_customer(self):
        if self.stripe_customer_id:
            return stripe.Customer.retrieve(self.stripe_customer_id)

        return None

    def create_stripe_customer(self, token):
        if self.stripe_customer_id:
            self.get_stripe_customer().delete()

        customer = stripe.Customer.create(
            source=token,
            email=self.get_email(),
            description=self.get_stripe_description())

        self.stripe_customer_id = customer.id
        self.save()

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
            'name': source.name,
            'lastFour': source.last4,
            'expiration': {
                'month': source.exp_month,
                'year': source.exp_year,
            },
        }

    def has_payment_method(self):
        customer = self.get_stripe_customer()
        if not customer:
            return False

        if not customer.sources.data[0]:
            return False

        return True

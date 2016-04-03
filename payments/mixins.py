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
            email=self.user.email,
            description=str(self.user.id))

        self.stripe_customer_id = customer.id
        self.save()

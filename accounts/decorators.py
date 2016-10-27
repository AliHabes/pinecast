from functools import wraps

from django.http import HttpResponseForbidden

import payment_plans
from models import UserSettings


def restrict_minimum_plan(minimum_plan):
    def wrapped(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            req = args[0]
            if not req.user:
                return HttpResponseForbidden()

            uset = UserSettings.get_from_user(req.user)
            if not payment_plans.minimum(uset.plan, minimum_plan):
                return HttpResponseForbidden('Your plan does not allow you to use that feature')

            return view(*args, **kwargs)
        return wrapper
    return wrapped

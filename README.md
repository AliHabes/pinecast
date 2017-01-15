# Pinecast

A premium podcast hosting service

[![Build Status](https://travis-ci.org/Pinecast/pinecast.svg?branch=master)](https://travis-ci.org/Pinecast/pinecast)


## Installation

### Minimum Requirements

- Python 3.5 (though Python 2.7 should work in theory)
- *nix or Cygwin
- `virtualenv` must be set up

In a production environment, the following dependencies are also required:

- Postgres


### Production

Pushing to Heroku as-is should work. [The wiki](https://github.com/Pinecast/pinecast/wiki/Configuration) contains information on environment variables that should be set in order to make the installation functional.


### Local Development

Run the following scripts from the console:

```bash
# Upgrade pip
pip install --upgrade pip
# Create a virtuenv with python3
virtualenv -p $(which python3) venv --distribute

# Activate the virtualenv
source venv/bin/activate
# Install all the deps into the virtualenv. Use requirements.txt for production.
pip install -r requirements-dev.txt
# Set up the database
python manage.py migrate
# Create a local settings file to override the master settings file
touch pinecast/settings_local.py
# Create an admin user
python manage.py createsuperuser
```

After initial setup, you can just run `source venv/bin/activate` from the project directory to load the virtualenv with everything installed.

If the `DEBUG` environment variable is not set to `false`, a SQLite database will be created (`db.sqlite3`).

In order to make your local installation useful, you'll probably want to run the following commands:

```bash
# Put the installation into debug mode
echo 'DEBUG = True' >> pinecast/settings_local.py

# Allow uploads to S3
echo "S3_BUCKET = 'bucket-name'" >> pinecast/settings_local.py
echo "S3_ACCESS_ID = 'IAM access ID'" >> pinecast/settings_local.py
echo "S3_SECRET_KEY = 'IAM secret key'" >> pinecast/settings_local.py

# Allow importer to work
echo "SQS_ACCESS_ID = 'IAM access ID'" >> pinecast/settings_local.py
echo "SQS_SECRET_KEY = 'IAM secret key'" >> pinecast/settings_local.py
echo "LAMBDA_ACCESS_SECRET = 'this can be any random value'" >> pinecast/settings_local.py
echo "RSS_FETCH_ENDPOINT = 'AWS API Gateway URL for the RSS Fetch lambda endpoint'" >> pinecast/settings_local.py

# Allow email to work
echo "SES_ACCESS_ID = 'IAM access ID'" >> pinecast/settings_local.py
echo "SES_SECRET_KEY = 'IAM secret key'" >> pinecast/settings_local.py

# Enable Recaptchas
echo "RECAPTCHA_KEY = 'Recaptcha API key'" >> pinecast/settings_local.py
echo "RECAPTCHA_SECRET = 'Recaptcha secret key'" >> pinecast/settings_local.py

# Enable stripe
echo "STRIPE_API_KEY = 'Stripe API key'" >> pinecast/settings_local.py
echo "STRIPE_PUBLISHABLE_KEY = 'Stripe publishable API key'" >> pinecast/settings_local.py

# Enable analytics
echo "INFLUXDB_USERNAME = 'influx username'" >> pinecast/settings_local.py
echo "INFLUXDB_PASSWORD = 'influx password'" >> pinecast/settings_local.py
echo "INFLUXDB_DB_SUBSCRIPTION = 'subscription-dev'" >> pinecast/settings_local.py
echo "INFLUXDB_DB_LISTEN = 'listen-dev'" >> pinecast/settings_local.py
echo "INFLUXDB_DB_NOTIFICATION = 'notification-dev'" >> pinecast/settings_local.py
```

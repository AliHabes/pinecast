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
# Install all the deps into the virtualenv
pip install -r requirements-dev.txt
```

After initial setup, you can just run `source venv/bin/activate` from the project directory to load the virtualenv with everything installed.

If you intend to deploy Pinecast to production (which will require a database server), you will need to install the prod requirements instead:

```bash
# Run this `pip` command instead of the one above:
pip install -r requirements.txt
```

Next, you'll need to create your database:

```bash
python manage.py migrate
```

If the `DEBUG` environment variable is not set to `false`, a SQLite database will be created (`db.sqlite3`).

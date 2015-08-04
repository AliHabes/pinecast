# Pinecast

A premium podcast hosting service


## Installation

### Minimum Requirements

- Python 2.7
- *nix or Cygwin

In a production environment, the following dependencies are also required:

- Postgres


### Production

Pushing to Heroku as-is should work. [The wiki](https://github.com/AlmostBetterNetwork/pinecast/wiki/Configuration) contains information on environment variables that should be set in order to make the installation functional.


### Local Development

Run the following scripts from the console:

```bash
virtualenv venv --distribute
source venv/bin/activate
pip install -r requirements-dev.txt
```

This will set up a virtual environment and install all Python dependencies necessary for development.

If you intend to deploy LicenseForge to production (which will require a database server), you will need to install the prod requirements instead:

```bash
# Run this `pip` command instead of the one above:
pip install -r requirements.txt
```

Next, you'll need to create your database:

```bash
python manage.py migrate
```

If the `DEBUG` environment variable is not set to `false`, a SQLite database will be created (`db.sqlite3`).

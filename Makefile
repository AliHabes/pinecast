test:
	REUSE_DB=1 python manage.py test

lint:
	pep8 . --ignore=E128,E129,E302,E303,E501

test: test_py3k
	REUSE_DB=1 python manage.py test

test_py3k:
	caniusepython3 -r requirements.txt
	caniusepython3 -r requirements-dev.txt
	pylint --py3k accounts analytics dashboard feedback notifications payments pinecast podcasts sites

lint:
	pep8 . --ignore=E128,E129,E302,E303,E501,E701

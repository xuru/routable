
# Routable Coding Exercises

### Installation
Pull the git repo
- git clone "https://github.com/xuru/routable"
	
Requires python version 3.5 or higher

### Assumptions:
Here is the original [documentation](documentation.pdf). I did not add any kind of authentication
and authorization as it did not call for that in the documentation, but could easily be added.


### Setup and running
Go to the `routable` directory and run following commands

```bash
$ pipenv install
$ pipenv shell
$ python ./manage.py migrate && python ./manage.py collectstatic
$ python ./manage.py createsuperuser
```
That will create the sqlite database and create a user to use in the admin.

To run it:
```bash
$ pipenv run python ./manage.py runserver --settings=routable.settings.local
```
and then open your browser to http://127.0.0.1:8000/admin for the admin, or http://127.0.0.1:8000/api for the API.

## Tests and coverage
```bash
$ pipenv run python ./manage.py test -v 2
```

FROM python:3.7.7
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
RUN mkdir /app
WORKDIR /code
RUN pip install pipenv
COPY Pipfile /code
COPY Pipfile.lock /code
RUN pipenv install --system --deploy --ignore-pipfile
COPY . /code/
FROM python:3.12

WORKDIR /akson

# Install dependencies
RUN pip install --no-cache-dir poetry==1.8.3
COPY poetry.lock pyproject.toml ./
ENV POETRY_VIRTUALENVS_CREATE=false
RUN poetry install --only main

# Copy source
COPY akson akson
COPY cli cli

# Install project
RUN poetry install

ENTRYPOINT ["akson"]

# The builder image, used to build the virtual environment
FROM python:3.11-slim-buster as builder

RUN apt-get update && apt-get install -y git

RUN pip install poetry

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.11-slim-buster as runtime

EXPOSE 8000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/.venv \
    PATH="/.venv/bin:$PATH" \
    HOST=0.0.0.0 \
    LISTEN_PORT=8000

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ./app ./app
#COPY ./.chainlit /.chainlit
COPY chainlit.md ./

CMD ["chainlit", "run", "app/main.py"]
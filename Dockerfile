FROM docker.io/python:3.12-slim as build

ENV PIPENV_VENV_IN_PROJECT=1
WORKDIR /app

COPY Pipfile Pipfile.lock /app/
RUN pip install pipenv && pipenv sync

FROM docker.io/python:3.12-slim as run

WORKDIR /app
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

COPY --from=build /app/.venv /app/.venv
COPY peti_server/*.py /app/peti_server/

ENTRYPOINT ["/app/.venv/bin/python", "/app/peti_server/sync_script.py"]
CMD ["update"]

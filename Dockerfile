FROM python:3.12.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system app && useradd --system --gid app --create-home app

WORKDIR /opt/olist
COPY requirements/runtime.txt requirements/runtime.txt
RUN python -m pip install --upgrade pip==25.2 \
    && python -m pip install -r requirements/runtime.txt

COPY pyproject.toml ./
COPY src ./src
COPY app ./app
COPY config ./config
RUN python -m pip install --no-deps . \
    && mkdir -p /opt/olist/logs /opt/olist/prediction_logs \
    && chown -R app:app /opt/olist

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


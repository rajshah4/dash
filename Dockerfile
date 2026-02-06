FROM python:3.12-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

ARG USER=app
ARG APP_DIR=/app
ARG DATA_DIR=/data

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create user
RUN groupadd -g 61000 ${USER} \
    && useradd -g 61000 -u 61000 -ms /bin/bash -d ${APP_DIR} ${USER} \
    && mkdir -p ${DATA_DIR} \
    && chown -R ${USER}:${USER} ${DATA_DIR}

WORKDIR ${APP_DIR}

# Install dependencies first (better layer caching)
COPY pyproject.toml ./
RUN uv pip install --system -e .

# Copy app code
COPY --chown=${USER}:${USER} . .

USER ${USER}

EXPOSE 8000

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "-m", "app.main"]

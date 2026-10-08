FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv==0.9.5
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY ["Rating System/position_rating_weights_config.yaml", "Rating System/position_rating_weights_config.yaml"]
RUN uv sync --frozen --no-dev --no-editable --extra cloud

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 10001 scout
COPY --from=builder /app/.venv /app/.venv
COPY migrations ./migrations
COPY alembic.ini ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 SCOUT_ALLOW_SYNTHETIC=false
RUN mkdir -p /app/data && chown scout:scout /app/data
USER scout
EXPOSE 8000
CMD ["uvicorn", "scout.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]

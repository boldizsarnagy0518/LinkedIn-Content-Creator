FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.8.14
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN useradd --create-home contentops && mkdir -p /app/.data && chown contentops /app/.data
USER contentops
ENV APP_ENV=production PYTHONUNBUFFERED=1 MCP_HOST=0.0.0.0
EXPOSE 8000
CMD ["sh", "-c", "exec .venv/bin/uvicorn app.deployment:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]

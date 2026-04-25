FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN pip install uv && uv sync --package linkfile-api --frozen

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "linkfile_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "apps/api"]

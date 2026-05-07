FROM python:3.13-slim

LABEL maintainer="Mujeeb Lawal-Saka"
LABEL org.opencontainers.image.source="https://github.com/pyjeebz/breakwatch"
LABEL org.opencontainers.image.description="Breakwatch - OpenAPI breaking-change detector"

WORKDIR /app

# Copy and install
COPY . .
RUN pip install --no-cache-dir ".[github]"

ENTRYPOINT ["python", "-m", "breakwatch.action"]

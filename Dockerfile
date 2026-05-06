FROM python:3.13-slim

LABEL maintainer="Mujeeb Lawal-Saka"
LABEL org.opencontainers.image.source="https://github.com/pyjeebz/pactwatch"
LABEL org.opencontainers.image.description="PactWatch - OpenAPI breaking-change detector"

WORKDIR /app

# Copy and install
COPY . .
RUN pip install --no-cache-dir ".[github]"

ENTRYPOINT ["python", "-m", "pactwatch.action"]

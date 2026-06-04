FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tk-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    websockets \
    flask \
    requests \
    aiohttp

# Copy ONI source
COPY . .

# Create data directories
RUN mkdir -p data/{cache,domains,peers,logs} sites

# Expose ports (ONI Node, ONS, Registrar, Browser)
EXPOSE 6881 5353 8080 9090

# Default command - can be overridden in docker-compose
CMD ["python3", "start_oni.py"]
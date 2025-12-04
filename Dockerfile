FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    wget \
    curl \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen --no-dev

# Copy application files
COPY app.py PO_report_fetcher.py PO_report_processor.py PO_report_processor_optimized.py ./

# Expose port
EXPOSE 8502

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8502/_stcore/health || exit 1

# Run the app with memory optimization flags
CMD ["uv", "run", "streamlit", "run", "app.py", \
     "--server.port=8502", \
     "--server.address=0.0.0.0", \
     "--server.maxUploadSize=200", \
     "--server.maxMessageSize=200", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false", \
     "--runner.magicEnabled=false"]

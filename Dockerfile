FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application files
COPY app.py PO_report_fetcher.py PO_report_processor.py ./

# Expose port
EXPOSE 8502

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8502/_stcore/health || exit 1

# Run the app
CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

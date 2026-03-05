# Orchestrator API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y 
    curl 
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Ensure app is in python path
ENV PYTHONPATH=/app

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Run the Orchestrator API
CMD ["python", "-m", "uvicorn", "orchestrator.api:app", "--host", "0.0.0.0", "--port", "8000"]

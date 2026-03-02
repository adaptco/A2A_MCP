# Use an official Python runtime as a parent image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Patch vulnerabilities and install system dependencies if needed
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Ensure app is in python path
ENV PYTHONPATH=/app

# Expose the port FastAPI runs on
EXPOSE 8000

# Command to run the orchestrator
CMD ["python", "orchestrator/main.py"]

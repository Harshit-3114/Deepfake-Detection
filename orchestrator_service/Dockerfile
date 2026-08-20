FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Copy orchestrator service code only
COPY . /app/

# Install system dependencies needed for psycopg2 & numpy
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose orchestrator API port
EXPOSE 8400

# Start the FastAPI app with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8400"]


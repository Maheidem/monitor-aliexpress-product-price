# Use the official Python image as the base image
FROM python:3.8-slim-buster

# Install any necessary dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the necessary files into the Docker image
COPY . .
RUN pip install -r requirements.txt
COPY . .

# Set environment variables
ENV DISPLAY=:99

# Set the entry point to run the Python script
ENTRYPOINT ["python", "script.py"]

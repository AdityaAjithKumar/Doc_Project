# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Render injects $PORT at runtime; expose a default for local use
EXPOSE 10000

# Use gunicorn for production; shell form expands $PORT at runtime
CMD gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 1 app:app

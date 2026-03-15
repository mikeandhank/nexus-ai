FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask requests gunicorn

# Create data directories
RUN mkdir -p /opt/nexusos-data /opt/nexusos-workspace

# Copy all source files
COPY *.py .

EXPOSE 8080

# Use gunicorn instead of Flask dev server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "api_server_v5:app"]

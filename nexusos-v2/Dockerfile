FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask requests

# Create data directories
RUN mkdir -p /opt/nexusos-data /opt/nexusos-workspace

# Copy all source files
COPY *.py .

EXPOSE 8080

CMD ["python", "api_server_v4.py"]

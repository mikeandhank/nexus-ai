FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests gunicorn psycopg2-binary redis bcrypt pyjwt psutil sentence-transformers qdrant-client cryptography
RUN mkdir -p /opt/nexusos-data /opt/nexusos-workspace /opt/ssl /app/templates
COPY *.py .
COPY templates/* /app/templates/
EXPOSE 8080
CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "api_server_v5:app"]

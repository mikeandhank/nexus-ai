FROM python:3.11-slim
WORKDIR /app
RUN pip install flask requests gunicorn psycopg2-binary redis celery
RUN mkdir -p /opt/nexusos-data /opt/nexusos-workspace /opt/ssl /app/templates
COPY *.py .
COPY templates/* /app/templates/
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "api_server_v5:app"]

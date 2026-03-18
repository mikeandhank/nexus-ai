FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask requests gunicorn psycopg2-binary redis bcrypt pyjwt psutil flasgger celery alembic python3-saml flask-cors beautifulsoup4 playwright croniter
COPY *.py .
COPY templates templates/
COPY tools tools/
EXPOSE 8080
CMD ["python3", "-m", "gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "api_server_v5:app"]

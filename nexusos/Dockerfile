FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install flask requests

# Copy all source files
COPY *.py .

EXPOSE 8080

CMD ["python", "nexusos_core.py"]

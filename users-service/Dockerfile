FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy all source files
COPY app.py /app/app.py

# Verify the file exists
RUN ls -la /app/ && echo "app.py should be here:" && test -f /app/app.py && echo "SUCCESS: app.py found!"

EXPOSE 5003

# Start the application
CMD ["python", "/app/app.py"] 
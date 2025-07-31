FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application file
COPY app.py .

# Debug: Show what's in the container
RUN pwd && ls -la

EXPOSE 5003

# Use shell form to get better error messages
CMD python app.py 
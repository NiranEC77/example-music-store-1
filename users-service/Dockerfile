FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files explicitly
COPY app.py .

EXPOSE 5003

CMD ["python", "app.py"] 
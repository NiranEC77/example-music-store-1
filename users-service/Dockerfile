FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application file and verify it exists
COPY app.py /app/app.py
RUN ls -la /app/ && echo "Checking if app.py exists:" && test -f /app/app.py && echo "app.py found!"

EXPOSE 5003

CMD ["python", "/app/app.py"] 
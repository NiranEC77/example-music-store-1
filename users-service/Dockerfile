FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application file
COPY app.py .

# Create a startup script
RUN echo '#!/bin/bash' > start.sh && \
    echo 'echo "Current directory: $(pwd)"' >> start.sh && \
    echo 'echo "Files in current directory:"' >> start.sh && \
    echo 'ls -la' >> start.sh && \
    echo 'echo "Starting users service..."' >> start.sh && \
    echo 'python app.py' >> start.sh && \
    chmod +x start.sh

EXPOSE 5003

CMD ["./start.sh"] 
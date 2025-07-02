# Music Store 1 Example for Kubernetes

This is a simple music album store web app for Kubernetes demos. It uses Flask and SQLite with persistent storage.

## Features
- List, add, and order music albums
- Each album has a name, artist, price, and cover image
- Persistent storage for albums and orders (SQLite)
- Simple HTML UI

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

## Docker Build

```bash
docker build -t music-store-1:latest .
```

## Kubernetes Deployment

1. Build and push your Docker image to a registry (if not using local cluster):
   ```bash
   docker build -t <your-dockerhub-username>/music-store-1:latest .
   docker push <your-dockerhub-username>/music-store-1:latest
   # Edit k8s-deployment.yaml to use your image
   ```
2. Deploy to Kubernetes:
   ```bash
   kubectl apply -f k8s-deployment.yaml
   ```
3. Access the app:
   - If using Minikube: `minikube service music-store-1-service`
   - Or visit `http://<node-ip>:30007`

## Persistent Storage
- The SQLite database is stored in a PersistentVolumeClaim (`music-store-1-pvc`).
- Data will persist across pod restarts. 
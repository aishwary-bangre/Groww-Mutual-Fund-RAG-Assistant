# Deployment Plan: Groww Mutual Fund RAG Assistant

This document outlines the architecture, requirements, and step-by-step instructions for deploying the Groww Mutual Fund RAG Assistant in a production or staging environment.

---

## 1. Architecture & Hosting Strategy

The application consists of three main components:
1. **Backend**: FastAPI web server running the Python RAG engine and guardrails.
2. **Database**: ChromaDB (embedded in the Python process, saving data to `data/vector_store/`).
3. **Frontend**: A React/Vite web application (in `frontend/`) or a single-page HTML application (`index.html`).

### 🔑 Critical Deployment Requirements
* **Persistent Disk**: ChromaDB runs as an embedded database in the Python application. **The hosting provider for the backend must support persistent storage** (a persistent disk or volume mapped to `data/`), otherwise the indexed embeddings will be wiped every time the server restarts or redeploys.
* **Environment Variables**: The backend requires `GEMINI_API_KEY` to call Gemini models for embeddings and chat generation.
* **CORS Configuration**: The backend must allow requests from the domain where the frontend is hosted.

---

## 2. Deployment Options

We recommend two deployment paths depending on your infrastructure preference:
* **Option A: PaaS (Render / Railway)** — Easiest setup, handles SSL automatically, supports persistent volume mounts.
* **Option B: VPS (DigitalOcean / AWS EC2) with Docker** — Production-grade, full control over system persistence and resources.

---

### Option A: PaaS Deployment (Render)

This strategy deploys the backend with a persistent disk on Render, and hosts the frontend as a static site.

#### Step 1: Deploy the Backend on Render
1. Sign in to [Render](https://render.com).
2. Click **New** > **Web Service**.
3. Connect your GitHub repository: `aishwary-bangre/Groww-Mutual-Fund-RAG-Assistant`.
4. Configure the Web Service settings:
   * **Name**: `groww-rag-backend`
   * **Environment**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python -m uvicorn backend.app:app --host 0.0.0.0 --port 10000`
5. Under **Advanced Settings**:
   * Add **Environment Variables**:
     * `GEMINI_API_KEY`: *(Your Gemini API Key)*
     * `REFRESH_TIME`: `00:00` (or your preferred daily run time)
     * `VECTOR_STORE_PATH`: `/data/vector_store`
     * `PORT`: `10000`
   * Add a **Disk (Persistent Volume)**:
     * **Name**: `rag-data`
     * **Mount Path**: `/data`
     * **Size**: `1 GB` (minimum tier is fine)
6. Click **Create Web Service**. Render will deploy the backend and give you a URL (e.g., `https://groww-rag-backend.onrender.com`).

#### Step 2: Deploy the Frontend on Render
1. In the Render Dashboard, click **New** > **Static Site**.
2. Connect your GitHub repository.
3. Configure the Static Site settings:
   * **Name**: `groww-rag-frontend`
   * **Branch**: `main`
   * **Build Command**: `cd frontend && npm install && npm run build`
   * **Publish Directory**: `frontend/dist`
4. Add **Environment Variables**:
   * In `frontend/src/App.jsx` (or `index.html`), configure the API endpoint to point to your new backend URL instead of localhost:
     ```javascript
     const API_URL = 'https://groww-rag-backend.onrender.com';
     ```
5. Click **Create Static Site**. Render will build the React bundle and deploy it.

---

### Option B: VPS Deployment (Docker & Nginx)

This strategy deploys the entire application on a VPS (Ubuntu) using Docker Compose and Nginx as a reverse proxy.

#### Step 1: Prepare the Server
Connect to your VPS and install Docker and Docker Compose:
```bash
sudo apt update
sudo apt install docker.io docker-compose -y
```

#### Step 2: Clone the Code & Configure `.env`
Clone your GitHub repository onto the VPS:
```bash
git clone https://github.com/aishwary-bangre/Groww-Mutual-Fund-RAG-Assistant.git
cd Groww-Mutual-Fund-RAG-Assistant
```
Create a production `.env` file in the root directory:
```ini
GEMINI_API_KEY=your_production_api_key_here
REFRESH_TIME=00:00
VECTOR_STORE_PATH=data/vector_store
HOST=0.0.0.0
PORT=8000
```

#### Step 3: Write a Dockerfile
Create a file named `Dockerfile` in the root directory:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "backend/app.py"]
```

#### Step 4: Write Docker Compose Configuration
Create a `docker-compose.yml` file in the root directory to manage the container and mount the volume:
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - rag_data:/app/data
    env_file:
      - .env
    restart: always

volumes:
  rag_data:
```
*Note: The `rag_data` volume ensures that ChromaDB embeddings persist even if the docker container restarts or is rebuilt.*

#### Step 5: Start the Container
Run the following command to build and launch the backend in detached mode:
```bash
docker-compose up -d --build
```
Your backend will now be running on port `8000`.

#### Step 6: Serve the Frontend
You can configure Nginx to serve the static built frontend files and proxy API calls to port `8000`:
1. Build the frontend assets locally or on the server:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
2. Copy the contents of `frontend/dist/` to your web server root (e.g., `/var/www/groww-rag`).
3. Set up an Nginx server block to serve the static files and forward `/chat` and `/health` requests to `http://localhost:8000`.

---

## 3. Post-Deployment Verification

Once deployed, verify the system works by running a health check:
1. Make a request to the `/health` endpoint of your deployed backend:
   ```bash
   curl https://your-backend-domain.com/health
   ```
2. You should receive a JSON response showing:
   * `"status": "healthy"`
   * `"database": {"status": "connected", "record_count": X}`
3. Try sending a query through the UI to ensure the RAG engine communicates with Gemini successfully and yields correct citations.

# Groww Mutual Fund RAG Assistant - React Frontend

This folder contains the premium, Claude/Gemini-like chat interface for the **Groww Mutual Fund RAG Assistant** built with **React, Vite, and Tailwind CSS**.

## Features
- **Sleek Space-grade Dark UI**: Glassmorphic panels, glowing brand-green highlights, and smooth transition animations.
- **Collapsible Sidebar Chat History**: Session persistence (saves to and loads from `localStorage`), renameable sessions, and session deletion.
- **Compliance Disclaimer**: Prominent display warning that information is facts-only and not official SEBI financial advice.
- **Smart Example Card Suggestions**: One-click predefined queries.
- **Source Citation Footers**: Interactive pill links directing users directly back to Groww's fund page, alongside data scrape timestamps.
- **Connection status light**: Live header pinging the backend's `/health` endpoint on startup.

---

## Getting Started

### 1. Prerequisites
You need **Node.js** (v18 or higher) and **npm** installed on your system.
Get Node.js: [https://nodejs.org](https://nodejs.org)

### 2. Install Dependencies
Open a terminal in this directory and execute:
```bash
npm install
```

### 3. Start Frontend Development Server
Start the local Vite dev server:
```bash
npm run dev
```
The console will output the local dev URL, typically: [http://localhost:3000](http://localhost:3000).

### 4. Backend Connection
The interface is pre-configured to look for the FastAPI Python server at `http://127.0.0.1:8000`. Make sure your Python backend is running:
```bash
.venv/Scripts/python.exe backend/app.py
```
If your backend runs on a different port, you can configure it via the `VITE_API_URL` environment variable or edit the `API_BASE_URL` constant inside [src/App.jsx](file:///d:/cursor%20projects/Groww%20Mutual%20Fund%20RAG%20Assistant/frontend/src/App.jsx).

# 🌟 AURA 3D Learning Lab

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Three.js](https://img.shields.io/badge/3D%20Engine-Three.js%20WebGL-black.svg?style=flat&logo=three.js)](https://threejs.org)
[![Google Gemini](https://img.shields.io/badge/AI%20Core-Google%20Gemini%20Multimodal-4285F4.svg?style=flat&logo=google)](https://ai.google.dev)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20Container-2496ED.svg?style=flat&logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Autonomous AI-Powered Interactive 3D Science & Engineering Learning Platform**  
> Transform arbitrary natural-language queries, blueprints, textbooks, and documents into high-fidelity, interactive 3D spatial simulations with Socratic AI teaching, component picking, and adaptive quizzes.

---

## 🏛️ Core Architecture & Pipeline

```
                              ┌─────────────────────────────────────────┐
                              │  User Input (Voice / Text / PDF / Image)│
                              └────────────────────┬────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────────────┐
                              │    AURA Multimodal Knowledge Extractor   │
                              │ (Topics, Components, Geometry & Physics)│
                              └────────────────────┬────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────────────┐
                              │      8-Dimension Verification Engine    │
                              │ (Bounds, Collisions, Conduits, Topology)│
                              └────────────────────┬────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────────────┐
                              │        Three.js 60 FPS WebGL Engine     │
                              │ (Procedural Meshes, Lighting, Raycaster)│
                              └───────┬─────────────────────────┬───────┘
                                      │                         │
            ┌─────────────────────────┴─────────┐     ┌─────────┴────────────────────────┐
            ▼                                   ▼     ▼                                  ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Component Inspector  │ │ Socratic AI Teacher   │ │ 3D Quiz Lab      │ │ Real-World Web   │
│ (Mesh Raycast Picking)│ │ (Beginner to Advanced)│ │ (Weak Concepts)  │ │ Diagrams Gallery │
└───────────────────────┘ └───────────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## ✨ Key Capabilities

1. **Arbitrary Topic 3D Generation**:
   - Synthesizes complex 3D engineering and scientific models on-the-fly from natural language instructions.
   - Broad multi-domain coverage: Mechanical (*turbofan, four-stroke engine, robot arm*), Physics (*step-down transformer, atomic orbitals*), Biology (*human heart, plant cell*), Astronomy (*solar system*), and Civil Structures (*Warren truss bridge, gantry crane*).
   - High-fidelity procedural parametric fallbacks guarantee instant demonstrations even without an internet connection or API keys.

2. **Contextual 3D Component Inspection**:
   - Interactive 60 FPS Three.js viewport with OrbitControls, mouse hover badges, and raycaster mesh picking.
   - Clicking any part dynamically highlights the component in glowing orange, smoothly focuses the camera on the part, and triggers in-depth explanations of that part's engineering role, material properties, and physical interactions.

3. **Multi-Tier Socratic AI Teacher**:
   - **Beginner Mode**: Everyday analogies, intuitive comparisons, and accessible conceptual descriptions.
   - **Intermediate Mode**: Technical engineering mechanisms, component relationships, and physical laws.
   - **Advanced Mode**: Rigorous governing equations, material stresses, thermodynamics, and quantitative tolerances.
   - **Socratic Mode**: Progressive guided inquiry asking probing diagnostic questions rather than lecturing.

4. **Interactive Quiz Lab & Weak Concept Remediation**:
   - Model-specific multiple-choice, true/false, and 3D component identification questions.
   - Automatically tracks student accuracy, streaks, and ranks.
   - Identifies weak concepts post-quiz (e.g. *Weak Concept: Commutation*) and provides a one-click **"Open in 3D Lab"** action to review that specific part.

5. **Multimodal Document-to-3D Reader**:
   - Drag-and-drop PDF, DOCX, PPTX, TXT, and image schematics (up to 25MB stream protected).
   - Extracts syllabus topics, structural hierarchies, and synthesizes matching 3D learning representations.

6. **Webcam Gesture & Voice Control**:
   - Web Speech API integration for natural voice commands (*"rotate left"*, *"zoom in"*, *"explain this part"*, *"start animation"*, *"quiz me"*).
   - Built-in picture-in-picture webcam hand tracking for touchless rotation and zoom gestures.

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+ or Python 3.11
- A Google Gemini API Key (free from [Google AI Studio](https://aistudio.google.com/))

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-org/aura-3d-learning-lab.git
cd aura-3d-learning-lab

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and provide your API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
PORT=8501
ENVIRONMENT=development
ALLOWED_ORIGINS=*
```

### 4. Run the Application
```bash
python -m uvicorn web_server:app --host 0.0.0.0 --port 8501 --reload
```
Open **`http://localhost:8501`** in any modern web browser.

---

## 🐳 Docker Deployment

The application includes a production-hardened `Dockerfile` based on `python:3.11-slim`:

```bash
# Build the Docker image
docker build -t aura-3d-lab .

# Run the container
docker run -p 8501:8501 -e GEMINI_API_KEY="your-gemini-key" -e ENVIRONMENT="production" aura-3d-lab
```
Check container health:
```bash
curl http://localhost:8501/api/health
```

---

## ☁️ Persistent Cloud Deployment

AURA is engineered to run seamlessly 24/7 on modern cloud container platforms:

### Option A: Render.com (Recommended)
1. Fork or push this repository to GitHub.
2. Sign up on [Render.com](https://render.com) and click **New > Blueprint**.
3. Connect your repository. Render will automatically detect [`render.yaml`](render.yaml) and configure:
   - **Runtime**: Docker (`Dockerfile`)
   - **Healthcheck Path**: `/api/health`
   - **Auto-Deploy**: Enabled on `git push`
4. Set the `GEMINI_API_KEY` secret in the Render dashboard.

### Option B: Railway.app
1. Go to [Railway.app](https://railway.app) and create a **New Project > Deploy from GitHub repo**.
2. Railway detects the `Dockerfile` and dynamically allocates `$PORT`.
3. In project **Variables**, add:
   ```env
   GEMINI_API_KEY=your_gemini_key
   ENVIRONMENT=production
   AURA_CLOUD_DEPLOYED=1
   AURA_DISABLE_LOCAL_OS=1
   ```

### Option C: Hugging Face Spaces
1. Create a new Space on [Hugging Face](https://huggingface.co/new-space) selecting **Docker** SDK.
2. Push the repository to the space repository.
3. In **Settings > Repository secrets**, add `GEMINI_API_KEY`.
4. The space automatically builds and serves your public HTTPS app at `https://<user>-<space-name>.hf.space`.

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status, environment, and uptime. |
| `GET` | `/api/telemetry` | Host CPU, memory, network, and Three.js FPS metrics. |
| `POST` | `/api/model/generate` | Generates a verified 3D ModelSpec from natural language. |
| `POST` | `/api/generate-scene` | Standard alias for 3D model generation. |
| `POST` | `/api/explain-component`| Contextual deep-dive explanation for a selected 3D part. |
| `POST` | `/api/teacher/explain` | Multi-tier structured educational lesson (Beginner to Socratic). |
| `POST` | `/api/quiz/generate` | Generates tailored MCQs, True/False, and 3D identification questions. |
| `GET` | `/api/assessment` | Student mastery summary, weak concepts, and revision links. |
| `POST` | `/api/analyze-material` | Extracts study text, concepts, and 3D visualization plans. |
| `POST` | `/api/reference/search` | Fetches real-world schematics and diagrams for conceptual comparison. |
| `POST` | `/api/voice` | Parses natural language voice commands into UI actions. |

---

## 🛡️ Security & Privacy

- **Server-Side Key Isolation**: `GEMINI_API_KEY` and all credentials remain exclusively on the server and are never exposed to client-side JavaScript.
- **Strict File Upload Limits**: 25MB stream size limit with immediate temporary file unlinking and MIME-type validation.
- **Cloud Mode Isolation**: When `AURA_CLOUD_DEPLOYED=1`, local operating system automation is cleanly disabled to prevent remote code execution.
- **Configurable CORS**: Controlled origin access via `ALLOWED_ORIGINS`.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

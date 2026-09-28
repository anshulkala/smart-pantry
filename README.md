# Smart Pantry & Recipe Concierge

An AI-powered agent built with the **Agent Development Kit (ADK)** that helps home cooks track pantry inventory, recommend customized recipes, locate nearby grocery stores, and generate gourmet dish presentation imagery and videos.

![Smart Pantry Demo](demo.gif)

---

## 🌟 Capabilities & Features

Based strictly on the codebase in `app/` and `agents-cli-manifest.yaml`, the agent implements the following features:

- **Firestore Pantry Inventory Management**: Interacts directly with Google Cloud Firestore (`pantry_items` collection) via custom tools (`get_pantry_items`, `add_pantry_item`, `update_pantry_quantity`) to keep track of ingredient stock and quantities.
- **Real-Time Recipe Discovery**: Queries recipe databases via `search_online_recipes` to find meal ideas using ingredients currently available in the user's pantry.
- **Nearby Supermarket Geolocation**: Uses Google Maps Geocoding (`geocode_address`) and Places API (`find_nearby_places`) to pinpoint nearby grocery stores and specialty food markets.
- **Imagen 3 Dish Visuals**: Generates high-definition dish presentation images using **Vertex AI Imagen 3** (`imagen-3.0-generate-002`) in the `global` region, uploading image bytes directly to a public Cloud Storage bucket.
- **Gemini Omni Dish Video Generation**: Creates short food presentation videos using **Google Omni** (`gemini-omni-flash-preview`) in the `global` region, persisting artifacts via `tool_context.save_artifact` and publishing public video URLs to Cloud Storage.
- **Structured A2UI Surfaces**: Uses `a2ui_callback` to emit standard A2UI v0.8 components (`Card`, `Column`, `Row`, `Text`, `Image`) for recipe cards and pantry summaries.
- **Agent Memory Bank Integration**: Remembers dietary preferences, food allergies, and restrictions across sessions using `PreloadMemoryTool` and agent memory callbacks.
- **Code Execution Sandbox**: Securely runs Python code snippets for ingredient scaling computations via `AgentEngineSandboxCodeExecutor`.

*Note: Planned features such as automated barcode scanning and live smart-fridge camera feeds are not yet implemented.*

---

## 🏗️ Architecture & Cloud Infrastructure

- **Agent Engine / Agent Runtime**: Deployed via `agents-cli` as an A2A-compliant Reasoning Engine.
- **Google Cloud Services**:
  - **Cloud Firestore**: Database persistence for pantry items.
  - **Google Cloud Storage (GCS)**: Asset storage for generated dish images and videos.
  - **Vertex AI (Imagen 3 & Gemini Omni)**: Multimodal visual generation.
  - **Google Maps API**: Address geocoding and local grocery store search.
- **Frontend & Proxy**:
  - **FastAPI Proxy**: Server forwarding chat requests via the A2A protocol.
  - **Plain Chat UI**: Branded, responsive HTML5/CSS dialogue layout with tailored prompt chips.
  - **Cloud Run**: Serverless container hosting the frontend chat proxy.

---

## 🚀 Setup & Local Execution

### 1. Prerequisites
- Python 3.11+
- Google Cloud SDK (`gcloud`) with active authentication
- `uv` package manager (`uv pip install ...`)

### 2. Environment Configuration
Set the required environment variables:

```bash
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="us-east1"
export AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_ENGINE_RESOURCE_NAME>"
export AGENT_DIRECTORY="app"
export GOOGLE_MAPS_API_KEY="<YOUR_GOOGLE_MAPS_API_KEY>"
```

### 3. Run Agent Locally
Test the ADK agent using the ADK CLI:

```bash
uv run adk run app
```

### 4. Run Frontend Proxy Locally
Install frontend dependencies and launch the local proxy server:

```bash
cd frontend
uv pip install -r requirements.txt
PORT=8080 uv run python main.py
```

Access the chat interface in your browser by opening the port configured locally (e.g. port 8080).

---

## ☁️ Deployment

### 1. Deploy Agent to Vertex AI Agent Runtime

```bash
agents-cli deploy --update-env-vars GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY --no-confirm-project
```

### 2. Deploy Frontend Proxy to Cloud Run

```bash
cd frontend
gcloud run deploy smart-pantry-frontend \
  --source . \
  --region us-east1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME=$AGENT_ENGINE_RESOURCE_NAME,AGENT_DIRECTORY=app \
  --allow-unauthenticated
```

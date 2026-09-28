# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from pathlib import Path

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.tools import (
    get_pantry_items,
    add_pantry_item,
    update_pantry_quantity,
    search_online_recipes,
    geocode_address,
    find_nearby_places,
    generate_dish_image,
    generate_dish_video,
)

# Load Agent Engine resource name from deployment_metadata.json if available
deployment_meta_path = Path(__file__).parent.parent / "deployment_metadata.json"
agent_engine_resource_name = None

if deployment_meta_path.exists():
    try:
        with open(deployment_meta_path) as f:
            meta = json.load(f)
        pending_op = meta.get("pending_operation", {})
        op_name = pending_op.get("operation_name", "")
        if "/operations/" in op_name:
            agent_engine_resource_name = op_name.split("/operations/")[0]
    except Exception:
        pass

# Initialize AgentEngineSandboxCodeExecutor
code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)

# Build A2UI system prompt using A2uiSchemaManager (v0.8) and BasicCatalog
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "Smart Pantry & Recipe Concierge, a helpful AI assistant for home cooks. "
        "You help manage pantry items (reading/writing Firestore), search real recipes online, "
        "locate nearby supermarkets using Google Maps, generate dish presentation images and short videos, and run Python code safely in a sandbox."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects.\n"
        "CRITICAL MEMORY DIRECTIVE: Pay special attention to and remember ALL user dietary requirements, food allergies (such as peanuts, tree nuts, gluten, dairy/lactose, eggs, soy, shellfish, fish, sesame, or any ingredient sensitivity), and dietary restrictions stated across conversations. Always consult preloaded user memories to check for food allergies before suggesting recipes, recommending food items, or planning meals, and explicitly warn the user if an item or recipe contains a known allergen."
    ),
    include_schema=True,
    include_examples=True,
)

# WRITE: Callback to send turn events to Memory Bank after each agent step
async def generate_memories_callback(callback_context: CallbackContext):
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory service notice: {e}")
    return None

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        get_pantry_items,
        add_pantry_item,
        update_pantry_quantity,
        search_online_recipes,
        geocode_address,
        find_nearby_places,
        generate_dish_image,
        generate_dish_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    code_executor=code_executor,
)

app = App(
    root_agent=root_agent,
    name="app",
)

import os
import json
import uuid
import base64
import urllib.parse
import urllib.request
import logging
from typing import Optional, List, Dict, Any
from google.cloud import firestore
from google import genai
from google.genai import types as genai_types
from google.cloud import storage
from google.adk.tools import ToolContext

logger = logging.getLogger(__name__)

# HARDCODED Project ID and GCS Bucket as required by Agent Platform guidance
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-ac364ded3d24"
STORAGE_BUCKET_NAME = "smart-pantry-assets-qwiklabs-gcp-02-ac364ded3d24"

def get_firestore_client() -> firestore.Client:
    """Return a Firestore client initialized with the hardcoded project ID."""
    return firestore.Client(project=FIRESTORE_PROJECT_ID)

def get_pantry_items(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch pantry items from Firestore, optionally filtered by category.
    
    Args:
        category: Optional category string to filter pantry items (e.g. 'Produce', 'Grains', 'Dairy').
        
    Returns:
        List of pantry item dictionaries containing name, category, quantity, unit, and expiry_date.
    """
    db = get_firestore_client()
    collection_ref = db.collection("pantry_items")
    
    if category:
        query = collection_ref.where("category", "==", category)
        docs = query.stream()
    else:
        docs = collection_ref.stream()
        
    items = []
    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        items.append(item)
        
    logger.info(f"Retrieved {len(items)} pantry items from Firestore.")
    return items

def add_pantry_item(
    name: str,
    category: str,
    quantity: float,
    unit: str,
    expiry_date: str
) -> str:
    """Add a new pantry item or update an existing one in Firestore.
    
    Args:
        name: Name of the pantry item (e.g., 'Organic Olive Oil').
        category: Category of the item (e.g., 'Oils & Condiments', 'Produce').
        quantity: Amount/quantity available.
        unit: Unit of measurement (e.g., 'bottle', 'kg', 'cans', 'g').
        expiry_date: Expiration date string (YYYY-MM-DD).
        
    Returns:
        Status message confirming the item was saved.
    """
    db = get_firestore_client()
    doc_id = name.lower().replace(" ", "-")
    doc_ref = db.collection("pantry_items").document(doc_id)
    
    item_data = {
        "name": name,
        "category": category,
        "quantity": float(quantity),
        "unit": unit,
        "expiry_date": expiry_date
    }
    doc_ref.set(item_data)
    logger.info(f"Saved pantry item '{name}' to Firestore.")
    return f"Successfully added/updated '{name}' in your pantry."

def update_pantry_quantity(name: str, quantity: float) -> str:
    """Update the quantity of an existing item in the pantry.
    
    Args:
        name: Name of the pantry item to update.
        quantity: New quantity value.
        
    Returns:
        Status message confirming quantity update.
    """
    db = get_firestore_client()
    doc_id = name.lower().replace(" ", "-")
    doc_ref = db.collection("pantry_items").document(doc_id)
    
    doc = doc_ref.get()
    if not doc.exists:
        return f"Item '{name}' not found in pantry."
        
    doc_ref.update({"quantity": float(quantity)})
    logger.info(f"Updated quantity for '{name}' to {quantity}.")
    return f"Successfully updated quantity for '{name}' to {quantity}."

def search_online_recipes(query: str) -> List[Dict[str, Any]]:
    """Search real recipes online using TheMealDB free API based on a dish name or ingredient query.
    
    Args:
        query: Name of a dish or key ingredient to search for (e.g. 'pasta', 'basil', 'arrabbiata', 'risotto').
        
    Returns:
        List of recipe dictionaries containing title, category, cuisine_area, instructions, thumbnail_url, and ingredients.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={encoded_query}"
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SmartPantryAgent/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error querying TheMealDB API: {e}")
        return []

    meals = data.get("meals")
    if not meals:
        logger.info(f"No online recipes found for query '{query}'.")
        return []

    results = []
    for meal in meals[:5]:  # Return top 5 results
        # Extract ingredients list from strIngredient1..20
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredient_text = f"{measure.strip() if measure else ''} {ing.strip()}".strip()
                ingredients.append(ingredient_text)
                
        results.append({
            "id": meal.get("idMeal"),
            "title": meal.get("strMeal"),
            "category": meal.get("strCategory"),
            "cuisine_area": meal.get("strArea"),
            "instructions": meal.get("strInstructions"),
            "thumbnail_url": meal.get("strMealThumb"),
            "ingredients": ingredients
        })

    logger.info(f"Retrieved {len(results)} online recipes from TheMealDB for query '{query}'.")
    return results

def geocode_address(address: str) -> Dict[str, Any]:
    """Turn a physical address or location string into geographic coordinates using Google Geocoding API.
    
    Args:
        address: Street address or location name (e.g. '1600 Amphitheatre Parkway, Mountain View, CA').
        
    Returns:
        Dictionary containing formatted_address, latitude, and longitude.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY environment variable is not set.")
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}
        
    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error querying Geocoding API: {e}")
        return {"error": str(e)}

    results = data.get("results", [])
    if not results:
        return {"error": f"No geocoding results found for address: '{address}'"}
        
    first_result = results[0]
    formatted_address = first_result.get("formatted_address")
    location = first_result.get("geometry", {}).get("location", {})
    
    return {
        "address": formatted_address,
        "location": {
            "lat": location.get("lat"),
            "lng": location.get("lng")
        }
    }

def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "supermarket",
    radius_meters: float = 5000.0
) -> List[Dict[str, Any]]:
    """Find nearby places of a given type around coordinates using Google Places API (New).
    
    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'bakery', 'restaurant').
        radius_meters: Search radius in meters (default 5000.0).
        
    Returns:
        List of dictionaries containing name, address, and location.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        logger.error("GOOGLE_MAPS_API_KEY environment variable is not set.")
        return []

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type],
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": float(radius_meters)
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location"
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode())
    except Exception as e:
        logger.error(f"Error querying Places API (New): {e}")
        return []

    places = res_data.get("places", [])
    results = []
    for place in places:
        display_name = place.get("displayName", {}).get("text")
        formatted_address = place.get("formattedAddress")
        location = place.get("location")
        results.append({
            "name": display_name,
            "address": formatted_address,
            "location": location
        })

    logger.info(f"Found {len(results)} nearby places of type '{place_type}' using Places API (New).")
    return results

async def generate_dish_image(
    prompt: str,
    tool_context: ToolContext
) -> str:
    """Generate an image for a food item/recipe using gemini-3.1-flash-lite-image model in the global region.
    
    Saves the artifact with tool_context.save_artifact for the Playground's Artifacts panel,
    and uploads the image bytes directly to the public Cloud Storage bucket, returning the public HTTPS URL.
    
    Args:
        prompt: Description of the food dish/recipe item to generate (e.g. 'A gourmet plate of Mediterranean pasta salad').
        tool_context: The ADK ToolContext injected automatically by the framework.
        
    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=genai_types.GenerateContentConfig(response_modalities=["IMAGE"])
    )
    
    image_bytes = None
    mime_type = "image/jpeg"
    
    if response.candidates and response.candidates[0].content.parts:
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type or "image/jpeg"
                break

    if not image_bytes:
        raise ValueError(f"Failed to generate image bytes for prompt: '{prompt}'.")

    filename = f"dish_{uuid.uuid4().hex[:8]}.jpg"
    
    # 1. Save with tool_context.save_artifact so it shows up in Playground Artifacts panel
    artifact_part = genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    
    # 2. Upload image bytes directly to public GCS bucket (without writing to a local file)
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)
    
    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
    logger.info(f"Uploaded generated dish image to {public_url}")
    return public_url

async def generate_dish_video(
    prompt: str,
    tool_context: ToolContext
) -> str:
    """Generate a short video clip for a food item or recipe using Google's gemini-omni-flash-preview model in the global region.
    
    Saves the video artifact with tool_context.save_artifact for the Playground's Artifacts panel,
    and uploads the video bytes directly to the public Cloud Storage bucket, returning the public HTTPS URL.
    
    Args:
        prompt: Description of the food dish or cooking action to generate (e.g. 'A short video clip of garnishing fresh basil on pasta').
        tool_context: The ADK ToolContext injected automatically by the framework.
        
    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=prompt,
        generation_config={"response_modalities": ["video"]}
    )
    
    video_bytes = None
    mime_type = "video/mp4"
    
    if interaction.output_video and interaction.output_video.data:
        video_bytes = base64.b64decode(interaction.output_video.data)
        mime_type = interaction.output_video.mime_type or "video/mp4"
    elif interaction.outputs:
        for out in interaction.outputs:
            if hasattr(out, "video") and out.video and getattr(out.video, "data", None):
                video_bytes = base64.b64decode(out.video.data)
                mime_type = getattr(out.video, "mime_type", None) or "video/mp4"
                break

    if not video_bytes:
        raise ValueError(f"Failed to generate video bytes for prompt: '{prompt}'.")

    filename = f"dish_video_{uuid.uuid4().hex[:8]}.mp4"
    
    # 1. Save with tool_context.save_artifact so it shows up in Playground Artifacts panel
    artifact_part = genai_types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
    await tool_context.save_artifact(filename=filename, artifact=artifact_part)
    
    # 2. Upload video bytes directly to public GCS bucket (without writing to a local file)
    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(video_bytes, content_type=mime_type)
    
    public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{filename}"
    logger.info(f"Uploaded generated dish video to {public_url}")
    return public_url





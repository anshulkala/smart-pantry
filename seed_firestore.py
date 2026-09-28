import logging
from google.cloud import firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# HARDCODED Project ID as required by Agent Platform guidance
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-02-ac364ded3d24"

def seed_database():
    logger.info(f"Initializing Firestore client for project: {FIRESTORE_PROJECT_ID}")
    db = firestore.Client(project=FIRESTORE_PROJECT_ID)
    
    pantry_items = [
        {
            "name": "Organic Olive Oil",
            "category": "Oils & Condiments",
            "quantity": 1.0,
            "unit": "bottle",
            "expiry_date": "2026-12-31"
        },
        {
            "name": "Arborio Rice",
            "category": "Grains",
            "quantity": 2.0,
            "unit": "kg",
            "expiry_date": "2027-05-15"
        },
        {
            "name": "San Marzano Tomatoes",
            "category": "Canned Goods",
            "quantity": 6.0,
            "unit": "cans",
            "expiry_date": "2027-01-20"
        },
        {
            "name": "Fresh Basil",
            "category": "Produce",
            "quantity": 1.0,
            "unit": "bunch",
            "expiry_date": "2026-10-02"
        },
        {
            "name": "Parmigiano Reggiano",
            "category": "Dairy",
            "quantity": 250.0,
            "unit": "g",
            "expiry_date": "2026-11-10"
        }
    ]
    
    collection_ref = db.collection("pantry_items")
    for item in pantry_items:
        # Use item name as document ID (lowercased & hyphenated)
        doc_id = item["name"].lower().replace(" ", "-")
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(item)
        logger.info(f"Seeded item: {item['name']} ({doc_id})")

    logger.info("Firestore seeding completed successfully!")

if __name__ == "__main__":
    seed_database()

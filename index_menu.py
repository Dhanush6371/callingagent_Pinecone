import os
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI
from menu_data import MENU_ITEMS

load_dotenv()

# Use new index "menudemo"
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("menudemo")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed(text):
    return client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    ).data[0].embedding

def get_hierarchical_metadata(item):
    """
    Maps menu items to hierarchical metadata structure.
    Returns: section, sub_section, protein, dish_type
    """
    category = item["metadata"]["category"]
    item_id = item["id"]
    item_text = item["text"].lower()
    
    # Initialize defaults
    section = None
    sub_section = None
    protein = None
    dish_type = None
    
    # Determine section (veg/non_veg)
    if "veg_" in category or category in ["paneer_appetizer", "paneer_entree", "quick_bites", "chaat", 
                                           "tiffin", "dosa", "puri", "uthappam", "veg_biryani", "veg_pulav",
                                           "house_special", "dessert", "ice_cream", "pastry", "shake",
                                           "hot_beverage", "cold_beverage", "soup", "tandoori"]:
        # Check if it's actually non-veg based on item_id or text
        if any(x in item_id for x in ["chicken", "mutton", "goat", "lamb", "fish", "shrimp", "egg", "kodi", "guddu"]):
            section = "non_veg"
        elif "egg" in category or "chicken" in category or "mutton" in category or "goat" in category or "lamb" in category or "seafood" in category:
            section = "non_veg"
        elif any(x in item_text for x in ["chicken", "mutton", "goat", "lamb", "fish", "shrimp", "egg", "kodi", "guddu", "kheema"]):
            section = "non_veg"
        else:
            section = "veg"
    elif any(x in category for x in ["chicken", "mutton", "goat", "lamb", "seafood", "egg"]):
        section = "non_veg"
    else:
        section = "veg"
    
    # Determine sub_section and dish_type
    if "appetizer" in category:
        sub_section = "appetizer"
        dish_type = "appetizer"
        if "paneer" in category:
            protein = "paneer"
        elif "chicken" in category:
            protein = "chicken"
        elif "mutton" in category:
            protein = "mutton"
        elif "seafood" in category:
            protein = "seafood"
    elif category == "soup":
        sub_section = "soup"
        dish_type = "soup"
        if "chicken" in item_id or "chicken" in item_text:
            protein = "chicken"
    elif category == "tandoori":
        sub_section = "tandoori"
        dish_type = "tandoori"
        if "paneer" in item_id:
            protein = "paneer"
        elif "chicken" in item_id:
            protein = "chicken"
        elif "mutton" in item_id:
            protein = "mutton"
        elif "pomfret" in item_id or "fish" in item_id:
            protein = "seafood"
    elif category == "quick_bites":
        sub_section = "quick_bites"
        dish_type = "quick_bites"
    elif category == "chaat":
        sub_section = "chaat"
        dish_type = "chaat"
        if "kheema" in item_id:
            protein = "mutton"
    elif category == "tiffin":
        sub_section = "tiffin"
        dish_type = "tiffin"
    elif category == "dosa":
        sub_section = "tiffin"
        dish_type = "dosa"
        if "chicken" in item_id:
            protein = "chicken"
        elif "paneer" in item_id:
            protein = "paneer"
        elif "goat" in item_id or "kheema" in item_id:
            protein = "mutton"
    elif category == "puri":
        sub_section = "tiffin"
        dish_type = "puri"
        if "chicken" in item_id:
            protein = "chicken"
        elif "goat" in item_id or "kheema" in item_id:
            protein = "mutton"
    elif category == "uthappam":
        sub_section = "tiffin"
        dish_type = "uthappam"
    elif category == "thali":
        sub_section = "thali"
        dish_type = "thali"
        if "non_veg" in item_id or "non_veg" in item_text:
            protein = "mixed"
    elif "indo_chinese" in category:
        sub_section = "indo_chinese"
        dish_type = "indo_chinese"
        if "egg" in category:
            protein = "egg"
        elif "chicken" in category:
            protein = "chicken"
        elif "kheema" in item_id:
            protein = "mutton"
    elif category == "house_special":
        sub_section = "house_special"
        dish_type = "house_special"
        if "kodi" in item_id or "chicken" in item_id:
            protein = "chicken"
        elif "mamsam" in item_id or "mutton" in item_id:
            protein = "mutton"
    elif "entree" in category:
        sub_section = "entree"
        dish_type = "entree"
        if "paneer" in category:
            protein = "paneer"
        elif "chicken" in category:
            protein = "chicken"
        elif "egg" in category:
            protein = "egg"
        elif "goat" in category:
            protein = "mutton"
        elif "lamb" in category:
            protein = "lamb"
    elif "biryani" in category:
        sub_section = "biryani"
        dish_type = "biryani"
        if "veg" in category:
            if "paneer" in item_id:
                protein = "paneer"
        elif "egg" in category:
            protein = "egg"
        elif "chicken" in category:
            protein = "chicken"
        elif "goat" in category:
            protein = "mutton"
        elif "seafood" in category:
            protein = "seafood"
    elif "pulav" in category:
        sub_section = "pulav"
        dish_type = "pulav"
        if "veg" in category:
            if "paneer" in item_id:
                protein = "paneer"
        elif "egg" in category:
            protein = "egg"
        elif "chicken" in category:
            protein = "chicken"
        elif "goat" in category:
            protein = "mutton"
        elif "seafood" in category:
            protein = "seafood"
    elif category == "side_order":
        sub_section = "side_order"
        dish_type = "side_order"
    elif category == "dessert":
        sub_section = "dessert"
        dish_type = "dessert"
    elif category == "ice_cream":
        sub_section = "dessert"
        dish_type = "ice_cream"
    elif category == "pastry":
        sub_section = "dessert"
        dish_type = "pastry"
    elif category == "shake":
        sub_section = "beverage"
        dish_type = "shake"
    elif category == "hot_beverage":
        sub_section = "beverage"
        dish_type = "hot_beverage"
    elif category == "cold_beverage":
        sub_section = "beverage"
        dish_type = "cold_beverage"
    
    return {
        "section": section,
        "sub_section": sub_section,
        "protein": protein,
        "dish_type": dish_type
    }

vectors = []
print("🔄 Processing menu items and adding hierarchical metadata...")

for i, item in enumerate(MENU_ITEMS):
    # Get hierarchical metadata
    hierarchical = get_hierarchical_metadata(item)
    
    # Merge with existing metadata
    enhanced_metadata = {
        **item["metadata"],
        **hierarchical
    }
    
    vectors.append({
        "id": item["id"],
        "values": embed(item["text"]),
        "metadata": enhanced_metadata
    })
    
    if (i + 1) % 20 == 0:
        print(f"  Processed {i + 1}/{len(MENU_ITEMS)} items...")

print(f"\n📤 Uploading {len(vectors)} vectors to Pinecone index 'menudemo'...")
index.upsert(vectors=vectors)
print("✅ Menu indexed successfully with hierarchical metadata!")
print(f"   - Total items: {len(vectors)}")
print(f"   - Index: menudemo")
print(f"   - Metadata fields: category, price, section, sub_section, protein, dish_type")

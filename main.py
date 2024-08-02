from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from geopy.geocoders import Nominatim
from urllib.parse import quote_plus
import logging
import urllib.parse
import json
from scoring.scoring import get_location_score
from processing.address_geocoder import get_location_from_coords, extract_pincode
from processing.contact import get_top_5_contacts, find_neardear_contacts
from processing.fin_app import read_apps_from_file , match_apps

app = FastAPI()

logging.basicConfig(level=logging.DEBUG)

# MongoDB configuration
mongo_config = {
    "username": "geteazr",
    "password": "Eazr@2024",
    "host": "sample.kuy4nlt.mongodb.net",
    "database": "eazr_DB",
    "segregated_collection": "SegregatedData"
}

# Encode username and password
encoded_username = urllib.parse.quote_plus(mongo_config["username"])
encoded_password = urllib.parse.quote_plus(mongo_config["password"])

# Construct MongoDB URI with encoded username and password
mongo_uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{mongo_config['host']}/{mongo_config['database']}?ssl=true&authSource=admin"

# Function to get location data from coordinates
def get_location_from_coords(latitude, longitude):
    geolocator = Nominatim(user_agent="location_info")
    try:
        location = geolocator.reverse((latitude, longitude), language='en')
        if location:
            address = location.address
            pincode = extract_pincode(address)
            return address, pincode
        else:
            return "Location not found", None
    except Exception as e:
        logging.error("Error:", e)
        return None, None

# Function to extract pincode from address
def extract_pincode(address):
    parts = address.split(',')
    for part in reversed(parts):
        if part.strip().isdigit() and len(part.strip()) == 6:
            return part.strip()
    return None

# Function to connect to MongoDB and get location information for a given user_id
def get_location_info(user_id):
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[mongo_config['database']]
    segregated_collection = db[mongo_config['segregated_collection']]
    
    # Find user_id in segregated data collection
    document = segregated_collection.find_one({"User_ID": user_id})
    
    if document:
        # Extract latitude and longitude from the document
        location = document.get('Location')
        if location:
            latitude = location[0].get('Latitude')
            longitude = location[0].get('Longitude')
            return latitude, longitude
    return None, None

def get_contacts(user_id):
    client = MongoClient(mongo_uri)
    db = client[mongo_config['database']]
    segregated_collection = db[mongo_config['segregated_collection']]
  
    document = segregated_collection.find_one({"User_ID": user_id})
    if document:
        contacts = document.get('Contacts', [{}])[0]
        return contacts
    return None

# Function to get call logs for a given user_id
def get_call_logs(user_id):
    client = MongoClient(mongo_uri)
    db = client[mongo_config['database']]
    segregated_collection = db[mongo_config['segregated_collection']]
    
    document = segregated_collection.find_one({"User_ID": user_id})
    if document:
        call_logs = document.get('CallLogs', [{}])
        return call_logs
    return None

# Function to get top 5 contacts for a given user_id and call logs
def get_top_5_contacts(call_logs):
    if call_logs is None:
        return []
    contacts_count = {}
    for log in call_logs:
        number = log.get('Number')
        if number in contacts_count:
            contacts_count[number] += 1
        else:
            contacts_count[number] = 1
    
    sorted_contacts = sorted(contacts_count.items(), key=lambda x: x[1], reverse=True)
    return sorted_contacts[:5]

# Function to find neardear contacts for a given user_id and call logs
def find_neardear_contacts(call_logs, threshold=3):
    neardear_contacts = []
    if call_logs:
        contacts_count = {}
        for log in call_logs:
            number = log.get('Number')
            if number in contacts_count:
                contacts_count[number] += 1
            else:
                contacts_count[number] = 1
        
        for contact, count in contacts_count.items():
            if count >= threshold:
                neardear_contacts.append((contact, count))
    
    return neardear_contacts
def get_installed_apps(user_id):
    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    # Select the database
    db = client[mongo_config['database']]
    # Select the collection
    segregated_collection = db[mongo_config['segregated_collection']]
    
    # Find the document for the given user_id
    document = segregated_collection.find_one({"User_ID": user_id})
    
    # If the document exists, extract and return the list of installed apps
    if document:
        return [(app['AppName'], app.get('AppID', '')) for app in document.get('InstallApps', [])]
    else:
        return []

# Function to categorize installed apps based on JSON data
def device_apps(installed_apps):
    # Read category information from the JSON file
    with open('sample/fin_app.json', 'r') as file:
        all_categories = json.load(file)

    # Initialize dictionary to store app categories and their counts
    category_counts = {}

    # Flatten all categories into one dictionary
    all_categories_combined = {}
    for main_category, sub_categories in all_categories['categories'].items():
        for category, apps_list in sub_categories.items():
            all_categories_combined[category] = apps_list

    # Initialize counts for each category
    for category in all_categories_combined:
        category_counts[category] = {'count': 0, 'apps': []}

    # Check each installed app against the categories
    for app, app_id in installed_apps:
        for category, apps_list in all_categories_combined.items():
            if app in apps_list:
                category_counts[category]['count'] += 1
                category_counts[category]['apps'].append({'name': app, 'id': app_id})
                break  # Stop searching for categories once the app is found in one category

    return category_counts
@app.get("/")
def read_root():
    return {"Hello": "World"}

# Route to calculate location score
@app.get('/location-score/{user_id}')
def calculate_location_score(user_id: int):
    # Get latitude and longitude from MongoDB
    latitude, longitude = get_location_info(user_id)
    
    if latitude is not None and longitude is not None:
        # Use latitude and longitude to get location data
        address, pincode = get_location_from_coords(latitude, longitude)
        if pincode is not None:
            # Calculate location score using pincode
            location_score = get_location_score(pincode)
            return JSONResponse(content={'User_ID': user_id, 'location_score': location_score}, status_code=200)
        else:
            raise HTTPException(status_code=404, detail='No pincode found for the given coordinates.')
    else:
        raise HTTPException(status_code=404, detail=f"No location information found for user ID: {user_id}")

# Route to calculate contact score
@app.get('/contact-score/{user_id}')
def contact_score(user_id: int):
    # Ensure user_id is an integer
    if not isinstance(user_id, int):
        raise HTTPException(status_code=400, detail='user_id must be an integer.')

    # Get contacts and call logs from MongoDB
    contacts = get_contacts(user_id)
    call_logs = get_call_logs(user_id)

    if call_logs is None:
        raise HTTPException(status_code=404, detail=f"No call logs found for user ID: {user_id}")

    top_5_contacts = get_top_5_contacts(call_logs)

    # Check if call logs and top contacts are retrieved successfully
    if top_5_contacts is not None:
        # Integrate your logic for contact score calculation
        # Dummy implementation, replace with actual logic
        contact_score = 25  # Calculate contact score here
        
        response_data = {
            'User_ID': user_id,
            'Top_5_Contacts': top_5_contacts,
            'Contact_Score': contact_score
        }
        return JSONResponse(content=response_data, status_code=200)
    else:
        raise HTTPException(status_code=404, detail=f"No top contacts found for user ID: {user_id}")

@app.get("/financial-apps-score/{user_id}")
def get_user_installed_apps(user_id: int):
    """API endpoint to get installed apps for a given user ID."""
    installed_apps = get_installed_apps(user_id)
    if not installed_apps:
        raise HTTPException(status_code=404, detail="User not found or no installed apps available.")
    return JSONResponse(content={"installed_apps": installed_apps})

@app.get("/categorize-apps/{user_id}")
def categorize_user_apps(user_id: int):
    """API endpoint to categorize installed apps for a given user ID."""
    installed_apps = get_installed_apps(user_id)
    if not installed_apps:
        raise HTTPException(status_code=404, detail="User not found or no installed apps available.")
    categorized_apps = device_apps(installed_apps)
    return JSONResponse(content={"categorized_apps": categorized_apps})

# Route to calculate location score
@app.get('/location-score/{user_id}')
def calculate_location_score(user_id: int):
    # Get latitude and longitude from MongoDB
    latitude, longitude = get_location_info(user_id)
    
    if latitude is not None and longitude is not None:
        # Use latitude and longitude to get location data
        address, pincode = get_location_from_coords(latitude, longitude)
        if pincode is not None:
            # Calculate location score using pincode
            location_score = get_location_score(pincode)
            return JSONResponse(content={'User_ID': user_id, 'location_score': location_score}, status_code=200)
        else:
            raise HTTPException(status_code=404, detail='No pincode found for the given coordinates.')
    else:
        raise HTTPException(status_code=404, detail=f"No location information found for user ID: {user_id}")

# Run the FastAPI application
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

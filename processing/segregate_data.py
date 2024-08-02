import pymongo
import urllib.parse
import requests
import logging
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

# Configure MongoDB connection
mongo_config = {
    "username": "geteazr",
    "password": "Eazr@2024",
    "host": "sample.kuy4nlt.mongodb.net",
    "database": "eazr_DB",
    "collection_raw": "Data",
    "address_collection": "AddressData",
    "segregated_collection": "SegregatedData"
}

# Encode username and password
encoded_username = urllib.parse.quote_plus(mongo_config["username"])
encoded_password = urllib.parse.quote_plus(mongo_config["password"])

# Construct MongoDB URI with encoded username and password
mongo_uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{mongo_config['host']}/{mongo_config['database']}?ssl=true&authSource=admin"

# Setup MongoDB client
client = pymongo.MongoClient(mongo_uri)
db = client[mongo_config["database"]]

class UserData(BaseModel):
    UserID: str

@app.post("/segregate_data")
async def segregate_data(request: Request, user_data: UserData):
    try:
        # Extract user ID from the request body
        user_id = user_data.UserID

        # Call the API to get the user data
        api_url = f"http://apin.eazr.in/user-permission-data/{user_id}"
        response = requests.get(api_url)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch user data from the API")
        
        api_data = response.json()
        if not api_data.get("UserID"):
            raise HTTPException(status_code=400, detail="User ID not found in the API response")

        # Accessing the collection_raw and segregated_collection
        collection_raw = db[mongo_config['collection_raw']]
        segregated_collection = db[mongo_config['segregated_collection']]

        # Check if the user exists in the segregated collection
        existing_user = segregated_collection.find_one({"User_ID": user_id})

        # Extract SMS data
        sms_cursor = collection_raw.find({"UserID": user_id}, {"Sms": 1})
        sms_list = []
        for sms_data in sms_cursor:
            sms_list.extend(sms_data.get("Sms", []))

        # Extract CallLogs data
        call_logs_cursor = collection_raw.find({"UserID": user_id}, {"CallLogs": 1})
        call_logs_list = []
        for call_logs_data in call_logs_cursor:
            call_logs_list.extend(call_logs_data.get("CallLogs", []))

        # Extract Apps data
        apps_cursor = collection_raw.find({"UserID": user_id}, {"InstallApps": 1})
        apps_list = []
        for apps_data in apps_cursor:
            apps_list.extend(apps_data.get("InstallApps", []))
        
        # Extract DeviceInfo data
        device_info_cursor = collection_raw.find({"UserID": user_id}, {"DeviceInfo": 1})
        device_info_list = []
        for device_info_data in device_info_cursor:
            device_info = {
                "product": device_info_data.get("DeviceInfo", {}).get("product"),
                "model": device_info_data.get("DeviceInfo", {}).get("model"),
                "id": device_info_data.get("DeviceInfo", {}).get("id"),
                "brand": device_info_data.get("DeviceInfo", {}).get("brand"),
                "device": device_info_data.get("DeviceInfo", {}).get("device"),
                "hardware": device_info_data.get("DeviceInfo", {}).get("hardware"),
                "ram": device_info_data.get("DeviceInfo", {}).get("ram"),
                "manufacturer": device_info_data.get("DeviceInfo", {}).get("manufacturer"),
                "hardware": device_info_data.get("DeviceInfo", {}).get("hardware")
            }
            device_info_list.append(device_info)

        if not sms_list and not call_logs_list and not apps_list and not device_info_list:
            raise HTTPException(status_code=404, detail="No SMS, CallLogs, InstallApp, or DeviceInfo data found for the user")

        # Prepare data for insertion into segregated collection
        segregated_data = {
            "User_ID": user_id,
            "SMS": [{
                "Sender": sms.get("address"),
                "Body": sms.get("body"),
                "Date": sms.get("date")
            } for sms in sms_list],
            "CallLogs": [{
                "Name": call.get("name"),
                "Number": call.get("number"),
                "Type": call.get("callType"),
                "Duration": call.get("duration"),
                "Timestamp": call.get("timestamp")
            } for call in call_logs_list],
            "InstallApps": [{"AppName": app} for app in apps_list],
            "DeviceInfo": device_info_list
        }

        # Insert or update segregated data into the new collection
        if segregated_data:
            if existing_user:
                # Update existing document
                segregated_collection.update_one({"User_ID": user_id}, {"$set": segregated_data})
                return JSONResponse(content={"message": "Data updated successfully."}, status_code=200)
            else:
                # Insert new document
                segregated_collection.insert_one(segregated_data)
                return JSONResponse(content={"message": "Data segregated and saved successfully."}, status_code=200)
        else:
            raise HTTPException(status_code=500, detail="Failed to segregate data.")

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the request.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

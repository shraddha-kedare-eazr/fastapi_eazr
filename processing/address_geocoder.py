from geopy.geocoders import Nominatim
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
        print("Error:", e)
        return None, None

# Function to extract pincode from address
def extract_pincode(address):
    parts = address.split(',')
    for part in reversed(parts):
        if part.strip().isdigit() and len(part.strip()) == 6:
            return part.strip()
    return None

from securespot.config import settings
import googlemaps


def get_address_from_latlng(lat, lng, api_key = settings.map_api):
    client = googlemaps.Client(key=api_key)

    try:
        results = client.reverse_geocode((lat, lng))
        if results:
            return results[0].get("formatted_address", "Address not found.")
        else:
            return "No address found."
    except Exception as e:
        return "No address found."

def get_lat_long_from_address(address: str):
    gmaps = googlemaps.Client(key=settings.map_api)
    geocode_result = gmaps.geocode(address)
    if geocode_result:
        location = geocode_result[0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        return None, None



# # Example Usage:
# if __name__ == "__main__":
#     api_key = "AIzaSyA4WeE-BvNOhIA7g3sxQQ_bVlEmGu2adhs"
#     latitude = 37.7749
#     longitude = -122.4194
#
#     address = get_address_from_latlng(latitude, longitude, api_key)
#     print("Address:", address)

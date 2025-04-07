import googlemaps
from datetime import datetime
import re
from securespot.config import settings

def parse_distance(distance_str: str) -> float:
    """
    Convert a distance string (e.g. "4,490 km" or "450 m") to a float value.
    The function removes commas and extracts the numeric part.
    """
    # Extract numeric parts (digits, comma, dot)
    numeric_str_list = re.findall(r"[\d,\.]+", distance_str)
    if not numeric_str_list:
        raise ValueError("No numeric value found in distance string")
    # Remove commas from the first numeric portion
    numeric_str = numeric_str_list[0].replace(",", "")
    # Convert to float and return
    return float(numeric_str)
def get_distance(origin, destination, api_key=settings.map_api):
    # Initialize the client with your API key
    gmaps = googlemaps.Client(key=api_key)

    # Request the distance matrix data
    matrix = gmaps.distance_matrix(
        origins=origin,
        destinations=destination,
        mode='driving',  # You can change this to 'walking', 'bicycling', etc.
        units='metric',  # or 'imperial'
        departure_time=datetime.now()
    )

    try:
        # Extract the relevant information from the response
        element = matrix['rows'][0]['elements'][0]
        if element['status'] == 'OK':
            distance_text = element['distance']['text']
            duration_text = element['duration']['text']
            return parse_distance(distance_text), parse_duration(duration_text)
        else:
            print("Error in response:", element['status'])
            return None, None
    except Exception as e:
        print("Error parsing the response:", e)
        return None, None


def parse_duration(duration_str: str) -> int:
    """
    Convert a duration string (e.g. "1 hour 30 mins" or "45 mins") to a total number of minutes.
    The function handles hours and minutes in the duration string.
    """
    duration_str = duration_str.lower()
    hours = 0
    minutes = 0

    # Extract hours from the string (e.g., "1 hour" or "2 hours")
    hour_match = re.search(r'(\d+)\s*hour', duration_str)
    if hour_match:
        hours = int(hour_match.group(1))

    # Extract minutes from the string (e.g., "30 mins" or "45 min")
    minute_match = re.search(r'(\d+)\s*min', duration_str)
    if minute_match:
        minutes = int(minute_match.group(1))

    # Calculate the total duration in minutes
    total_minutes = hours * 60 + minutes
    return total_minutes
from securespot.database import chats_collection
import google.generativeai as genai
from securespot.config import settings
import googlemaps


class SecureChatbot:
    def __init__(self):
        # Configure the generative AI API and initialize the model.
        genai.configure(api_key=settings.gemini_api)
        self.bottools = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='get_hotels_and_restaurants',
            description="Call this method get_hotels_and_restaurants to find the best hotels and restaurants for the given location. location will be in the form name for example cs cafe, attock name city or country reference is must in location name",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'location': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=['location']
            )
        ),
        genai.protos.FunctionDeclaration(
            name='get_distance',
            description="Call this method get_distance to find the distance and tiem duration for the given origin location to destination location. location will be in the name form for example cs cafe, attock name city or country reference is must in location name for both origin and destination location name",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'origin_location': genai.protos.Schema(type=genai.protos.Type.STRING),
                    'destination_location': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=['origin_location', 'destination_location']
            )
        ),
        genai.protos.FunctionDeclaration(
            name='get_traffic_status',
            description="Call this method to find the traffic status between two location. location will be in the name form for example cs cafe, attock name city or country reference is must in location name for both origin and destination location name",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'origin_location': genai.protos.Schema(type=genai.protos.Type.STRING),
                    'destination_location': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=['origin_location', 'destination_location']
            )
        ),
        genai.protos.FunctionDeclaration(
            name='get_parking',
            description="Call this method get_parking to find the best parking areas for the given location. location will be in the form name for example cs cafe, attock name city or country reference is must in location name",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    'location': genai.protos.Schema(type=genai.protos.Type.STRING),
                },
                required=['location']
            )
        )
    ]
)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", tools=[self.bottools]
        )
        self.context_model = genai.GenerativeModel(
        model_name="gemini-1.5-flash")
        # Initialize the Google Maps client.
        self.gmaps = googlemaps.Client(key=settings.map_api)

    async def get_lat_long_from_address(self, address: str):
        geocode_result = self.gmaps.geocode(address)
        if geocode_result:
            location = geocode_result[0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            return None, None

    async def get_hotels_and_restaurants(self, location, radius=5000):
        restaurants_result = self.gmaps.places_nearby(location=location, radius=radius, type="restaurant")
        restaurants = restaurants_result.get("results", [])
        # Get hotels
        hotels_result = self.gmaps.places_nearby(location=location, radius=radius, type="lodging")
        hotels = hotels_result.get("results", [])

        # Return only the first 5 items if available, otherwise return all.
        restaurants = restaurants[:5] if len(restaurants) > 5 else restaurants
        hotels = hotels[:5] if len(hotels) > 5 else hotels

        return f"""Restaurants: {restaurants}, Hotels: {hotels}"""

    async def get_distance(self, origin, destination, mode="driving"):
        matrix = self.gmaps.distance_matrix(origin, destination, mode=mode, departure_time="now")
        if matrix.get("status") == "OK":
            element = matrix["rows"][0]["elements"][0]
            if element.get("status") == "OK":
                return f"""distance": {element.get("distance", {}).get("text")} and duration: {element.get("duration", {}).get("text")}"""
            else:
                return "error accured due to incorrect name of origin and destination"
        else:
            return "error accured due to incorrect name of origin and destination"

    async def get_traffic_status(self, origin, destination, mode="driving"):
        directions = self.gmaps.directions(origin, destination, mode=mode, departure_time="now")
        if directions:
            leg = directions[0]["legs"][0]
            # Use duration_in_traffic if available; otherwise fallback to duration.
            duration_in_traffic = leg.get("duration_in_traffic", leg.get("duration"))
            distance = leg.get("distance")
            return f"duration_in_traffic: {duration_in_traffic.get('text')} and distance: {distance.get('text')}"
        else:
            return "error: No directions found"

    async def get_parking(self, location, radius=5000):
        parking_result = self.gmaps.places_nearby(location=location, radius=radius, type="parking")
        parking = parking_result.get("results", [])
        return f"Available Parking: {parking}"
    async def get_context_answer(self, context, query):

        prompt = f"""
        fetch the following detail from context {query}
        Context:
        {context}
        """
        response = self.context_model.generate_content(prompt)
        return response.text

    async def get_response(self, question, chat_history):
        # Extended and detailed prompt for SecureBot with updated riding detail service
        prompt = f"""Make sure that your answer should be concise and to the point.
            You are SecureBot, an expert virtual assistant for the SecureSpot project. Your services include riding detail inquiries (calculating distance and travel time between two locations), parking assistance, traffic status updates, and hotel/restaurant recommendations. Your primary goal is to provide accurate, concise, and service-oriented responses to user queries related to these domains.

            Key Guidelines:
            1. If the query is directly related to your core services:
               - For parking queries: Ask the user to provide a location in the format 'location name, city/county' and then call the get_parking method.
               - For riding detail queries (distance calculation and time estimation): Request both the origin and destination locations in the format 'location name, city/county' and then use the get_distance function to calculate the distance and travel time.
               - For traffic status inquiries: Ask for the origin and destination locations in the same format and call the get_traffic_status function.
               - For hotel and restaurant suggestions: Request a location in the specified format and call the get_hotels_and_restaurants method.
            2. If the query is irrelevant to these services:
               - Inform the user politely that you specialize in providing distance calculations, parking assistance, traffic updates, and hotel/restaurant recommendations.
            3. Additional User Interactions:
               - If greeted, respond with a friendly greeting and then guide the user on how to get help with distance calculations or parking services.
               - If asked for your name, respond: "I am SecureBot, created by Sara and Nida."
            4. Maintain clarity and conciseness:
               - Ensure your answers are brief yet informative. Do not repeat the entire prompt or chat history.
               - Use the chat history only if it provides additional context needed to answer the query.

            Example Interaction:
            - User: "I need the riding details."
              SecureBot: "Sure, please provide both the origin and destination locations in the format 'location name, city/county'."
            - User: "Can you find parking near Central Park, New York?"
              SecureBot: "Certainly! Let me find the best parking options for 'Central Park, New York'."

            Remember to reference the provided chat history if it is relevant:
            Chat History:
            {chat_history}

            Now, based on the guidelines above, answer the following query:
            QUESTION: {question}
            """

        # Generate the content based on the extended prompt
        response = self.model.generate_content(prompt)
        parts = response.candidates[0].content.parts
        has_function_call = any(part.function_call for part in parts)

        if has_function_call:
            for part in parts:
                if part.function_call:
                    fc = part.function_call
                    if fc.name == 'get_hotels_and_restaurants':
                        lat_lng = await self.get_lat_long_from_address(fc.args['location'])
                        if lat_lng is None:
                            return 'You have provided an incorrect location.'
                        lat, lng = lat_lng
                        result = await self.get_hotels_and_restaurants(f'{lat}, {lng}')
                        return await self.get_context_answer(result,
                                                             f'get recommended hotels and restaurants in proper format in good and attractive and also consider this {question} while answering')
                    elif fc.name == 'get_distance':
                        org_coords = await self.get_lat_long_from_address(fc.args['origin_location'])
                        if org_coords is None:
                            return 'You have provided an incorrect origin location.'
                        org_lat, org_lng = org_coords
                        dest_coords = await self.get_lat_long_from_address(fc.args['destination_location'])
                        if dest_coords is None:
                            return 'You have provided an incorrect destination location.'
                        dest_lat, dest_lng = dest_coords
                        result = await self.get_distance(f'{org_lat}, {org_lng}', f'{dest_lat}, {dest_lng}')
                        return await self.get_context_answer(result, f'get distance and time duration and also consider this {question} while answering')
                    elif fc.name == 'get_traffic_status':
                        org_coords = await self.get_lat_long_from_address(fc.args['origin_location'])
                        if org_coords is None:
                            return 'You have provided an incorrect origin location.'
                        org_lat, org_lng = org_coords
                        dest_coords = await self.get_lat_long_from_address(fc.args['destination_location'])
                        if dest_coords is None:
                            return 'You have provided an incorrect destination location.'
                        dest_lat, dest_lng = dest_coords
                        result = await self.get_traffic_status(f'{org_lat}, {org_lng}', f'{dest_lat}, {dest_lng}')
                        return await self.get_context_answer(result, f'get the traffic status detail and also consider this {question} while answering')
                    elif fc.name == 'get_parking':
                        lat_lng = await self.get_lat_long_from_address(fc.args['location'])
                        if lat_lng is None:
                            return 'You have provided an incorrect location.'
                        lat, lng = lat_lng
                        result = await self.get_parking(f'{lat}, {lng}')
                        return await self.get_context_answer(result, f'get the parking available detail and also consider this {question} while answering')
        else:
            # If no function call is found, return the first text part.
            for part in parts:
                if part.text:
                    return part.text
            return 'No response; kindly provide proper detail.'

    async def create_chat(self, id: str):
        await chats_collection.insert_one({
            "_id": id,
            "history": []
        })

    async def update_chat(self, id: str, question: str, answer: str):
        await chats_collection.update_one(
            {"_id": id},
            {"$push": {"history": {"question": question, "response": answer}}}
        )

    async def load_chat(self, id: str):
        chat_record = await chats_collection.find_one({"_id": id})
        if chat_record:
            return chat_record.get("history", [])
        return []

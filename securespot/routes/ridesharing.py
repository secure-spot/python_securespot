from fastapi import APIRouter
from bson import ObjectId
from securespot.models import (
    ShareRide,
    RequestRide
)
from securespot.database import (
    ride_offer_collection,
    ride_request_collection,
    user_collection,
    vehicle_collection
)
from securespot.services.googlemap import get_distance
from securespot.services.ridemap import get_lat_long_from_address

router = APIRouter()

ORIGIN_THRESHOLD = 2000  # meters
DESTINATION_THRESHOLD = 2000  # meters


@router.post("/ride_requests")
async def ride_requests_post(data: RequestRide):
    try:
        ride_request_data = data.dict()

        # Look up the user in the user_collection.
        existing_user = await user_collection.find_one({"token": ride_request_data.get("token")})
        if not existing_user:
            return {"status": False, "message": "User not found"}

        user_id = existing_user["_id"]
        ride_request_doc = ride_request_data.copy()

        # Use consistent key name "current_location"
        cur_lat, cur_long = get_lat_long_from_address(ride_request_doc['current_location'])
        if not cur_lat and not cur_long:
            return {"status": False, "message": "Enter a correct current location"}
        des_lat, des_long = get_lat_long_from_address(ride_request_doc['destination_location'])
        if not des_lat and not des_long:
            return {"status": False, "message": "Enter a correct destination location"}

        ride_request_doc.pop("token", None)
        ride_request_doc["user_id"] = user_id

        existing_request = await ride_request_collection.find_one({"user_id": user_id})
        if existing_request:
            return {"status": False, "message": "Already requesting ride"}
        else:
            ride_request_doc["_id"] = str(ObjectId())
            ride_request_doc.setdefault("status", "requesting")
            ride_request_doc.setdefault("sharing", False)
            ride_request_doc.setdefault("share_with", None)
            ride_request_doc.setdefault("cancel_notification", False)
            ride_request_doc.setdefault("complete_notification", False)
            await ride_request_collection.insert_one(ride_request_doc)
            return {"status": True, "message": "Successfully requested ride"}
    except Exception as e:
        return {"status": False, "message": "An error occurred while requesting ride"}


@router.get("/ride_request_status/{token}")
async def status_request_ride(token: str):
    try:
        existing_user = await user_collection.find_one({"token": token})
        if not existing_user:
            return {"status": False}
        user_id = existing_user["_id"]

        existing_request = await ride_request_collection.find_one({"user_id": user_id})
        if existing_request:

            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        return {"status": False}


@router.post("/stop_ride_request/{token}")
async def stop_request_ride(token: str):
    try:
        existing_user = await user_collection.find_one({"token": token})
        if not existing_user:
            return {"status": False, "message": "User not found"}
        user_id = existing_user["_id"]

        existing_request = await ride_request_collection.find_one({"user_id": user_id})
        if existing_request:
            if existing_request['sharing']:
                return {"status": False, "message": "Cannot stop ride; you are sharing a ride with someone"}
            else:
                await ride_request_collection.delete_one({"user_id": user_id})
                return {"status": True, "message": "Ride request stopped and deleted"}
        else:
            return {"status": False, "message": "You have not requested a ride"}
    except Exception as e:
        return {"status": False, "message": f"An error occurred while stopping ride: {str(e)}"}


@router.get("/get_ride_requests/{token}")
async def ride_requests_result(token: str):
    try:
        # Look up the user in the user_collection.
        existing_user = await user_collection.find_one({"token": token})
        if not existing_user:
            return {"status": False, "message": "User not found"}

        user_id = existing_user['_id']
        matching_offers = []
        existing_request = await ride_request_collection.find_one({"user_id": user_id})
        if not existing_request:
            return {"status": False, "message": "You have not requested a ride"}
        else:
            # Search ride_offer_collection for open ride offers.
            async for offer in ride_offer_collection.find({"status": "open"}):
                # Skip if the offer belongs to the same user.
                if offer.get("user_id") == existing_request.get("user_id"):
                    continue

                # Use consistent key name "current_location"
                req_cur_lat, req_cur_long = get_lat_long_from_address(existing_request['current_location'])
                off_cur_lat, off_cur_long = get_lat_long_from_address(offer['current_location'])
                req_des_lat, req_des_long = get_lat_long_from_address(existing_request['destination_location'])
                off_des_lat, off_des_long = get_lat_long_from_address(offer['destination_location'])

                # Calculate distances between request and offer.
                req_origin = f"{req_cur_lat}, {req_cur_long}"
                off_origin = f"{off_cur_lat}, {off_cur_long}"
                req_dest = f"{req_des_lat}, {req_des_long}"
                off_dest = f"{off_des_lat}, {off_des_long}"

                distance_origin, _ = get_distance(req_origin, off_origin)
                distance_destination, _ = get_distance(req_dest, off_dest)

                if (distance_origin is not None and distance_destination is not None and
                        distance_origin <= ORIGIN_THRESHOLD and distance_destination <= DESTINATION_THRESHOLD):
                    # Fetch additional details for the ride offer.
                    offer_user = await user_collection.find_one({"_id": offer.get("user_id")})
                    offer_vehicle = await vehicle_collection.find_one({"user_id": offer.get("user_id")})

                    data_match = {
                        "rider_offer_id": offer["_id"],
                        "name": offer_user.get("name", "Unknown") if offer_user else "Unknown",
                        "vehicle_model": offer_vehicle.get("model", "Unknown") if offer_vehicle else "Unknown",
                        "color": offer_vehicle.get("color", "Unknown") if offer_vehicle else "Unknown",
                        "current_location": offer["current_location"],
                        "destination_location": offer["destination_location"],
                        "available_seats": offer["available_seats"]
                    }
                    matching_offers.append(data_match)

            return {
                "status": True,
                "message": "Successfully retrieved matching offers",
                "matching_offers": matching_offers
            }
    except Exception as e:
        return {"status": False, "message": "An error occurred while getting rides"}


@router.post("/ride_share")
async def create_share_ride(data: ShareRide):
    try:
        existing_user = await user_collection.find_one({"token": data.token})
        if not existing_user:
            return {"status": False, "message": "User not found"}

        existing_vehicle = await vehicle_collection.find_one({"user_id": existing_user['_id']})
        if not existing_vehicle:
            return {"status": False, "message": "Kindly register vehicle for sharing ride"}

        user_id = existing_user["_id"]
        offer_doc = data.dict()

        existing_offer = await ride_offer_collection.find_one({"user_id": user_id})
        if existing_offer:
            return {"status": False, "message": "Cannot share ride; you are already sharing a ride"}
        else:
            offer_doc["_id"] = str(ObjectId())
            offer_doc.pop("token", None)
            offer_doc["user_id"] = user_id
            offer_doc.setdefault("status", "open")
            offer_doc.setdefault("sharing", False)
            offer_doc.setdefault("share_with", None)
            offer_doc.setdefault("available_seats", data.available_seats)
            offer_doc.setdefault("received_requests", [])
            offer_doc.setdefault("cancel_notification", False)
            offer_doc.setdefault("complete_notification", False)
            await ride_offer_collection.insert_one(offer_doc)
        return {"status": True, "message": "Ride shared successfully"}
    except Exception as e:
        return {"status": False, "message": "An error occurred while sharing ride"}


@router.post("/ride_share_status/{token}")
async def status_share_ride(token: str):
    try:
        existing_user = await user_collection.find_one({"token": token})
        if not existing_user:
            return {"status": False}
        user_id = existing_user["_id"]

        existing_offer = await ride_offer_collection.find_one({"user_id": user_id})
        if existing_offer:
            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        return {"status": False}


@router.post("/stop_ride_share/{token}")
async def stop_share_ride(token: str):
    try:
        existing_user = await user_collection.find_one({"token": token})
        if not existing_user:
            return {"status": False, "message": "User not found"}
        user_id = existing_user["_id"]

        existing_offer = await ride_offer_collection.find_one({"user_id": user_id})
        if existing_offer:
            if existing_offer['sharing']:
                return {"status": False, "message": "Cannot stop ride; you are sharing a ride with someone"}
            else:
                await ride_offer_collection.delete_one({"user_id": user_id})
                return {"status": True, "message": "Ride sharing stopped and deleted"}
        else:
            return {"status": False, "message": "You are not sharing a ride"}
    except Exception as e:
        return {"status": False, "message": f"An error occurred while stopping ride: {str(e)}"}

# @router.post("/send_request_ride")
# async def send_request_ride(data: SendRequestRide):
#     try:
#         # Lookup the user by token.
#         existing_user = await user_collection.find_one({"token": data.token})
#         if not existing_user:
#             return {"status": False, "message": "User not found"}
#         user_id = existing_user["_id"]
#
#         existing_offer = await ride_offer_collection.find_one({"_id": data.ride_offer_id})
#         if existing_offer:
#             if user_id in existing_offer.get('received_requests', []):
#                 return {'status': False, "message": 'Already sent request'}
#             else:
#                 result = await ride_offer_collection.update_one(
#                     {"_id": data.ride_offer_id},
#                     {"$push": {"received_requests": user_id}}
#                 )
#                 return {"status": True, "message": "Ride request sent"}
#         else:
#             return {"status": False, "message": "Ride offer does not exist"}
#     except Exception as e:
#         return {"status": False, "message": "An error occurred while sending ride request"}
#
# @router.websocket("/ws/receive_request_ride")
# async def receive_request_ride_ws(websocket: WebSocket):
#     await websocket.accept()
#     try:
#         # Wait for the initial message containing the driver's token.
#         data = await websocket.receive_json()
#         driver_token = data.get("token")
#         if not driver_token:
#             await websocket.send_json({"status": False, "message": "Token not provided"})
#             await websocket.close()
#             return
#
#         # Validate the driver using the token.
#         existing_driver = await user_collection.find_one({"token": driver_token})
#         if not existing_driver:
#             await websocket.send_json({"status": False, "message": "Driver not found"})
#             await websocket.close()
#             return
#         driver_id = existing_driver["_id"]
#
#         # Continuously poll for ride requests.
#         while True:
#             all_requests = []
#             # Look up the ride offer created by this driver.
#             existing_offer = await ride_offer_collection.find_one({"user_id": driver_id})
#             if existing_offer['sharing']:
#                 await websocket.send_json({"status": False, "message": "you are already sharing ride"})
#                 await websocket.close()
#                 return
#
#             if existing_offer:
#                 for passenger_id in existing_offer.get("received_requests", []):
#                     # Fetch the passenger's details.
#                     passenger = await user_collection.find_one({"_id": passenger_id})
#                     # Fetch the ride request corresponding to this passenger.
#                     ride_req = await ride_request_collection.find_one({"user_id": passenger_id})
#                     if ride_req:
#                         req_data = {
#                             "rider_req_id": ride_req["_id"],
#                             "name": passenger.get("name", "Unknown") if passenger else "Unknown",
#                             "current_location": get_address_from_latlng(
#                                 ride_req["current_latitude"],
#                                 ride_req["current_longitude"]
#                             ),
#                             "destination_location": get_address_from_latlng(
#                                 ride_req["destination_latitude"],
#                                 ride_req["destination_longitude"]
#                             )
#                         }
#                         all_requests.append(req_data)
#                 response_data = {
#                     "status": True,
#                     "message": "Ride requests received",
#                     "data": all_requests
#                 }
#             else:
#                 # If no ride offer exists for the driver, inform them.
#                 response_data = {
#                     "status": False,
#                     "message": "Ride offer does not exist"
#                 }
#             await websocket.send_json(response_data)
#             await asyncio.sleep(1)
#     except WebSocketDisconnect:
#         print("Receive ride requests WebSocket disconnected")
#
# @router.post("/respond_request")
# async def response_request(data: ResponseRequestRide):
#     existing_driver = await user_collection.find_one({"token": data.token})
#     if not existing_driver:
#         return {"status": False, "message": "Driver not found"}
#     driver_id = existing_driver["_id"]
#
#     # Look up the ride offer using its _id. Convert string to ObjectId.
#     existing_offer = await ride_offer_collection.find_one({"user_id": driver_id})
#
#     ride_request = await ride_request_collection.find_one({"_id": data.ride_request_id})
#     if not ride_request and existing_offer:
#         return {"status": False, "message":"Ride offer not found"}
#     if ride_request.get("status") != "requesting":
#         return {"status": False, "message": "Rider requesting already accepted"}
#     if existing_offer.get("share_with"):
#         return {"You are already sharing ride with someone"}
#     if data.accept:
#         update_data = {"share_with": data.ride_request_id, "status": "accepted", "sharing": True, "received_requests": []}
#         await ride_offer_collection.update_one({"user_id": driver_id}, {"$set": update_data})
#
#         update_data_request = {"share_with": existing_offer['_id'],
#                        "status": "sharing",
#                        "sharing": True}
#
#         await ride_request_collection.update_one({"_id": data.ride_request_id}, {"$set": update_data_request})
#         return {"status": True, "message": "Ride accepted successfully", "accept": True}
#
#     else:
#
#         await ride_offer_collection.update_one(
#             {"user_id": driver_id},
#             {"$pull": {"received_requests": ride_request['user_id']}}
#         )
#
#         return {"status": True, "message": "Request decline successfully", "accept": False}
#
# @router.post("/receive_reqrespond_notification")
# async def reqrespond_notification(data: RespondRideNotication):
#     existing_driver = await user_collection.find_one({"token": data.token})
#     if not existing_driver:
#         return {"status": False, "message": "Driver not found"}
#     driver_id = existing_driver["_id"]
#
#     ride_request = await ride_request_collection.find_one({"user_id": driver_id})
#     if not ride_request:
#         return {"status": False, "message":"Ride offer not found"}
#     if ride_request.get("status") == "sharing" and ride_request.get("share_with"):
#         existing_rider = await ride_offer_collection.find_one({"_id":ride_request.get("share_with")})
#         existing_driver = await user_collection.find_one({"_id": existing_rider['user_id']})
#         offer_vehicle = await  vehicle_collection.find_one({"user_id": existing_rider['user_id']})
#         data = {
#             "name": existing_driver.get("name", "Unknown") if existing_driver else "Unknown",
#             "vehicle_model": offer_vehicle.get("model", "Unknown") if offer_vehicle else "Unknown",
#             "color": offer_vehicle.get("color", "Unknown") if offer_vehicle else "Unknown",
#             "current_location": get_address_from_latlng(existing_rider["current_latitude"],
#                                                         existing_rider["current_longitude"]),
#             "destination_location": get_address_from_latlng(existing_rider["destination_latitude"],
#                                                             existing_rider["destination_longitude"])}
#         return {"status": True, "message": "request accept", "data":data}
#     else:
#         return {"status": False, "message": "not accept by anyone"}
#
# @router.post("/ridecomplete")
# async def complete_ride_request(data: CompleteRide):
#     existing_user = await user_collection.find_one({"token": data.token})
#     result = await ride_request_collection.update_one(
#         {"_id": ObjectId(data.ride_request_id), "token": data.token},
#         {"$set": {"status": "cancelled"}}
#     )
#     if result.modified_count == 0:
#         raise HTTPException(status_code=404, detail="Ride request not found or already cancelled")
#     return {"Message": "Ride request cancelled successfully"}
#

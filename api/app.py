from fastapi import FastAPI, Request, HTTPException
from datetime import datetime, timedelta
from geopy.geocoders import Nominatim
import requests
import pydantic 
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import re
import motor.motor_asyncio
import pytz

# Initializing the FastAPI application
app = FastAPI()

# Cross-origin resource sharing (CORS) origins
allowed_origins = [
    "https://simple-smart-hub-client.netlify.app",
    "http://localhost:8000"
]

# Adding middleware for the CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setting encoder for ObjectId to be string
pydantic.json.ENCODERS_BY_TYPE[ObjectId] = str

# Initializing MongoDB client using hidden URL
load_dotenv() #Retrieves URL from hidden file
mongo_client = motor.motor_asyncio.AsyncIOMotorClient('MONGODB_STRING')
mongo_db = mongo_client.iot_platform
sensor_collection = mongo_db['sensor_readings']
data_collection = mongo_db['data']

# Initialize Nominatim API
location_service = Nominatim(user_agent="MyApp")
location_info = location_service.geocode("Hyderabad")

# Function to get sunset time
def get_sunset_time():
    lat =  location_info.latitude
    lon = location_info.longitude
    api_endpoint = f'https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}'
    api_response = requests.get(api_endpoint)
    api_data = api_response.json()
    sunset_time = datetime.strptime(api_data['results']['sunset'], '%I:%M:%S %p').time()
    return datetime.strptime(str(sunset_time),"%H:%M:%S")

# Regex for time string
time_regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

# Function to parse time string
def parse_time_str(time_str):
    matched_parts = time_regex.match(time_str)
    if not matched_parts:
        return
    parts_dict = matched_parts.groupdict()
    time_values = {}
    for part_name, part_value in parts_dict.items():
        if part_value:
            time_values[part_name] = int(part_value)
    return timedelta(**time_values)

# Default route
@app.get("/")
async def root():
    return {"message": "This that ECSE3038 IOT Project Mayne!"}

# Route to get graph data
@app.get('/graph')
async def graph(request: Request):
    entry_limit = int(request.query_params.get('size'))
    graph_entries = await data_collection.find().sort('_id', -1).limit(entry_limit).to_list(entry_limit)
    response_data = []
    for entry in graph_entries:
        temperature = entry.get("temperature")
        presence = entry.get("presence")
        entry_time = entry.get("current_time")
        response_data.append({
            "temperature": temperature,
            "presence": presence,
            "datetime": entry_time
        })
    return response_data

# Route to put sensor readings
@app.put('/settings')
async def put_sensor_readings(request: Request):
    state_dict = await request.json()
    user_temperature = state_dict["user_temp"]
    user_light_time = state_dict["user_light"]
    light_duration = state_dict["light_duration"]

    if user_light_time == "sunset":
        light_time_scr = get_sunset_time()
    else:
        light_time_scr = datetime.strptime(user_light_time, "%H:%M:%S")
        updated_light_time = light_time_scr + parse_time_str(light_duration)

    output_data = {
        "user_temp": user_temperature,
        "user_light": str(light_time_scr.time()),
        "light_time_off": str(updated_light_time.time())
    }

    obj_found = await sensor_collection.find().sort('_id', -1).limit(1).to_list(1)

    if obj_found:
        await sensor_collection.update_one({"_id": obj_found[0]["_id"]}, {"$set": output_data})
        new_obj = await sensor_collection.find_one({"_id": obj_found[0]["_id"]})
    else:
        new_entry = await sensor_collection.insert_one(output_data)
        new_obj = await sensor_collection.find_one({"_id": new_entry.inserted_id})
    return new_obj

# Route to put temperature
@app.put("/temperature")
async def update_temperature(request: Request): 
    state_dict = await request.json()

    last_param = await sensor_collection.find().sort('_id', -1).limit(1).to_list(1)
    user_temperature = last_param[0]["user_temp"]   
    user_light_time = datetime.strptime(last_param[0]["user_light"], "%H:%M:%S")
    light_off_time = datetime.strptime(last_param[0]["light_time_off"], "%H:%M:%S")

    current_time = datetime.now(pytz.timezone('Jamaica')).time()
    current_time_parsed = datetime.strptime(str(current_time),"%H:%M:%S.%f")

    state_dict["light"] = ((current_time_parsed < user_light_time) and (current_time_parsed < light_off_time ) & (state_dict["presence"] == "1" ))
    state_dict["fan"] = ((float(state_dict["temperature"]) >= user_temperature) & (state_dict["presence"]=="1"))
    state_dict["current_time"]= str(datetime.now())

    new_entry = await data_collection.insert_one(state_dict)
    new_obj = await data_collection.find_one({"_id":new_entry.inserted_id}) 
    return new_obj

# Route to get current state
@app.get("/state")
async def get_state():
    last_entry = await data_collection.find().sort('_id', -1).limit(1).to_list(1)

    if not last_entry:
        return {
            "presence": False,
            "fan": False,
            "light": False,
            "current_time": datetime.now()
        }

    return last_entry[0]  # return the first (and only) element in the list


from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from os import access
from datetime import datetime, timedelta
import time
import math
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration
from flask import Flask
# Get your token, don't change client pip instID and client secret
oauth_client = BackendApplicationClient(client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3")
token_url = "https://api2.arduino.cc/iot/v1/clients/token"
oauth = OAuth2Session(client=oauth_client)
token = oauth.fetch_token(
	token_url=token_url,
	client_id="967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3",
	client_secret="IzJKMUUnl09D1aTZQoYWxu31PpmKH1JLPPWVMBliDCet0aClF0MWXF5hGnuZH5c7",
	include_client_id=True,
	audience="https://api2.arduino.cc/iot",
)

# store access token in access_token variable
access_token = token.get("access_token")
# configure and instance the API client with our access_token
client_config = iot.Configuration(host="https://api2.arduino.cc/iot")
client_config.access_token = access_token
api = None
thing_id = None
with iot.ApiClient(client_config) as client:
	# Create an instance of the API class
	api = iot.PropertiesV2Api(client)
	thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824" # iPhone thing
	# thing_id = "a798decb-21e5-4b5f-a659-f4941437ae8f" # test_thing
# client = iot.ApiClient(client_config)

# Change this based on the device being used
# thing_id = "95f40050-a59d-4624-80b2-01d27ebbb824"

# Custom variables for debugging
looping = True # whether the program continuously fetches data in a loop
minutes_ago = 1 # how far back in time should the program fetch data, more minutes means longer fetch time
sleep_duration = float(5) # how many seconds should the program wait before fetching again

# init data for Properties API interactions
# api = iot.PropertiesV2Api(client)
prev_time_record = datetime.min # reset prev_time_record

# Change these property IDs based on info in the Thing setup page
gps_id = "a058906f-caad-465b-96d3-da1981e81be7"
gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146"
acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5"

property_id = gps_id
#final output
max_velocity = 0
average_velocity = 0
total_distance = 0
total_calorie_burnt = 0
coordinates =[]
velocity = []
def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
	
    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon1_rad - lon1_rad
	
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
	
    # Distance in kilometers
    distance_km = R * c
    # Convert distance to meters
    distance_m = distance_km * 1000
    return distance_m


first_fetch = True
interval_length = 0
previous_time = 0
while (True):
	try:
		now_time = datetime.now()
		if first_fetch == False:
			if now_time.second < previous_time.second:
				interval_length = now_time.second + 60 + (now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000)
			else:
				interval_length = now_time.second + (now_time.microsecond/1000000) - previous_time.second - (previous_time.microsecond/1000000)
			# interval length, not finished, datetime type issue
		previous_time = now_time
		print(f"Now:\t{now_time}")
		prev_time = now_time + timedelta(minutes=-minutes_ago)
		print(f"{minutes_ago} mins ago:\t{prev_time}")
		formatted_month = ('00' + str(prev_time.month))[-2:]
		formatted_date = ('00' + str(prev_time.day))[-2:]
		formatted_hour = ('00' + str(prev_time.hour - 7))[-2:]
		formatted_minute = ('00' + str(prev_time.minute))[-2:]
		formatted_second = ('00' + str(prev_time.second))[-2:]
		formatted_time = str(prev_time.year) + '-' + formatted_month + '-' + formatted_date + 'T' + formatted_hour + ':' + formatted_minute + ':' + formatted_second + 'Z'
		print(f"Formatted:\t{formatted_time}")

		# resp = api.properties_v2_list(thing_id)
		resp = api.properties_v2_show(thing_id, gps_id)
		# resp = api.properties_v2_timeseries(thing_id, property_id, desc=True, _from=formatted_time, interval=1)
		# if (len(resp.data) > 0):
		# 	print(f"Batch size: {len(resp.data)}")
		# 	if (resp.data[0].time != prev_time_record):
		# 		prev_time_record = resp.data[0].time
		# 		print(resp.data[0])
		# 	else:
		# 		print("No new records since last fetch")
		# else:
		# 	print(f"No records in last {minutes_ago} minutes")
		# print(resp)
		print(f"{resp.value_updated_at}\tGyroscope_X: {resp.last_value}")
		coordinates.append(tuple((resp._last_value['lat'],resp._last_value['lon'])))
		if first_fetch == True:
			first_fetch = False
		else:
			distance = haversine(coordinates[len(coordinates)-2][0],coordinates[len(coordinates)-2][1],coordinates[len(coordinates)-1][0],coordinates[len(coordinates)-1][0])
			total_distance += distance
			current_velocity = distance / interval_length
			max_velocity = max(max_velocity,current_velocity)
			velocity.append(current_velocity)
			print(current_velocity)
			print(distance)
			print(interval_length)
	except ApiException as e:
		print("Got an exception: {}".format(e))
	if len(velocity) >= 4:
		if coordinates[-1] == coordinates[-2] and coordinates[-2] == coordinates[-3]:
			break
	print()
	time.sleep(sleep_duration)
print(max_velocity)
sum = 0
for i in range(0,len(velocity)-2):
	sum+=i
average_velocity = sum / len(velocity)
print(average_velocity)
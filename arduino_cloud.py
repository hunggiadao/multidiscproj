from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from os import access
from datetime import datetime, timedelta, timezone
import time
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration
import math
from threading import Thread, Event
from time import sleep


# running_sessions = [
# 	# {'datetime': '18/06/2024', 'duration': '23', 'distance': 5, 'avg': '1.2', 'max': '2', 'calories': 300},
# 	# {'datetime': '18/06/2024', 'duration': '32432', 'distance': 10, 'avg': '3.4', 'max': '4', 'calories': 600},
# 	# {'datetime': '18/06/2024', 'duration': '485935', 'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
# 	# {'datetime': '18/06/2024', 'duration': '485935', 'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
# 	# {'datetime': '18/06/2024', 'duration': '485935', 'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
# 	# {'datetime': '18/06/2024', 'duration': '485935', 'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
# 	# {'datetime': '18/06/2024', 'duration': '485935', 'distance': 7, 'avg': '2.1', 'max': '3', 'calories': 450},
# ]
session_done = Event()
# mph, kmph, MET
met_table = [(1.0, 1.6, 2.0),
						 (1.7, 2.7, 2.3),
						 (2.0, 3.2, 2.8),
						 (2.5, 4.0, 3.0),
						 (3.0, 4.8, 3.3),
						 (3.5, 5.6, 3.8),
						 (4.0, 6.4, 5.0),
						 (4.5, 7.2, 7.0),
						 (5.0, 8.0, 8.3),
						 (5.2, 8.4, 9.0),
						 (6.0, 9.7, 9.8),
						 (6.7, 10.8, 10.5),
						 (7.0, 11.3, 11.0),
						 (7.5, 12.1, 11.5),
						 (8.0, 12.9, 11.8),
						 (8.6, 13.8, 12.3),
						 (9.0, 14.5, 12.8),
						 (10.0, 16.1, 14.5),
						 (10.9, 17.5, 16.0),
						 (11.5, 18.5, 18.0),
						 (12.0, 19.3, 19.0),
						 (12.5, 20.1, 19.8),]

def get_met_from_kmph(kmph):
	if (kmph < met_table[0][1]):
		# if speed is below minimum, set to minimum
		return met_table[0][2]
	
	lower = 0
	upper = 0
	for i in range(0, len(met_table)):
		if (met_table[i][1] <= kmph):
			lower = met_table[i][1]
		else:
			upper = met_table[i][1]
			percentage = (kmph - lower) / (upper - lower)
			met = met_table[i - 1][2] + percentage * (met_table[i][2] - met_table[i - 1][2])
			return met
	# for speed demons, needs tuning
	return met_table[len(met_table) - 1][2]

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
		dlon = lon2_rad - lon1_rad

		# Haversine formula
		a = math.pow(math.sin(dlat / 2), 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.pow(math.sin(dlon / 2), 2)
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

		# Distance in kilometers
		distance_km = R * c
		# Convert distance to meters
		distance_m = distance_km * 1000
		return distance_m

def formatted_time_return(puttime):
	# if (type(puttime) != type(datetime.datetime)):
	# 	raise TypeError(f"{puttime} attribute must be set to an instance of datetime.datetime")
	formatted_month = ('00' + str(puttime.month))[-2:]
	formatted_date = ('00' + str(puttime.day))[-2:]
	formatted_hour = ('00' + str(puttime.hour - 7))[-2:]
	formatted_minute = ('00' + str(puttime.minute))[-2:]
	formatted_second = ('00' + str(puttime.second))[-2:]
	formatted_time = str(puttime.year) + '-' + formatted_month + '-' + formatted_date + 'T' + formatted_hour + ':' + formatted_minute + ':' + formatted_second + 'Z'
	# print(f"Formatted:\t{formatted_time}")
	return formatted_time

def start_session(running_sessions, weight):
	# Get your token, don't change client ID and client secret
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

	# Custom variables for debugging
	looping = True # whether the program continuously fetches data in a loop
	minutes_ago = 0 # how far back in time should the program fetch data, more minutes means longer fetch time
	sleep_duration = float(1) # how many seconds should the program wait before fetching again
	inactiv_timeout = 15 # how many seconds until timeout due to inactivity

	# init data for Properties API interactions
	# api = iot.PropertiesV2Api(client)

	# Change these property IDs based on info in the Thing setup page
	gps_id = "a058906f-caad-465b-96d3-da1981e81be7"
	gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146"
	acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5"
	property_id = gps_id

	# final output
	max_velocity = 0
	average_velocity = 0
	total_distance = 0
	total_time = 0
	total_calories = 0
	coordinatestamps = []
	velocity = []
	duration_list = []
	first_fetch = True
	interval_length = 0
	interval_length_for_sum = 0
	interval_length_for_list = 0
	previous_time = 0

	# reset prev_record_time
	now_time = datetime.now(timezone.utc)
	resp = api.properties_v2_show(thing_id, gps_id)
	prev_record_time = resp._value_updated_at
	if (prev_record_time < now_time):
		prev_record_time = now_time

	while (True):
		try:
			now_time = datetime.now(timezone.utc)
			print(f"Now:\t{now_time}")
			buffer_time = now_time + timedelta(minutes=-minutes_ago)
			# print(f"{minutes_ago} mins ago:\t{buffer_time}")
			formatted_time = formatted_time_return(buffer_time)
			print(f"Formatted:\t{formatted_time}")

			# resp = api.properties_v2_list(thing_id)
			resp = api.properties_v2_show(thing_id, gps_id)
			# print(type(resp._value_updated_at))

			if (resp._value_updated_at > prev_record_time):
				# new record found
				prev_record_time = resp._value_updated_at
				last_val = resp._last_value
				# print(f"{last_val}")
				# print(type(last_val))
				print(f"{last_val['lat']} {last_val['lon']}")
				# print(f"{type(last_val['lat'])} {type(last_val['lon'])}")
				coordinatestamps.append({'timestamp':resp._value_updated_at, 'lat':resp._last_value['lat'], 'lon':resp._last_value['lon']})
				if (len(coordinatestamps) > 1):
					distance = haversine(coordinatestamps[len(coordinatestamps)-2]['lat'], coordinatestamps[len(
							coordinatestamps)-2]['lon'], coordinatestamps[len(coordinatestamps)-1]['lat'], coordinatestamps[len(coordinatestamps)-1]['lon'])
					delta = (coordinatestamps[len(coordinatestamps)-1]['timestamp'] - coordinatestamps[len(coordinatestamps)-2]['timestamp']).total_seconds()
					current_velocity = distance / (delta + 0.000001) # to prevent division by 0
					total_distance += distance
					total_time += delta
					max_velocity = max(max_velocity, current_velocity)
					# velocity.append(current_velocity)
					# duration_list.append(interval_length_for_list)
					# print(current_velocity)
					# print(distance)
					# print(delta)
			else:
				# no new records found
				print("No new records since last fetch")
				delta = now_time - prev_record_time
				print(f"now: {now_time} {type(now_time)}")
				print(f"prev: {prev_record_time} {type(prev_record_time)}")
				print(f"{delta.total_seconds()} {type(delta.total_seconds())}")
				if (delta.total_seconds() > inactiv_timeout):
					# finish session due to inactivity
					print(f"No action in the last {inactiv_timeout}s, quitting")
					average_velocity = total_distance / (total_time + 0.000001) # to prevent division by 0
					average_velocity_kmph = average_velocity * 3.6
					met = get_met_from_kmph(average_velocity_kmph)
					# Calories Burned=MET×Weight (kg)×Duration (hours)
					total_calories = met * weight * total_time / 3600
					now_time = now_time + timedelta(hours=7)
					session_dict = {
						'datetime': now_time.strftime("%d-%m-%Y %H:%M:%S"),
						'duration': round(total_time, 1),
						'distance': round(total_distance, 2),
						'avg': round(average_velocity, 3),
						'max': round(max_velocity, 3),
						'calories': round(total_calories, 3)
					}
					running_sessions.append(session_dict)
					# session_done.set()
					return

			# this code is used for timeseries
			# resp = api.properties_v2_timeseries(thing_id, property_id, desc=True, _from=formatted_time, interval=1)
			# if (len(resp.data) > 0):
			# 	print(f"Batch size: {len(resp.data)}")
			# 	if (resp.data[0].time != prev_record_time):
			# 		prev_record_time = resp.data[0].time
			# 		print(resp.data[0])
			# 	else:
			# 		print("No new records since last fetch")
			# else:
			# 	print(f"No records in last {minutes_ago} minutes")
				
			# print(resp)
			# print(f"{resp.value_updated_at}\tGyroscope_X: {resp.last_value}")
			
		except ApiException as e:
			print("Got an exception: {}".format(e))

		if (not looping):
			break
		print()
		time.sleep(sleep_duration)

if __name__ == "__main__":
	# main()
	# start_session(running_sessions)
	pass
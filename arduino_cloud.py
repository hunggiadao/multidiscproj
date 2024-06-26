from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from os import access
from datetime import datetime, timedelta
import time
import iot_api_client as iot
from iot_api_client.rest import ApiException
from iot_api_client.configuration import Configuration

def formatted_time_return(puttime):
	# if (type(puttime) != type(datetime.datetime)):
	# 	raise TypeError(f"{puttime} attribute must be set to an instance of datetime.datetime")
	formatted_month = ('00' + str(buffer_time.month))[-2:]
	formatted_date = ('00' + str(buffer_time.day))[-2:]
	formatted_hour = ('00' + str(buffer_time.hour - 7))[-2:]
	formatted_minute = ('00' + str(buffer_time.minute))[-2:]
	formatted_second = ('00' + str(buffer_time.second))[-2:]
	formatted_time = str(buffer_time.year) + '-' + formatted_month + '-' + formatted_date + 'T' + formatted_hour + ':' + formatted_minute + ':' + formatted_second + 'Z'
	return formatted_time
	print(f"Formatted:\t{formatted_time}")

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

# init data for Properties API interactions
# api = iot.PropertiesV2Api(client)
prev_time_record = datetime.min # reset prev_time_record

# Change these property IDs based on info in the Thing setup page
gps_id = "a058906f-caad-465b-96d3-da1981e81be7"
gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146"
acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5"

property_id = gps_id

while (True):
	try:
		now_time = datetime.now()
		print(f"Now:\t{now_time}")
		buffer_time = now_time + timedelta(minutes=-minutes_ago)
		# print(f"{minutes_ago} mins ago:\t{buffer_time}")
		formatted_time = formatted_time_return(buffer_time)
		print(f"Formatted:\t{formatted_time}")

		# resp = api.properties_v2_list(thing_id)
		resp = api.properties_v2_show(thing_id, gps_id)
		# print(type(resp._value_updated_at))
		if (resp._value_updated_at != prev_time_record):
			# new record found
			prev_time_record = resp._value_updated_at
			last_val = resp._last_value
			# print(f"{last_val}")
			# print(type(last_val))
			print(f"{last_val['lat']} {last_val['lon']}")
			# print(f"{type(last_val['lat'])} {type(last_val['lon'])}")
		else:
			print("No new records since last fetch")

		# this code is used for timeseries
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
		# print(f"{resp.value_updated_at}\tGyroscope_X: {resp.last_value}")
		
	except ApiException as e:
		print("Got an exception: {}".format(e))

	if (not looping):
		break
	print()
	time.sleep(sleep_duration)
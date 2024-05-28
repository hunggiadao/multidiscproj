var IotApi = require('@arduino/arduino-iot-client');
var rp = require('request-promise');

async function getToken() {
    var options = {
        method: 'POST',
        url: 'https://api2.arduino.cc/iot/v1/clients/token',
        headers: { 'content-type': 'application/x-www-form-urlencoded' },
        json: true,
        form: {
            grant_type: 'client_credentials',
            client_id: '967VT2YXvzhTjgPr7YqJnwpx4gv9LPj3',
            client_secret: 'IzJKMUUnl09D1aTZQoYWxu31PpmKH1JLPPWVMBliDCet0aClF0MWXF5hGnuZH5c7',
            audience: 'https://api2.arduino.cc/iot'
        }
    };

    try {
        const response = await rp(options);
        return response['access_token'];
    }
    catch (error) {
        console.error("Failed getting an access token: " + error)
    }
}

async function printProperties() {
	var client = IotApi.ApiClient.instance;
	// Configure OAuth2 access token for authorization: oauth2
	var oauth2 = client.authentications['oauth2'];
	oauth2.accessToken = await getToken();

	var api = new IotApi.PropertiesV2Api(client)
	var id = "95f40050-a59d-4624-80b2-01d27ebbb824"; // {String} The id of the thing

	// Change these property IDs based on info in the Thing setup page
	var gps_id = "a058906f-caad-465b-96d3-da1981e81be7";
	var gyro_x_id = "9a0023b7-4e8c-4d87-b388-30b481ca8146";
	var acc_linear_id = "16d6ec74-c599-4386-b3a2-ec71fcf8e5b5";
	var property_id = acc_linear_id;

	// var opts = {
	// 	'showDeleted': true // {Boolean} If true, shows the soft deleted properties
	// };
	// api.propertiesV2Show(id, property_id, opts).then(function(data) {
	// 	console.log(data);
	// });
	// api.propertiesV2List(id, opts).then(function(data) {
	// 	console.log(data);
	// });
	var opts = {
		// 'aggregation': aggregation_example, // {String} Samples aggregation statistic. Supported aggregations AVG|MAX|MIN|COUNT|SUM|PCT_99|PCT_95|PCT_90|PCT_75|PCT_50|PCT_15|PCT_5
		'desc': true, // {Boolean} Whether data's ordering (by time) should be descending
		'from': "2024-05-27T00:00:00Z", // {String} Get data with a timestamp >= to this date (default: 2 weeks ago, min: 1842-01-01T00:00:00Z, max: 2242-01-01T00:00:00Z)
		'interval': 10, // {Integer} Binning interval in seconds (defaut: the smallest possible value compatibly with the limit of 1000 data points in the response)
		// 'to': to_example, // {String} Get data with a timestamp < to this date (default: now, min: 1842-01-01T00:00:00Z, max: 2242-01-01T00:00:00Z)
		// 'xOrganization': xOrganization_example // {String} The id of the organization
	};
	var data = api.propertiesV2Timeseries(id, property_id, opts).then(function(data) {
		console.log('API called successfully. Returned data: ' + data);
	}, function(error) {
		console.error(error);
	});
}

printProperties();
// setInterval(function() {printProperties()}, 1000);

import requests, json
from classHandler import Handler


# weather report uses an api to send weather to the flask interface
class weather_report():
    def __init__(self, city_name, weather_key):
        # city name and weather key come from config database.
        self.city_name = city_name
        self.weather_key = weather_key
        # API needs gps coordinates so city has to be passed to get_gps
        gps = self.get_gps(self.city_name)
        self.longitude = gps[0] or -74.0060152
        self.latitude = gps[1] or 40.7127281
        self.city = gps[2] or "New York"
        self.state = gps[3] or "NY"
        self.country = gps[4] or "US"
        # Once gps is retrieved a second call to get_weather is performed
        self.assign()
        # config database is updated with changes to match new city
        self.update_config()


    # Get gps passes city to return long and lat
    def get_gps(self,city):
        try:
            # requests api response
            GPS_response = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={self.weather_key}").json()
            #print(GPS_response)
            if not GPS_response:
                print(f"WARNING: No results found for city '{city}'. Using default (New York City).")
                # Returns usable list with default data sets
                return [-74.0060152, 40.7127281, "New York", "NY", "US"]
            try:
                # Extract list and dictionary to get usable data.
                country = GPS_response[0].get('country', 'US')
                state = GPS_response[0].get('state', '')
                name = GPS_response[0].get('name', city)
                lon = GPS_response[0].get('lon', -74.0060152)
                lat = GPS_response[0].get('lat', 40.7127281)
            except (IndexError, KeyError) as e:
                print(f"ERROR: weather.get_gps >>> data parsing >>> {e}")
                return [-74.0060152, 40.7127281, "New York", "NY", "US"]
            # return a list
            return [lon, lat, name, state, country]
        
        except requests.exceptions.RequestException as e:
            print("ERROR: weather.get_gps >>> api request >>>", e)
            # Returns usable list with default data sets
            return [-74.0060152, 40.7127281, "New York", "NY", "US"]
    

    #Get weather makes second call to the api for detailed weather 
    def get_weather(self):
        # api call uses gps coordinates from get gps
        try: 
            WEATHER_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.weather_key}").json()
        except requests.exceptions.RequestException as e:
            print("ERROR: weather.get_weather >>> api request >>>", e)
            WEATHER_response = self.error_data()
        print(WEATHER_response)
        # Returns full dict
        return WEATHER_response
    

    # update config sends gps city and country data to the config database
    def update_config(self):
        conn = Handler(profile="user")
        conn.update_database("config_database", "key", "value", "city", self.city)
        conn.update_database("config_database", "key", "value", "lon", self.longitude)
        conn.update_database("config_database", "key", "value", "lat", self.latitude)
        conn.update_database("config_database", "key", "value", "country", self.country)
    
    # Weather direction translates degrees returned from api to cardinal directions.
    def wind_direction(self, wind_dir):
        try:
            wind_float = float(wind_dir)
            if wind_float in range(23, 66): cardinal = 'NE'
            elif wind_float in range(67, 112): cardinal = 'E'
            elif wind_float in range(113, 156): cardinal = 'SE'
            elif wind_float in range(157, 202): cardinal = 'S'
            elif wind_float in range(203, 246): cardinal = 'SW'
            elif wind_float in range(247, 292): cardinal = 'W'
            elif wind_float in range(293, 336): cardinal = 'NW'
            else: cardinal = 'N' # 0-22 and 337-360
        except: 
            # returns a blank string
            cardinal = " "
            print("ERROR: (wind_direction) assigning >>> wind_dir")
        # print("CF --- wind_direction RUN")
        return cardinal
    

    def assign(self):
        try:
            data = self.get_weather()
            # Check if we got a valid response with weather data
            if 'weather' not in data or 'main' not in data:
                print(f"ERROR: Invalid weather API response: {data}")
                data = self.error_data()
        except Exception as e:
            print("ERROR: weather.__init__ >>> get_weather >>>", e)
            data = self.error_data()
        
        # response is formatted for direct output.
        try:
            self.description = data['weather'][0]['description'].title()
            self.icon = data['weather'][0]['icon']
            if not self.icon.endswith('.png'):
                self.icon += ".png"
            self.feel = int((data['main']['feels_like']) * 1.8 - 459.67)
            min_temp = int((data['main']['temp_min']) * 1.8 - 459.67)
            max_temp = int((data['main']['temp_max']) * 1.8 - 459.67)
            self.temp = f"{min_temp} - {max_temp}"
            self.humid = data['main']['humidity']
            self.clouds = data['clouds']['all']
            dir = self.wind_direction(data['wind']['deg'])
            self.wind = f"{dir} {int(data['wind']['speed'])}mp/h"
        except (KeyError, TypeError, ValueError) as e:
            print(f"ERROR: weather.__init__ >>> parsing weather data >>> {e}")
            # Set default error values
            self.description = "API Error"
            self.icon = "01d.png"
            self.feel = "N/A"
            self.temp = "N/A"
            self.humid = "N/A"
            self.clouds = "N/A"
            self.wind = "N/A"
        stored_weather = {"description": self.description, "icon":self.icon, "feel":self.feel, "temp":self.temp,"humid":self.humid, "clouds":self.clouds,"wind":self.wind}
        if stored_weather["description"] is not "API Error":
            user_handle = Handler("user")
            user_handle.send_command("DELETE FROM weather_database")
            for k,v in stored_weather.items():
                user_handle.send_command("INSERT INTO weather_database (key, value) VALUES %s, %s", (k,v))
        else:
            print("Error: Using old database values for weather")


    def error_data(self):
        return {
            "weather": [
                {
                    "description": "API Error",
                    "icon": "01d"
                }
            ], 
            "main": {   
                "feels_like": 255.372,
                "temp_min": 255.372,
                "temp_max": 255.372,
                "humidity": 0
            },
            "clouds": {
                "all": 0
            },
            "wind": {
                "deg": 0,
                "speed": 0
            }
        } 
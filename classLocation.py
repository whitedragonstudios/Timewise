import requests
from classHandler import Handler


class Change_City():
    def __init__(self, city_name, autorun = True):
        # city name and weather key come from config database.
        self.city_name = city_name or "New York"
        self.user_handle = Handler("user")
        if autorun:
            wk = self.user_handle.send_query("SELECT value FROM config_database WHERE key = 'weather_key';")
            print("here",wk)
            self.weather_key = wk[0][0]
            gps = self.get_gps(self.city_name)
            print(gps)
            self.update_config(*gps)


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
                return (-74.0060152, 40.7127281, "New York", "NY", "US")
            # return a list
            return (lon, lat, name, state, country)
        
        except requests.exceptions.RequestException as e:
            print("ERROR: weather.get_gps >>> api request >>>", e)
            # Returns usable list with default data sets
            return [-74.0060152, 40.7127281, "New York", "NY", "US"]
    

    # update config sends gps city and country data to the config database
    def update_config(self, long, lat, city, state, country):
        self.user_handle.update_database("config_database", "key", "value", "lon", long)
        self.user_handle.update_database("config_database", "key", "value", "lat", lat)
        self.user_handle.update_database("config_database", "key", "value", "city", city)
        self.user_handle.update_database("config_database", "key", "value", "state", state)
        self.user_handle.update_database("config_database", "key", "value", "country", country)
        self.user_handle.update_database("updates_database", "key", "value", "weather", "NOW()")


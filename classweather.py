import requests
from classHandler import Handler


# weather report uses an api to send weather to the flask interface
class Update_Weather():
    def __init__(self, autorun = True):
        self.user_handle = Handler("user")
        db = self.user_handle.send_query(
            "SELECT value FROM config_database WHERE key IN ('weather_key', 'lon', 'lat', 'city', 'state', 'country') ORDER BY key;"
        )
        self.city = db[0][0]        # city
        self.country = db[1][0]     # country
        self.latitude = db[2][0]    # lat
        self.longitude = db[3][0]   # lon
        self.state = db[4][0]       # state
        self.weather_key = db[5][0] # weather_key
        print(f"Weather config loaded: {self.city}, {self.state}, {self.country} (lat={self.latitude}, lon={self.longitude})")
        if autorun:
            response = self.api_request()
            # Once gps is retrieved a second call to get_weather is performed
            stored = self.parse_weather(response)
            # update database with new weather data
            self.save_weather(stored)
    
    
    # Get weather makes second call to the api for detailed weather 
    def api_request(self):
        # api call uses gps coordinates from get gps
        try:
            print(f"Fetching weather for coordinates: {self.latitude}, {self.longitude}")
            WEATHER_response = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.weather_key}",
                timeout=10
            ).json()
            # Check if API returned an error
            if 'cod' in WEATHER_response and WEATHER_response['cod'] != 200:
                error_msg = WEATHER_response.get('message', 'Unknown error')
                print(f"ERROR: Weather API returned error code {WEATHER_response['cod']}: {error_msg}")
                return self.error_data()
            # Verify response has required fields
            if 'weather' not in WEATHER_response or 'main' not in WEATHER_response:
                print(f"ERROR: Invalid weather API response structure: {WEATHER_response}")
                return self.error_data()
            print(f"Successfully fetched weather data")
            return WEATHER_response
            
        except requests.exceptions.Timeout:
            print("ERROR: Weather API request timed out")
            return self.error_data()
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Weather API request failed: {e}")
            return self.error_data()
        except Exception as e:
            print(f"ERROR: Unexpected error in weather api_request: {e}")
            return self.error_data()
    

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
        except Exception as e:
            # returns a blank string
            cardinal = " "
            print(f"ERROR: wind_direction parsing failed for value '{wind_dir}': {e}")
        return cardinal
    

    def parse_weather(self, weather_response):
        try:
            data = weather_response
            # Check if we got a valid response with weather data
            if 'weather' not in data or 'main' not in data:
                print(f"ERROR: Invalid weather API response: {data}")
                data = self.error_data()
        except Exception as e:
            print(f"ERROR: Exception checking weather response: {e}")
            data = self.error_data()
        # response is formatted for direct output.
        try:
            description = data['weather'][0]['description'].title()
            icon = data['weather'][0]['icon']
            if not icon.endswith('.png'):
                icon += ".png"
            feel = int((data['main']['feels_like']) * 1.8 - 459.67)
            min_temp = int((data['main']['temp_min']) * 1.8 - 459.67)
            max_temp = int((data['main']['temp_max']) * 1.8 - 459.67)
            temp = f"{min_temp} - {max_temp}"
            humid = data['main']['humidity']
            clouds = data['clouds']['all']
            # Handle missing wind direction gracefully
            wind_deg = data.get('wind', {}).get('deg', 0)
            wind_speed = data.get('wind', {}).get('speed', 0)
            dir = self.wind_direction(wind_deg)
            wind = f"{dir} {int(wind_speed)}mp/h"
        except (KeyError, TypeError, ValueError) as e:
            print(f"ERROR: Failed to parse weather data: {e}")
            # Set default error values
            description = "API Error"
            icon = "01d.png"
            feel = "N/A"
            temp = "N/A"
            humid = "N/A"
            clouds = "N/A"
            wind = "N/A"
        
        stored_weather = {
            "city": self.city, 
            "state": self.state, 
            "country": self.country,
            "description": description, 
            "icon": icon, 
            "feel": feel, 
            "temp": temp,
            "humid": humid, 
            "clouds": clouds,
            "wind": wind
        }
        return stored_weather


    def save_weather(self, data):
        if data["description"] != "API Error":
            try:
                self.user_handle = Handler("user")
                self.user_handle.send_command("DELETE FROM weather_database")
                saved_count = 0
                for k, v in data.items():
                    try:
                        self.user_handle.update_database("weather_database", "key", "value", k, v)
                        saved_count += 1
                    except Exception as e:
                        print(f"ERROR: Failed to save weather field {k}={v}: {e}")
                self.user_handle.send_command("UPDATE updates_database SET value = NOW() WHERE key = 'weather';")
                print(f"Saved {saved_count} weather fields to database")
            except Exception as e:
                print(f"ERROR: Failed to save weather to database: {e}")
        else:
            print("Keeping old weather data in database")


    def error_data(self):
        return {
            "weather": [{"description": "API Error", "icon": "01d"}], 
            "main": {"feels_like": 255, "temp_min": 255, "temp_max": 255, "humidity": 0},
            "clouds": {"all": 0}, 
            "wind": {"deg": 0, "speed": 0}
        } 


class Weather_Report():
    def __init__(self, autorun = True):
        self.last_loaded = None
        self.city = "Geolocating..."
        self.state = ""
        self.country = ""
        self.description = "Loading..."
        self.icon = "01d.png"
        self.feel = "N/A"
        self.temp = "N/A"
        self.humid = "N/A"
        self.clouds = "N/A"
        self.wind = "N/A"
        if autorun:
            self.get_weather()

    # Checks if the most recent entry in the updated_database is new
    def get_weather(self):
        user_handle = Handler("user")
        try:
            last = user_handle.send_query("SELECT value FROM updates_database WHERE key = 'weather'")
            if not last or len(last) == 0:
                return self.error_data()
            if last[0][0] != self.last_loaded:
                self.last_loaded = last[0][0]
                try:
                    data = user_handle.send_query("SELECT * FROM weather_database")
                    data = dict(data)
                    report = self.assign(data)
                    print(f"Weather cache refreshed at {self.last_loaded}")
                    return report
                except Exception as e:
                    print(f"ERROR: Failed to load weather from database: {e}")
                    return self.error_data()
            else:
                # Return cached data when timestamp hasn't changed
                return {
                    "city": self.city, 
                    "state": self.state, 
                    "country": self.country, 
                    "description": self.description, 
                    "icon": self.icon, 
                    "feel": self.feel, 
                    "temp": self.temp, 
                    "humid": self.humid, 
                    "clouds": self.clouds, 
                    "wind": self.wind
                }
        except Exception as e:
            print(f"ERROR: Failed to get weather: {e}")
            return self.error_data()
        

    def assign(self, data):
        # response is formatted for direct output.
        try:
            self.city = data.get('city', 'Unknown').title()
            self.state = data.get('state', '').title()
            self.country = data.get('country', '').upper()
            self.description = data.get('description', 'N/A').title()
            self.icon = data.get('icon', '01d.png')
            self.feel = data.get('feel', 'N/A')
            self.temp = data.get('temp', 'N/A')
            self.humid = data.get('humid', 'N/A')
            self.clouds = data.get('clouds', 'N/A')
            self.wind = data.get('wind', 'N/A')
            print(f"Weather assigned: {self.city}, {self.state} - {self.description}")
        except (KeyError, TypeError, ValueError) as e:
            print(f"ERROR: Failed to assign weather data: {e}")
            return self.error_data()
        return data


    def error_data(self):
        return {
            "city": "Unknown", 
            "state": "", 
            "country": "",
            "description": "API Error", 
            "icon": "01d.png", 
            "feel": "N/A", 
            "temp": "N/A",
            "humid": "N/A", 
            "clouds": "N/A",
            "wind": "N/A"
        }
import requests
from classHandler import Handler


# weather report uses an api to send weather to the flask interface
class Update_Weather():
    def __init__(self, autorun = True):
        self.user_handle = Handler("user")
        db = self.user_handle.send_query("SELECT value FROM config_database WHERE key IN ('weather_key', 'lon', 'lat');")
        self.weather_key = db[0][0]
        self.longitude = db[1][0]
        self.latitude = db[2][0]  
        if autorun:
            response = self.api_request()
            # Once gps is retrieved a second call to get_weather is performed
            stored = self.parse_weather(response)
            # update database with new weather data
            self.save_weather(stored)
    
    
    #Get weather makes second call to the api for detailed weather 
    def api_request(self):
        # api call uses gps coordinates from get gps
        try: 
            WEATHER_response = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={self.latitude}&lon={self.longitude}&appid={self.weather_key}").json()
        except requests.exceptions.RequestException as e:
            print("ERROR: weather.get_weather >>> api request >>>", e)
            WEATHER_response = self.error_data()
        #print(WEATHER_response)
        # Returns full dict
        return WEATHER_response
    

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
    

    def parse_weather(self, weather_response):
        try:
            data = weather_response
            # Check if we got a valid response with weather data
            if 'weather' not in data or 'main' not in data:
                print(f"ERROR: Invalid weather API response: {data}")
                data = self.error_data()
        except Exception as e:
            print("ERROR: >>> get_weather >>>", e)
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
            dir = self.wind_direction(data['wind']['deg'])
            wind = f"{dir} {int(data['wind']['speed'])}mp/h"
        except (KeyError, TypeError, ValueError) as e:
            print(f"ERROR:  >>> parsing weather data >>> {e}")
            # Set default error values
            description = "API Error"
            icon = "01d.png"
            feel = "N/A"
            temp = "N/A"
            humid = "N/A"
            clouds = "N/A"
            wind = "N/A"
        stored_weather = {"description": description, "icon":icon, "feel":feel, "temp":temp,"humid":humid, "clouds":clouds,"wind":wind}
        return stored_weather

    def save_weather(self, data):
        print(data)
        if data["description"] != "API Error":
            self.user_handle = Handler("user")
            self.user_handle.send_command("DELETE FROM weather_database")
            for k,v in data.items():
                try:
                    self.user_handle.send_command(f"INSERT INTO weather_database (key, value) VALUES ('{k}', '{v}')")
                except Exception as e:
                    print(f"Error adding weather to database - {k} = {v} :\n {e}")
            self.user_handle.send_command("UPDATE updates_database SET value = NOW() WHERE key = 'weather'; ")
        else:
            print("Error: Using old database values for weather")
        


    def error_data(self):
        return {"weather": [{"description": "API Error", "icon": "01d"}], 
            "main": {"feels_like": 255, "temp_min": 255, "temp_max": 255, "humidity": 0},
            "clouds": {"all": 0}, "wind": {"deg": 0, "speed": 0}} 


class Weather_Report():
    def __init__(self):
        self.last_loaded = None


    # Checks if the most recent entry in the updated_database is new
    def get_weather(self):
        user_handle = Handler("user")
        try:
            last = user_handle.send_query("SELECT value FROM updates_database WHERE key = 'weather'")
            print(last)
            if last[0][0] != self.last_loaded:
                self.articles = self.reload(user_handle)
                self.last_loaded = last[0][0]
            return self.articles
        except Exception as e:
            print("Error reading news from database:", e)
            return []


    # Gets news articles from database
    def reload(self, handler):
        try:
            data = handler.send_query("SELECT * FROM weather_database")
        except Exception as e:
            print("ERROR: >>> Loading weather from database >>>", e)
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
            print(f"ERROR:  >>> parsing weather data >>> {e}")
            # Set default error values
            self.description = "API Error"
            self.icon = "01d.png"
            self.feel = "N/A"
            self.temp = "N/A"
            self.humid = "N/A"
            self.clouds = "N/A"
            self.wind = "N/A"
        stored_weather = {"description": self.description, "icon":self.icon, "feel":self.feel, "temp":self.temp,"humid":self.humid, "clouds":self.clouds,"wind":self.wind}
        return stored_weather

gps = Change_City("new york")

#up = Update_Weather()
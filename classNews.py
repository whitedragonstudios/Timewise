import requests
from classHandler import Handler

# This class gets news from an API and processes it for display in flask and js
class News_Report():
    def __init__(self, country, news_key, banned_list = [], autorun = True):
        # News Report needs the api key and country stored in config database 
        self.country = country
        self.news_key = news_key
        # A banned list can be passed to not display certain news sources defaults to an empty list
        self.banned_list = banned_list or []
        # Autorun is true by default to automatically send api request.
        self.autorun = autorun or True
        if self.autorun:
            self.articles = self.update_news()


    # get news sends API request and returns json dictionary of news articles.
    def api_request(self):
        try: 
            NEWS_response = requests.get(
                f"https://newsapi.org/v2/top-headlines?country={self.country}&apiKey={self.news_key}"
            ).json()
            
            # Check if the API returned an error
            if 'status' in NEWS_response and NEWS_response['status'] == 'error':
                print(f"ERROR: News API returned error: {NEWS_response.get('message', 'Unknown error')}")
                return self.error_data()
            
            # Check if articles exist in response
            if 'articles' not in NEWS_response:
                print(f"ERROR: No articles in API response: {NEWS_response}")
                return self.error_data()
            print(NEWS_response) 
            return NEWS_response
            
        except requests.exceptions.RequestException as e:
            print("ERROR:api request >>>", e)
            return self.error_data()


    # parse news organizes news articles into a list of dictionaries which flask expects.
    def parse_news(self, news_response):
        parsed_news = []
        
        # Ensure articles exist and is a list
        if 'articles' not in news_response or not isinstance(news_response['articles'], list):
            return [{'src': 'Error', 'art': 'No news available', 'url': '#'}]
        
        for item in news_response['articles']:
            try:
                # Handle case where item might be a string (from error_data)
                if isinstance(item, str):
                    parsed_news.append({'src': 'Error', 'art': item, 'url': '#'})
                    continue
                
                source = item.get('source', {}).get('name', 'Unknown Source')
                article = item.get('title', item.get('description', 'No title available'))
                url = item.get('url', '#')
                
                # check sources against banned list.
                if source not in self.banned_list:
                    parsed_news.append({'src': source, 'art': article, 'url': url})
                    
            except (KeyError, TypeError) as e:
                print(f"ERROR: Parsing news item: {e}")
                continue
        
        # If no articles were parsed, return error message
        if not parsed_news:
            return [{'src': 'Error', 'art': 'No news available', 'url': '#'}]
            
        return parsed_news


    # Adds news articles to database.
    def save_news(self, articles):
        user_handle = Handler("user")
        try:
            user_handle.send_command("DELETE FROM news_database")
            for item in articles:
                try:
                    src = item.get("src", "").replace("'", "''")
                    art = item.get("art", "").replace("'", "''")
                    url = item.get("url", "").replace("'", "''")
                    cmd = (f"INSERT INTO news_database (src, art, url) VALUES ('{src}', '{art}', '{url}')")
                    user_handle.send_command(cmd)
                    print(f"Article from {src} added to database")
                except Exception as e:
                    print(f"Error inserting article from {item.get('src', 'UNKNOWN')}: {e}")
        except Exception as e:
            print(f"Error preparing news_database table: {e}")


        # Gets news from the database NOTE is not included in autorun process
    def get_news(self):
        user_handle = Handler("user")
        try:
            data = user_handle.send_query("SELECT * FROM news_database")
            news_sorted = []
            for item in data:
                news_sorted.append(dict(item))
            return news_sorted
        except Exception as e:
            print("Error reading news from database:", e)
            return []
        

    # Flow control for the class calls both methods and passes data between them
    def update_news(self):
        try:
            news_response = self.api_request()
            articles = self.parse_news(news_response)
            self.save_news(articles)
            #self.get_news()
            return articles
        except Exception as e:
            print("Error updating news:", e)
            return []

    


    # Return error data structure when API fails
    def error_data(self):
        return {
            'status': 'error',
            'articles': [
                {
                    'source': {'name': 'Error'},
                    'title': 'Unable to fetch news',
                    'description': 'API connection error',
                    'url': '#'
                },
                {
                    'source': {'name': 'Error'},
                    'title': 'Check your API key',
                    'description': 'Invalid or expired API key',
                    'url': '#'
                },
                {
                    'source': {'name': 'Error'},
                    'title': 'Check your internet connection',
                    'description': 'Unable to reach news service',
                    'url': '#'
                }
            ]
        }
    
# save_news and get_news are for future implimentations of the app. If a single server is run 
# and multiple client side scanners are deployed news can be accessed via database to reduce API calls.
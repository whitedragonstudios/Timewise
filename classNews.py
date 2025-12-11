import requests
from classHandler import Handler

# This class gets news from an API and processes it for display in flask and js
class Update_News():
    def __init__(self, country, news_key, banned_list = [], autorun = True):
        # News Report needs the api key and country stored in config database 
        self.country = country
        self.news_key = news_key
        # A banned list can be passed to not display certain news sources defaults to an empty list
        self.banned_list = banned_list or []
        if autorun:
            self.articles = self.run()


    # Sends API request and returns json dictionary of news articles.
    def api_request(self):
        try: 
            NEWS_response = requests.get(f"https://newsapi.org/v2/top-headlines?country={self.country}&apiKey={self.news_key}").json()
            # Check if the API returned an error
            if 'status' in NEWS_response and NEWS_response['status'] == 'error':
                print(f"ERROR: News API returned error: {NEWS_response.get('message', 'Unknown error')}")
                return self.error_data()
            # Check if articles exist in response
            if 'articles' not in NEWS_response:
                print(f"ERROR: No articles in API response: {NEWS_response}")
                return self.error_data()
            #print(NEWS_response) 
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
        # Iterate through Articles
        for item in news_response['articles']:
            try:
                # Handle case where item might be a string (from error_data)
                if isinstance(item, str):
                    parsed_news.append({'src': 'Error', 'art': item, 'url': '#'})
                    continue
                # Oraganize into three keys per article
                source = item.get('source', {}).get('name', 'Unknown Source')
                article = item.get('title', item.get('description', 'No title available'))
                url = item.get('url', '#')
                # Check sources against banned list.
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
            # Iterate through articles
            for item in articles:
                try:
                    # Clean out sql unfriendly quotes
                    src = item.get("src", "").replace("'", "''")
                    art = item.get("art", "").replace("'", "''")
                    url = item.get("url", "").replace("'", "''")
                    # Send to db
                    user_handle.send_command(f"INSERT INTO news_database (src, art, url) VALUES ('{src}', '{art}', '{url}')")
                    print(f"Article from {src} added to database")
                    user_handle.send_command("UPDATE updates_database SET value = NOW() WHERE key = 'news'; ")
                except Exception as e:
                    print(f"Error inserting article from {item.get('src', 'UNKNOWN')}: {e}")
                    continue
        except Exception as e:
            print(f"Error preparing news_database table: {e}")


    # Flow control for the class calls both methods and passes data between them
    def run(self):
        news_response = self.api_request()
        articles = self.parse_news(news_response)
        self.save_news(articles)
        return articles


    # Return error data structure when API fails
    def error_data(self):
        return {'status': 'error','articles': [
                {'source': {'name': 'Error'},
                    'title': 'Unable to fetch news',
                    'description': 'API connection error',
                    'url': '#'},
                {'source': {'name': 'Error'},
                    'title': 'Check your API key',
                    'description': 'Invalid or expired API key',
                    'url': '#'},
                {'source': {'name': 'Error'},
                    'title': 'Check your internet connection',
                    'description': 'Unable to reach news service',
                    'url': '#'}]}


class News_Report():
    def __init__(self):
        self.articles = []
        self.last_loaded = None


    # Checks if the most recent entry in the updated_database is new
    def get_news(self):
        user_handle = Handler("user")
        try:
            last = user_handle.send_query("SELECT value FROM updates_database WHERE key = 'news'")
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
            rows = handler.send_query("SELECT src, art, url FROM news_database ORDER BY id")
            articles = [
                {"src": r[0], "art": r[1], "url": r[2]}
                for r in rows]
            print(f"NewsReport: loaded {len(articles)} articles")
        except Exception as e:
            print("Error reading news from database:", e)
            articles = []
        return articles

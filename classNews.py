import requests
from classHandler import Handler

# This class gets news from an API and processes it for display in flask and js
class Update_News():
    def __init__(self, autorun = True):
        self.user_handle = Handler("user")
        
        # FIXED: Use ORDER BY to ensure consistent ordering of results
        db = self.user_handle.send_query(
            "SELECT value FROM config_database WHERE key IN ('country', 'news_key', 'banned') ORDER BY key;"
        )
        
        # After ORDER BY key, the order will be: banned, country, news_key (alphabetical)
        # So we need to access them in this order:
        self.banned_list = db[0][0].split(",") if db[0][0] else []  # banned
        self.country = db[1][0]  # country
        self.news_key = db[2][0]  # news_key
        
        print(f"News config loaded: country={self.country}, banned_sources={len(self.banned_list)}")
        
        # A banned list can be passed to not display certain news sources defaults to an empty list
        if autorun:
            response = self.api_request()
            articles = self.parse_news(response)
            self.save_news(articles)


    # Sends API request and returns json dictionary of news articles.
    def api_request(self):
        try:
            print(f"Fetching news for country: {self.country}")
            NEWS_response = requests.get(
                f"https://newsapi.org/v2/top-headlines?country={self.country}&apiKey={self.news_key}",
                timeout=10
            ).json()
            
            # Check if the API returned an error FIRST
            if 'status' in NEWS_response and NEWS_response['status'] == 'error':
                error_msg = NEWS_response.get('message', 'Unknown error')
                print(f"ERROR: News API returned error: {error_msg}")
                return self.error_data()
            
            # Check if articles exist in response
            if 'articles' not in NEWS_response:
                print(f"ERROR: No articles key in API response: {NEWS_response}")
                return self.error_data()
            
            # Check if any articles were actually returned
            if not NEWS_response["articles"] or len(NEWS_response["articles"]) == 0:
                print("WARNING: API returned 0 articles")
                print("NOTE: Free version of newsapi only works for select countries")
                return self.error_data()
            
            print(f"✓ Successfully fetched {len(NEWS_response['articles'])} articles")
            return NEWS_response
            
        except requests.exceptions.Timeout:
            print("ERROR: News API request timed out")
            return self.error_data()
        except requests.exceptions.RequestException as e:
            print(f"ERROR: API request failed: {e}")
            return self.error_data()
        except Exception as e:
            print(f"ERROR: Unexpected error in api_request: {e}")
            return self.error_data()


    # parse news organizes news articles into a list of dictionaries which flask expects.
    def parse_news(self, news_response):
        parsed_news = []
        
        # Ensure articles exist and is a list
        if 'articles' not in news_response or not isinstance(news_response['articles'], list):
            print("ERROR: Invalid news_response structure")
            return [{'src': 'Error', 'art': 'No news available', 'url': '#'}]
        
        # Iterate through Articles
        for item in news_response['articles']:
            try:
                # Handle case where item might be a string (from error_data)
                if isinstance(item, str):
                    parsed_news.append({'src': 'Error', 'art': item, 'url': '#'})
                    continue
                
                # Organize into three keys per article
                source = item.get('source', {}).get('name', 'Unknown Source')
                article = item.get('title', item.get('description', 'No title available'))
                url = item.get('url', '#')
                
                # Check sources against banned list.
                if source not in self.banned_list:
                    parsed_news.append({'src': source, 'art': article, 'url': url})
                else:
                    print(f"Skipping banned source: {source}")
                    
            except (KeyError, TypeError) as e:
                print(f"ERROR: Parsing news item: {e}")
                continue
        
        # If no articles were parsed, return error message
        if not parsed_news:
            print("WARNING: No articles passed the filter")
            return [{'src': 'Error', 'art': 'No news available after filtering', 'url': '#'}]
        
        print(f"✓ Parsed {len(parsed_news)} articles successfully")
        return parsed_news


    # Adds news articles to database.
    def save_news(self, articles):
        user_handle = Handler("user")
        try:
            user_handle.send_command("DELETE FROM news_database")
            saved_count = 0
            
            # Iterate through articles
            for item in articles:
                try:
                    # Clean out sql unfriendly quotes
                    src = item.get("src", "").replace("'", "''")
                    art = item.get("art", "").replace("'", "''")
                    url = item.get("url", "").replace("'", "''")
                    
                    # Send to db
                    user_handle.send_command(
                        f"INSERT INTO news_database (src, art, url) VALUES ('{src}', '{art}', '{url}')"
                    )
                    saved_count += 1
                    
                except Exception as e:
                    print(f"Error inserting article from {item.get('src', 'UNKNOWN')}: {e}")
                    continue
            
            # Update the timestamp after all articles are saved
            user_handle.send_command("UPDATE updates_database SET value = NOW() WHERE key = 'news';")
            print(f"✓ Saved {saved_count} articles to database")
            
        except Exception as e:
            print(f"ERROR: Failed to save news to database: {e}")


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
                },
                {
                    'source': {'name': 'Error'},
                    'title': 'Free version of newsAPI only works for US cities',
                    'description': 'Unable to get articles',
                    'url': '#'
                }
            ]
        }


class News_Report():
    def __init__(self):
        self.articles = []
        self.last_loaded = None


    # Checks if the most recent entry in the updated_database is new
    def get_news(self):
        user_handle = Handler("user")
        try:
            last = user_handle.send_query("SELECT value FROM updates_database WHERE key = 'news'")
            
            if not last or len(last) == 0:
                print("WARNING: No news update timestamp found")
                return []
            
            # Check if we need to reload
            if last[0][0] != self.last_loaded:
                self.articles = self.reload(user_handle)
                self.last_loaded = last[0][0]
                print(f"✓ News cache refreshed at {self.last_loaded}")
            
            return self.articles
            
        except Exception as e:
            print(f"ERROR: Failed to get news: {e}")
            return []


    # Gets news articles from database
    def reload(self, handler):
        try:
            rows = handler.send_query("SELECT src, art, url FROM news_database ORDER BY id")
            
            if not rows:
                print("WARNING: No news articles in database")
                return []
            
            articles = [
                {"src": r[0], "art": r[1], "url": r[2]}
                for r in rows
            ]
            
            print(f"✓ Loaded {len(articles)} articles from database")
            return articles
            
        except Exception as e:
            print(f"ERROR: Failed to reload news from database: {e}")
            return []


# REMOVED: upn = Update_News()
# Do not instantiate at module level - this causes initialization issues
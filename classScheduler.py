from classHandler import Handler
from classRedis import redis_handle
from celery import Celery
from celery.schedules import crontab
from datetime import datetime as dt
from classMailer import Mailer
from classNews import News_Report
from classWeather import Weather_Report

# Global celery app (created later)
celery_app = None


class Scheduler():
    def __init__(self, config):
        broker_url, backend_url, redis_handler = redis_handle()
        self.broker = broker_url
        self.backend = backend_url
        self.redis = redis_handler
        # Config settings
        self.city = config.city
        self.country = config.country
        self.nkey = config.news_key
        self.wkey = config.weather_key

        print("Scheduler initialized")

    def create_celery(self):
        app = Celery('timewise', broker=self.broker, backend=self.backend)
        # Configure Celery
        app.conf.update(
            timezone='UTC',
            enable_utc=True,
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            task_track_started=True,
            task_time_limit=3600,
            task_soft_time_limit=3000,
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
            result_expires=3600,
            task_acks_late=True,
            task_reject_on_worker_lost=True,
        )
        print(f"Celery app created: {app.main}")
        return app

    def define_tasks(self):
        global celery_app
        @celery_app.task(name='timewise.send_email', bind=True, max_retries=3)
        def send_email(self):
            try:
                print("=== SENDING EMAILS ===")
                email = Mailer()
                email.send_now()
                print("Emails sent successfully")
                return {'timestamp': dt.utcnow().isoformat(), 'status': 'success'}
            except Exception as e:
                print(f"Error sending emails: {e}")
                raise self.retry(exc=e, countdown=300)
        
        
        @celery_app.task(name='timewise.get_weather', bind=True, max_retries=5)
        def get_weather(self):
            try:
                print("=== REFRESHING WEATHER ===")
                weather = Weather_Report(self.city, self.wkey, autorun=True, gps_check=False)
                weather.assign()
                weather.update_database()
                print("Weather refreshed successfully")
                return {'timestamp': dt.now().isoformat(), 'status': 'success'}
            except Exception as e:
                print(f"Error refreshing weather: {e}")
                raise self.retry(exc=e, countdown=600)
        
        
        @celery_app.task(name='timewise.get_news', bind=True, max_retries=5)
        def get_news(self):
            try:
                print("=== REFRESHING NEWS ===")
                news = News_Report(self.country, self.nkey)
                news.api_request()
                news.get_news()
                print("News refreshed successfully")
                return {'timestamp': dt.now().isoformat(), 'status': 'success'}
            except Exception as e:
                print(f"Error refreshing news: {e}")
                raise self.retry(exc=e, countdown=600)
        
        
        @celery_app.task(name='timewise.clockout', bind=True, max_retries=3)
        def clockout(self):
            try:
                print("=== AUTO CLOCK-OUT STARTED ===")
                user_handle = Handler("user")
                # Update all unclosed clock-outs
                user_handle.send_command("""
                    UPDATE timesheet_database
                    SET clock_out = (work_date + TIME '00:00:00')::timestamptz, notes = 'no clock out'
                    WHERE clock_out IS NULL;""")
                print("Auto clock-out completed")
                return {'timestamp': dt.now().isoformat(), 'status': 'success'}
            except Exception as e:
                print(f"Error during auto clock-out: {e}")
                raise self.retry(exc=e, countdown=300)


    def define_schedule(self):
        global celery_app
        celery_app.conf.beat_schedule = {
            'clockout-before-midnight': {
                'task': 'timewise.clockout',
                'schedule': crontab(hour=23, minute=50),
                'options': {
                    'priority': 9
                }
            },

            'refresh-news-morning': {
                'task': 'timewise.get_news',
                'schedule': crontab(hour=8, minute=0),
            },
            'refresh-news-evening': {
                'task': 'timewise.get_news',
                'schedule': crontab(hour=20, minute=0),
            },
            
            'refresh-weather-every-2h': {
                'task': 'timewise.get_weather',
                'schedule': crontab(minute=0, hour='*/2'),
            },
            
            'send-daily-emails': {
                'task': 'timewise.send_email',
                'schedule': crontab(hour=23, minute=59),
            },
        }


    def run(self):
        global celery_app
        print("Initializing Celery...")
        # Step 1: Create Celery app
        celery_app = self.create_celery()
        # Step 2: Define tasks
        self.define_tasks()
        # Step 3: Define schedule
        self.define_schedule()
        print("Celery initialized successfully")
        return celery_app



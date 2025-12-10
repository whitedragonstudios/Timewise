from classHandler import Handler
from classRedis import redis_handle
from celery import Celery
from celery.schedules import crontab
from datetime import datetime as dt, date
from classMailer import Mailer
from classNews import News_Report
from classWeather import Weather_Report

class Scheduler():
    def __init__(self):
        #self.userhandle = Handler("user")
        broker_url, backend_url, redis_handler = redis_handle()
        self.broker = broker_url
        self.backend = backend_url
        self.redis = redis_handler

    def create_celery(self):
        app = Celery('timewise', broker=self.broker, backend=self.backend)
        # Configure Celery
        app.conf.update(
            timezone='UTC',
            enable_utc=True,
            # Encode tasks as JSON
            task_serializer='json',      
            accept_content=['json'],
            result_serializer='json',
            # Task tracking and timeout
            task_track_started=True,
            task_time_limit=3600,
            task_soft_time_limit=3000,
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=1000,
            result_expires=3600, # Keep results for 1 hour
            task_acks_late=True,
            task_reject_on_worker_lost=True,)
        print(f"Celery app created: {app.main}")
        return app
    
    @celery_app.task
    def send_email(self):
        try:
            print("Sending Emails")
            email = Mailer()
            email.send_now()
            return {'timestamp': dt.utcnow().isoformat(),'status': 'success'}
        except Exception as e:
            print(f"Error sending emails: {e}")
            raise

    def get_weather(self):
        try:
            print("Refreshing weather")
            weather = Weather_Report(autorun = True, gps_check = False)
            weather.assign()
            weather.update_database()
            return {'timestamp': dt.utcnow().isoformat(), 'status': 'success'}
        except Exception as e:
            print(f"Error refreshing weather: {e}")
            raise

    def get_news():
        try:
            print("Refreshing news")
            news = News_Report(0)
            news.get_news()
            return {'timestamp': dt.utcnow().isoformat(), 'status': 'success'}
        except Exception as e:
            print(f"Error refreshing news: {e}")
            raise

    def clockout_all():
        user_handle = Handler("user")

        try:
            user_handle.send_command("""UPDATE timesheet_database
                SET clock_out = (work_date + TIME '00:00')::timestamptz,
                notes = 'no clock out'
                WHERE clock_out IS NULL;""")
        except Exception as e:
            print("Error getting clocked in")

        try: 
            not_clocked_out = user_handle.send_query("""
            SELECT t.work_date, t.clock_in, p.first_name, p.last_name p.employee_id,
            FROM people_database p JOIN timesheet_database t
            ON p.employee_id = t.employee_id WHERE t.notes IS "no clock out"
            ORDER BY t.work_date DESC , t.clock_in DESC;""")
        except Exception as e:
            print("Error getting clocked in")
        print(not_clocked_out)
        return not_clocked_out


    def run(self):
        global celery_app
        # Create Celery app
        celery_app = self.create_celery()
        # Define tasks (after app is created)
        self.tasks()
        # Define schedule (after tasks are defined)
        self.schedule()
        
        print("Celery Run")
        return celery_app
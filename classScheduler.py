from classHandler import Handler
from classRedis import redis_handle
from celery import Celery
from celery.schedules import crontab
from datetime import datetime as dt, date


class Autosend():
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
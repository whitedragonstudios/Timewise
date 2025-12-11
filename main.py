import classInstall, classSettings
from classScheduler import Scheduler
from classHandler import Handler

def edit_db():
    user = Handler("user")
    user.send_command("""
                CREATE TABLE IF NOT EXISTS updates_database (
                    key TEXT PRIMARY KEY, 
                    value TIMESTAMPTZ DEFAULT NOW());""")
    user.send_command("INSERT INTO updates_database (key) VALUES ('news'), ('weather'), ('config'), ('emails');")

#edit_db()
reset = False

if __name__ == "__main__":
    cf = None
    if reset == True:
        initalize = classInstall.Postgre_Install()
        #initalize.drop_tables("people_database")
        #initalize.drop_tables("timesheet_database")
        #initalize.drop_tables("config_database")
        #initalize.drop_tables("email_list")
        #initalize.drop_database("news_database")
        #initalize.drop_database("weather_database")
        #initalize.drop_database('scanner')
        #initalize.drop_user('marcus') #uncomment if you need to reset user
    try:
        # Load config file
        cf = classSettings.Setting()
        print("Settings loaded successfully.")
        #print(cf.data)
    except Exception as e:
        print(f"Failed to load settings: {e}")
        print("Initializing installation process...")
        # Run classInstall and check the server connection works, if not updates path and installs psql.
        initalize = classInstall.Postgre_Install()
        # run controls the flow of classInstall
        initalize.run()
        # initalize.insert_test_data() # uncomment to add test data to people and email databases
        cf = classSettings.Setting()
        print("Settings loaded successfully.")
    try:
        scheduler = Scheduler(cf)
        schedule = scheduler.run()
    except Exception as e:
        print(f"Error initalizing redis and celery: {e}")
    try:
        if cf.config_status == "True" and schedule is not None:
            from server import app, frontend
            # Launcher server
            app.register_blueprint(frontend)
            app.run(host="0.0.0.0", port=2000, debug=True)
            #serve(app, host="0.0.0.0", port=2000))
        else:
            print("Configuration status is False. Please complete the installation process.")
    except Exception as e:
        print(f"Error during startup: {e}")
        print("Please complete the installation process.")



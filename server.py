from flask import Flask, render_template, request, redirect, Blueprint, flash, session
import classSettings, classScheduler
from classNews import News_Report
from classQuotes import quote_generator
from classWeather import weather_report
from classHandler import Handler
from classPerson import Person, Default_Person
from classReports import Reports
import services


def preload_data():
    try:
        config = classSettings.Setting()
        weather_data = weather_report(config.city, config.weather_key)
        news = News_Report(config.country, config.news_key)
        quoteOTDay = quote_generator().QotD
    except Exception as e:
        print("Error preloading data")
    return config, weather_data, news, quoteOTDay


def message_parser(messages):
    for k,v in messages.items():
        if len(v) > 0:
            counter = 1
            catagory = k
            for msg in v:
                flash(msg, catagory)
                counter +=1
                if counter > 12:
                    flash(f"{len(v)-counter} more", catagory)
                    break
    return messages


# Intialize flask server
app = Flask(__name__)
app.secret_key = "stoic"
frontend = Blueprint('frontend', __name__, template_folder='templates', static_folder='static')
recent_list = []

config, weather_data, news, quoteOTDay = preload_data()
user_handle = Handler("user")

# Set default and index route
@frontend.route ('/')
def index():
    return redirect('/home')


@frontend.route('/home', methods=['GET', 'POST'])
def home():
    global recent_list
    employee = None
    idscan = None
    if request.method == 'POST':
        idscan = request.form.get('idscan')
        if not idscan:
            employee = Default_Person(recent_list, idscan)
        else:
            try:
                employee = Person(idscan, recent_list)
                message_parser({"success":[f"{idscan} Clocked {employee.io}"]})
                # Save last successful scan ID to session
                session['last_scan_id'] = idscan
                
            except Exception as e:
                print(f"Error: Person failed to find matching ID {e}")
                message_parser({"error":["Failed to match person to ID"]})
                employee = Default_Person(recent_list, idscan)
                
        recent_list = employee.recent
        session['recent_list'] = recent_list
        
    else:  # GET request
        # Restore recent list from session
        if 'recent_list' in session:
            recent_list = session['recent_list']
        
        # If there was a last scan, recreate that person
        if 'last_scan_id' in session:
            try:
                idscan = session['last_scan_id']
                employee = Person(idscan, recent_list)
            except:
                employee = Default_Person(recent_list, None)
        else:
            employee = Default_Person(recent_list, None)

    # Fallback if employee is still None
    if employee is None:
        employee = Default_Person(recent_list, idscan)

    return render_template("home.html", 
                           recent_people=recent_list,
                           scan=employee,
                           cf=config,
                           quote=quoteOTDay[0],
                           author=quoteOTDay[1],
                           wd=weather_data,
                           news_articles=news.articles
                           )




@frontend.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == "POST":
        global config, weather_data, news
        
        # Danger Zone
        action = request.form.get("action")
        if action:
            msg = services.danger(action, user_handle)
            config = classSettings.Setting()
            message_parser(msg)
        
        # Simple config changes    
        keys = ["company", "city", "weather_key", "news_key"]
        if any(key in request.form for key in keys):
            updated = False
            for key in keys:
                try:
                    msg = services.single_button(key, user_handle)
                    if len(msg['success']) > 0:
                        message_parser(msg)
                        updated = True
                    elif len(msg['error']) > 0:
                        message_parser(msg)
                except Exception as e:
                    print(f"Failed to update {key}: {e}")
            if updated:
                config = classSettings.Setting()
                news = News_Report(config.country, config.news_key)
                weather_data = weather_report(config.city, config.weather_key)

        # color updates dynamically
        if request.form.get("form_type") == "colors":
            for key, value in request.form.items():
                if services.hex_check(value):
                    if hasattr(config, key):
                        try:
                            setattr(config, key, value)
                            user_handle.update_database("config_database", "key", "value", key, value)
                            config = classSettings.Setting()
                            flash(f"{key} updated to {value}", "success")
                        except Exception as e:
                            flash(f"Failed to update {key}: {e}", "error")
                else:
                    flash(f"{value} is not a valid Hex Color", "error")

        
        # reset colors to default settings
        if "reset_colors" in request.form:
            default = config.default_colors()
            for key,value in default.items():
                try:
                    user_handle.update_database("config_database", "key", "value", key, value)
                    flash(f"{key} reset to {value}", "info")
                except Exception as e:
                    flash(f"Failed to reset {key}: {e}", "error")
            config = classSettings.Setting()
            #user_handle.send_query("SELECT * FROM config_database;")


        # Emails
        if "emails" in request.form:
            report_email = request.form.get("emails").strip().lower().replace("'", "''")
            freq = request.form.get("send-reports").strip().lower().replace("'", "''")
            try:
                user_handle.update_database("email_list", "key", "value", report_email, freq)
                flash(f"Added {report_email} at frequency {freq } to database", "success")
            except Exception as e:
                flash(f"Failed to insert {report_email} into database: {e}", "error")

        # file upload
        if "fileUpload" in request.files:
            file_handle = request.files["fileUpload"]
            msgs = services.upload(file_handle, user_handle)
            message_parser(msgs)

        # manual database entry
        if 'manual-entry-action' in request.form:
            action = request.form.get('manual-entry-action')
            request_dict = request.form.to_dict()
            msg = services.manual_entry(action, request_dict, user_handle)
            message_parser(msg)
    
    return render_template("settings.html", cf=config)




@frontend.route('/search', methods=['GET', 'POST'])
def search():
    search = session.get('last_search')
    field = session.get('last_field', 'name')
    time_entries = session.get('last_time_entries', '10')
    search_result = session.get('search_result', [])

    if request.method == "POST":
        search = request.form.get("search")
        field = request.form.get("field")
        time_entries = request.form.get("time_entries", 10)
        if search is not None:
            se = classScheduler.search_event(search, field, time_entries)
            search_result = se.results
        
            # Save to session
            session['last_search'] = search
            session['last_field'] = field
            session['last_time_entries'] = time_entries
            session['search_result'] = search_result
        if request.form.get("preview"):
            pass
        if request.form.get("send-now"):
            classScheduler.mailer().send_now()
        if request.form.get("save-now"):
            classScheduler.mailer().save_report()
        
    return render_template("search.html", 
        cf = config,
        search_result = search_result,
        )
    
@frontend.route('/reports', methods=['GET', 'POST'])
def reports():
    current = Reports()

    if request.method == "POST":
        pass
        if request.form.get("preview"):
            pass
        if request.form.get("send-now"):
            classScheduler.mailer().send_now()
        if request.form.get("save-now"):
            classScheduler.mailer().save_report()
        
    return render_template("reports.html", 
        cf = config,
        live = current.get_clocked_in(),
        report = current.get_report()
        )
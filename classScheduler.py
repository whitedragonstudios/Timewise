from classHandler import Handler
from classSettings import Setting

from io import BytesIO
import smtplib, threading, pandas as pd, os
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime as dt, date, timedelta

# for emailing to work do this on your Gmail account
#Go to your Google account security settings
#Enable 2-Step Verification
#Generate an App Password
#Use that 16-character code instead of your normal password

class search_event():
    def __init__(self, search, field, num_entries = 10, autorun = True):
        self.search = search.title().strip().replace("'", "''")
        self.field = field
        self.num_entries = num_entries or 10
        self.search_handle = Handler("user")
        if autorun == True:
            self.assign()
    
    def field_parser(self):
        
        base_query = """SELECT employee_id, first_name, last_name, email, phone, pic_path, employee_role, position, department"""
        if self.field == "name":
            twoName = self.search.split()
            if len(twoName) >1:
                fname = twoName[0]
                lname = twoName[1]
            else:
                fname = lname = twoName[0]
            query = f"""
                {base_query},
                (CASE
                    WHEN first_name = '{fname}' AND last_name = '{lname}' THEN 4
                    WHEN first_name LIKE '{fname}%' AND last_name LIKE '{lname}%' THEN 3
                    WHEN first_name ILIKE '%{fname}%' OR last_name ILIKE '%{fname}%' THEN 2
                    WHEN first_name LIKE '{lname}%' AND last_name LIKE '{fname}%' THEN 1
                    ELSE 0
                END) AS score
                FROM people_database
                WHERE first_name ILIKE '%{fname}%' 
                OR last_name ILIKE '%{fname}%'
                OR first_name ILIKE '%{lname}%' 
                OR last_name ILIKE '%{lname}%'
                ORDER BY score DESC, last_name, first_name;
            """
        elif self.field == "idnumber":
            query = f"""
                {base_query},
                (CASE WHEN employee_id = '{self.search}' THEN 1 ELSE 0 END) AS score
                FROM people_database
                WHERE employee_id = '{self.search}'
                ORDER BY score DESC;"""
        elif self.field == "email":
            s_lower = self.search.lower()
            query = f"""
                {base_query},
                (CASE WHEN LOWER(email) = '{s_lower}' THEN 3
                      WHEN LOWER(email) LIKE '{s_lower}%' THEN 2
                      WHEN LOWER(email) LIKE '%{s_lower}%' THEN 1
                      ELSE 0 END) AS score
                FROM people_database
                WHERE LOWER(email) LIKE '%{s_lower}%'
                ORDER BY score DESC;
            """
        elif self.field == "phone":
            query = f"""{base_query}
                FROM people_database WHERE phone = '{self.search}'"""
        elif self.field in ["role", "position", "department"]:
            query = f"""
                {base_query},
                (CASE WHEN {self.field} = '{self.search}' THEN 3
                      WHEN {self.field} LIKE '{self.search}%' THEN 2
                      WHEN {self.field} LIKE '%{self.search}%' THEN 1
                      ELSE 0 END) AS score
                FROM people_database
                WHERE {self.field} LIKE '%{self.search}%'
                ORDER BY score DESC;"""
        else:
            print("Error classScheduler.fieldparser: Field not valid")

        try:
            result = self.search_handle.send_query(query)
        except Exception as e:
            print(f"Error classSchedule.field_parser: {e}")
            result=[("", "Error", "Field Parser", "", "", "", "", "", "", 0)]


        columns = ["employee_id", "first_name", "last_name", "email", "phone", "pic_path", "employee_role", "position", "department", "score"]
        result = [dict(zip(columns, row)) for row in result]
        return result
    
    def format_time(self, value):
        if value is None:
            return "-----"
        if isinstance(value, str):
            value = dt.fromisoformat(value)
        if isinstance(value, dt):
            return value.strftime("%I:%M %p")
        if isinstance(value, date):
            return value.strftime("%d-%m-%Y")
        return str(value)

    def time_parser(self, idnumber):
        try:
            query = f"""
                SELECT id, employee_id, clock_in, clock_out, work_date
                FROM timesheet_database
                WHERE employee_id = {idnumber}
                ORDER BY clock_in DESC
                LIMIT {self.num_entries};"""
            result = self.search_handle.send_query(query)
        except Exception as e:
            print(f"Error classSchedule.time_parser: {e}")
            return []

        time_list = []
        for item in result:
            # Keep original datetime objects for calculation
            clockin_dt = item[2] if isinstance(item[2], dt) else dt.fromisoformat(item[2]) if item[2] else None
            clockout_dt = item[3] if isinstance(item[3], dt) else dt.fromisoformat(item[3]) if item[3] else None
            
            # Format for display
            clockin = self.format_time(item[2])
            clockout = self.format_time(item[3])
            date_str = self.format_time(item[4])
            
            # Calculate duration using datetime objects
            if clockin_dt is not None and clockout_dt is not None:
                duration_delta = clockout_dt - clockin_dt
                # Format duration as hours:minutes
                total_seconds = int(duration_delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f"{hours}h {minutes}m"
            else: 
                duration = "-----"
                
            clock_row = {
                "clockin": clockin, 
                "clockout": clockout,
                "date": date_str,
                "duration": duration
            }
            time_list.append(clock_row)
        
        return time_list
    

    def assign(self):
        people_list = self.field_parser()
        index = 0
        for person in people_list: 
            ten_times = self.time_parser(person["employee_id"])
            people_list[index]["times"] = ten_times
            index +=1
        self.results = people_list
        return people_list
        

class mailer():
    def __init__(self):
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.week = self.today - timedelta(days=7)
        self.month = self.today - timedelta(days=30)
        self.user_handle = Handler("user")
        config = Setting()
        self.sender = config.sender_email
        self.spass = config.sender_password
        self.last_email = config.last_email

    def run(self):
        threads = []
        t1 = threading.Thread(target=self.save_report)
        t2 = threading.Thread(target=self.send_now)
        threads.extend([t1, t2])
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def generate_report(self, later):
        start_date = date.today().strftime("%Y-%m-%d")
        end_date = later.strftime("%Y-%m-%d")
        query = f"""
            SELECT t.work_date, t.clock_in, t.clock_out,
                p.employee_id, p.first_name, p.last_name,
                p.email, p.phone, p.employee_role, p.position, p.department
            FROM timesheet_database t
            JOIN people_database p ON p.employee_id = t.employee_id
            WHERE t.work_date BETWEEN '{end_date}' AND '{start_date}'
            ORDER BY t.work_date, t.clock_in;
        """
        data = self.user_handle.send_query(query)
        cleaned_data = []
        for row in data:
            work_date = row[0] if len(row) > 0 else None
            clock_in = row[1] if len(row) > 1 else None
            clock_out = row[2] if len(row) > 2 else None

            clock_in_time = None
            clock_out_time = None
            if clock_in is not None:
                clock_in_time = clock_in.replace(tzinfo=None)
            if clock_out is not None:
                clock_out_time = clock_out.replace(tzinfo=None)

            

            cleaned_data.append((work_date, clock_in_time, clock_out_time) + row[3:])
        columns = ["work_date", "clock_in", "clock_out", "id", "first_name", 
                "last_name", "email", "phone", "role", "position", "department"]

        df = pd.DataFrame(cleaned_data, columns=columns)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output


    def save_report(self):
        for freq, delta in [("daily", self.yesterday), ("weekly", self.week), ("monthly", self.month)]:
            report_bytes = self.generate_report(delta)
            scanner_dir = os.path.dirname(os.path.abspath(__file__))
            save_folder = os.path.join(scanner_dir, "saved_reports")
            os.makedirs(save_folder, exist_ok=True)

            filename = f"timesheet_{self.today:%m-%d-%Y}_{freq}.xlsx"
            file_path = os.path.join(save_folder, filename)
            with open(file_path, "wb") as f:
                f.write(report_bytes.getbuffer())
            print(f"Excel file saved at {file_path}")

    def send_now(self):
        mail_list = self.get_emails()
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(self.sender, self.spass)
        except Exception as e:
            print(f"SMTP connection failed: {e}")
            return

        for freq, emails in mail_list.items():
            if not emails:
                continue
            if freq == "now":
                report_bytes = self.generate_report(self.yesterday)
                for receiver in emails:
                    msg = MIMEMultipart()
                    msg['From'] = self.sender
                    msg['To'] = receiver
                    msg['Subject'] = f"TimeWise {freq.title()} Report {self.today}"

                    part = MIMEApplication(report_bytes.getvalue(),
                                        Name=f"timesheet_{self.today:%m-%d-%Y}.xlsx")
                    part['Content-Disposition'] = f'attachment; filename="timesheet_{self.today:%m-%d-%Y}.xlsx"'
                    msg.attach(part)

                    try:
                        server.sendmail(self.sender, receiver, msg.as_string())
                        print(f"Email sent to {receiver} successfully!")
                    except Exception as e:
                        print(f"Error sending email to {receiver}: {e}")
        server.quit()

    def get_emails(self):
        data = self.user_handle.send_query("SELECT * FROM email_list;")
        mailing_list = {"now":[], "daily": [], "weekly": [], "monthly": []}
        for email, freq in data:
            mailing_list[freq].append(email)
        return mailing_list

class Auto_send():
    def __init__(self):
        self.userhandle = Handler("user")
        
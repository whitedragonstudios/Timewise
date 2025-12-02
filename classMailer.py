import smtplib, threading, pandas as pd, os
from classSettings import Setting
from io import BytesIO
from classHandler import Handler
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import date, timedelta

# for emailing to work do this on your Gmail account
#Go to your Google account security settings
#Enable 2-Step Verification
#Generate an App Password
#Use that 16-character code instead of your normal password

class Mailer():
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

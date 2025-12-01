import datetime as dt
from datetime import datetime as dt, timezone
from classHandler import Handler


# Person takes input from idscan and stores and updates all information to retrieve employee data and update timesheets
# A new instance of person is initalized with each scan
class Person():
    def __init__(self, idnumber, recent_list):
        self.id = int(idnumber)
        # recent list handles live updates to the home screen and reports from what was entered in the database.
        self.recent = recent_list
        # Handler instance connects to db
        self.handle = Handler(profile="user")
        # Upon init idnumber is used to look_up data in people_database
        data = self.look_up()
        if data:
            # if data is returned the rest of the methods are called.
            self.assign(data)
            self.update_DB()
            self.recent_list(50)
        else:
            # if the id is not valid default_person provides valid feedback to flask
            data = Default_Person(self.recent, self.id)
            self.assign([data.idnumber, data.fname, data.lname, data.email, data.phone, data.pic, data.role, data.position, data.department])
        

    # Queries the people_database for employee information reuturns set of tuples.
    def look_up(self):
        employee = self.handle.send_query(f"""
            SELECT employee_id, first_name, last_name, email, phone, pic_path, employee_role, position, department
            FROM people_database
            WHERE employee_id = {self.id}""")
        if not employee:
            return None # return none to use default_person
        return employee[0] #query returns a list of tuples index 0 bypasses dealing with the list.


    # Assign takes the place of initalizing data in case no data is returned from lookup assign allows for graceful failure.
    def assign(self, data):
        # These attributes are accessed by flask
        self.idnumber = data[0]
        self.fname = data[1]
        self.lname = data[2]
        self.email = data[3]
        self.phone = data[4]
        self.pic = data[5]
        self.role = data[6]
        self.position = data[7]
        self.department = data[8]
        return data # Data is returned for flexibility in use instead of using object attributes.


    # Update DB sends the employees ID to the timesheet database for record keeping.
    def update_DB(self):
        # Latest sends query to determine if the employee needs to be logged as clocking in or clocking out.
        latest = self.handle.send_query(f"""
            SELECT clock_in, clock_out FROM timesheet_database
            WHERE employee_id = {self.id}
            ORDER BY clock_in DESC LIMIT 1;""")
        # prevent double scans by getting current time
        now = dt.now(timezone.utc)
        debounce = 1
        # If clock in or clock out are not in the database insert new entry using clock in
        if not latest:
            self.handle.send_command(f"INSERT INTO timesheet_database (employee_id, clock_in) VALUES ({self.id}, NOW());")
            action = "Clock In"
        else:
            clock_in, clock_out = latest[0]
            if clock_out is None:
                # Check that debounce secounds has passed since last scan
                if (now - clock_in).total_seconds() <= debounce:
                    print(f"Duplicate scan ignored for ID {self.id}")
                    return
                # If only clock in is present updates the entry with a clockout time.
                self.handle.send_command(f"UPDATE timesheet_database SET clock_out = NOW() WHERE employee_id = {self.id} AND clock_out IS NULL;")
                action = "Clock Out"
            # If latest was present and not clock in then next entry will be a clock in
            else:
                if (now - clock_out).total_seconds() <= debounce:     
                    print(f"Duplicate scan ignored for ID {self.id}")
                    return
                self.handle.send_command(f"INSERT INTO timesheet_database (employee_id, clock_in) VALUES ({self.id}, NOW());")
                action = "Clock In"
                    
                
        # Sends query to verify and display data commited to db. Query accounts for clock in or clock out conditions
        data = self.handle.send_query(f"""SELECT p.first_name, p.last_name,
                CASE WHEN t.clock_out IS NULL THEN t.clock_in ELSE t.clock_out 
                END AS event_time,
                CASE WHEN t.clock_out IS NULL THEN 'Clock In' ELSE 'Clock Out' 
                END AS event_type
            FROM people_database p
            JOIN timesheet_database t ON p.employee_id = t.employee_id
            WHERE p.employee_id = {self.id}
            ORDER BY t.clock_in DESC LIMIT 2;""") # limit 2 gets in and out time for duration not implimented
        
        if not data:
            return #don't update return_data

        time = data[0][2]
        # Check if datetime object was returned
        if isinstance(time, str):
            time = dt.fromisoformat(time)
        time_str = time.strftime("%I:%M %p %d-%m") #Format date time object to string
        direction = "==>" if action == "Clock In" else "<==" # connditional to determine which arrow to use.
        self.io = "IN"if action == "Clock In" else "OUT" # conditional to determine which word to use.
        #self.return_data = f"{self.io} {time_str} {direction} {data[0][0]} {data[0][1]}"
        self.return_data = {"io": self.io, "time": time_str, "fname": data[0][0], "lname": data[0][1]}
        print(self.return_data)
        return self.return_data # returns formatted data which can be added to recent list.


    # Live view of recent scan in's limted by lenght.
    def recent_list(self, length):
        #insert return_data from update_db at the top of the list
        self.recent.insert(0, self.return_data)
        # if the list is longer that length remove old entries. while ensures the list is never longer even if there are persestent data errors. 
        while len(self.recent) > length:
            self.recent.pop(-1)
        return self.recent # Returns a list of entries most recent at the top.


# Default person allows for graceful failure of id's not in the database.
class Default_Person:
    def __init__(self, recent_list, scan):
        # same attributes as the person class
        self.idnumber = scan
        self.fname = "Error"
        self.lname = "Invalid ID"
        self.email = " "
        self.phone = " "
        self.pic = "error.jpg" # error.jpg is a question mark picture
        self.role = " "
        self.position = " "
        self.department = " "
        self.recent = recent_list
        self.time=dt.now().strftime("%H:%M") # Uses system time because database is not appended.
        # recent list works the same as for the person class
    def recent_list(self, length):
        person_string = f"{self.time} ==> {self.fname} {self.lname}"
        self.recent.insert(0, person_string)
        while len(self.recent) > length:
            self.recent.pop(-1)
        return self.recent
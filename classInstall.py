import os, platform, subprocess, sys, shutil
from datetime import datetime as dt
from psycopg2 import OperationalError, sql
from time import sleep
from classHandler import Handler
from classSettings import Setting

# Postgre_Install handles the installation process and checks for required packages and databases
class Postgre_Install:
    def __init__(self):
        # Detect OS
        self.system = platform.system().lower()
        # Create instance of Handler with admin privilages
        self.admin = Handler("admin")
        # Create instance of Handler with user privilages for normal operations
        self.user_handle = Handler("user")


    # List of all likely psql paths
    def path_list(self):
        return [
            r"C:\Program Files\PostgreSQL\18\bin",
            r"C:\Program Files\PostgreSQL\17\bin",
            r"C:\Program Files\PostgreSQL\16\bin",
            r"C:\Program Files\PostgreSQL\15\bin",
            r"C:\Program Files\PostgreSQL\14\bin",
            r"C:\Program Files\PostgreSQL\13\bin",
            r"C:\Program Files\PostgreSQL\12\bin",
            r"C:\Program Files\PostgreSQL\11\bin",
            r"C:\Program Files\PostgreSQL\10\bin",
            r"C:\Program Files\PostgreSQL\9.6\bin",
            r"C:\Program Files (x86)\PostgreSQL\13\bin",
            r"C:\Program Files (x86)\PostgreSQL\12\bin",
            r"/usr/local/bin",
            r"/usr/local/pgsql/bin",
            r"/Library/PostgreSQL/18/bin",
            r"/Library/PostgreSQL/17/bin",
            r"/Library/PostgreSQL/16/bin",
            r"/Library/PostgreSQL/15/bin",
            r"/Library/PostgreSQL/14/bin",
            r"/opt/homebrew/bin",
            r"/opt/homebrew/opt/postgresql@16/bin",
            r"/opt/homebrew/opt/postgresql@15/bin",
            r"/opt/homebrew/opt/postgresql@14/bin",
            r"/opt/homebrew/opt/postgresql@13/bin",
            r"/usr/bin",
            r"/usr/local/bin",
            r"/usr/pgsql-18/bin",
            r"/usr/pgsql-17/bin",
            r"/usr/pgsql-16/bin",
            r"/usr/pgsql-15/bin",
            r"/usr/pgsql-14/bin",
            r"/usr/lib/postgresql/18/bin",
            r"/usr/lib/postgresql/17/bin",
            r"/usr/lib/postgresql/16/bin",
            r"/usr/lib/postgresql/15/bin",
            r"/usr/lib/postgresql/14/bin",
            r"/opt/postgres/18/bin",
            r"/opt/postgres/17/bin",
            r"/opt/postgres/16/bin",
            r"/opt/postgres/15/bin",
            r"/usr/lib/aarch64-linux-gnu/postgresql/16/bin",
            r"/usr/lib/arm-linux-gnueabihf/postgresql/15/bin",
            r"/usr/local/pgsql/bin",
            r"/opt/pgsql/bin",
            r"/usr/local/pgsql/bin",
            r"/var/lib/postgresql/bin",
            r"/mnt/c/Program Files/PostgreSQL/16/bin",
        ]


    # Automatically looks for PostgreSQL install
    def check_install(self):
        print("Checking for PostgreSQL installation...")
        try:
            # Try to connect to the default postgres database (not scanner which may not exist)
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            temp_admin.disconnect()
            print("Connection to default psql server confirmed.")
            return True
        except Exception as e:
            print(f"Failed to connect to psql server: {e}")
            print("Locating installation manually")
        
        # Search through every likely Path for psql
        for path in self.path_list():
            # Check which version of psql to look for.
            if os.name == "nt":
                bin_name = "psql.exe"
            else:
                bin_name = "psql"
            psql_location = os.path.join(path, bin_name)
            # Check Path against psql location
            if os.path.exists(psql_location):
                print(f"Found PostgreSQL at: {psql_location}")
                # Append env:PATH to include psql's path for the future
                if os.name == "nt":
                    # Set path for windows
                    subprocess.run(f'setx PATH "%PATH%;{path}"', shell=True)
                else:
                    # Set path for linux/mac
                    with open(os.path.expanduser("~/.bashrc"), "a") as f:
                        f.write(f'\nexport PATH="$PATH:{path}"\n')
                print(f"Added '{path}' to PATH.")
                return True
        
        # If Path cannot be located function returns false
        if shutil.which("psql") is None:
            print("Failure: PATH detection \n!!! Could not locate PostgreSQL installation !!!\nYou must install PostgreSQL")
            return False


    # Detect os and automaticaly install psql.
    def install_psql(self):
        print(self.system.title(), " detected")
        # Check for windows OS
        if self.system == "windows":
            print("Installing PostgreSQL with Chocolatey")
            # Install postgresql with chocolatey
            cmd = "choco install postgresql --yes"
        # Check for Mac OS
        elif self.system == "darwin":
            # Install postgresql with homebrew
            print("Installing PostgreSQL with Homebrew")
            cmd = "brew install postgresql"
        # Check for Linux OS
        elif self.system == "linux":
            distro = platform.freedesktop_os_release().get("ID", "").lower() if hasattr(platform, "freedesktop_os_release") else ""
            print(f"Distro detected: {distro}")
            # Find package managner
            if shutil.which("apt"):
                # Install postgresql with apt
                cmd = "sudo apt update && sudo apt install -y postgresql-client"
            elif shutil.which("dnf"):
                # Install postgresql with dnf
                cmd = "sudo dnf install -y postgresql"
            elif shutil.which("yum"):
                # Install postgresql with yum
                cmd = "sudo yum install -y postgresql"
            elif shutil.which("pacman"):
                # Install postgresql with pacman
                cmd = "sudo pacman -Sy postgresql --noconfirm"
            else:
                # Could not determine linux distro
                print("Failure: Linux Distro detection \n!!! Automatic installation failed !!!\nPlease install PostgreSQL manually then try running this program again")
                return False
        else:
            # Could not determine OS
            print("Failure: OS detection \n!!! Automatic installation failed !!!\nPlease install PostgreSQL manually then try running this program again")
            return False
        installed = True
        try:
            # Send the correct OS command to shell
            result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
            print(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            print(f"Command failed: {cmd}")
            print(e.stderr.strip())
            installed = False
        if installed == True:
            print(">>> PostgreSQL sucessfully installed <<<")
            return True
        else:
            print("Failure: installing psql\n!!! Automatic installation failed !!!\nPlease install PostgreSQL manually then try running this program again")
            return False


    # Setup the database that you will need for the program to run
    def create_database(self):
        print("No Databases found: creating them")
        try:
            # Make sure we're connected to postgres database as admin
            self.admin.disconnect()
            self.admin = Handler(profile="admin", dbname="postgres")
            self.admin.connect()
            
            # Try to create the user, but don't fail if it exists
            try:
                self.admin.send_command(sql.SQL("CREATE USER marcus WITH PASSWORD 'stoic';"))
                print("User 'marcus' created successfully")
            except Exception as e:
                if "already exists" in str(e):
                    print("User 'marcus' already exists, continuing...")
                else:
                    raise

            # Create database owned by the new user
            try:
                self.admin.send_command(sql.SQL("CREATE DATABASE scanner OWNER marcus;"))
                print("Database 'scanner' created successfully")
            except Exception as e:
                if "already exists" in str(e):
                    print("Database 'scanner' already exists, continuing...")
                else:
                    raise

            # NOW disconnect from postgres and connect to scanner as marcus
            self.admin.disconnect()
            self.user_handle = Handler(profile="user", dbname="scanner")
            self.user_handle.connect()

            # Create schema and set search path
            self.user_handle.send_command(sql.SQL("CREATE SCHEMA IF NOT EXISTS public;"))
            self.user_handle.send_command(sql.SQL("SET search_path TO public;"))

            # Create tables (now owned by marcus since we're connected as marcus)
            tables = {
                "config_database": "CREATE TABLE config_database (key VARCHAR(50) PRIMARY KEY, value VARCHAR(128));",
                "email_list": "CREATE TABLE email_list(key VARCHAR(255) PRIMARY KEY, value VARCHAR(8));",
                "people_database": (
                    "CREATE TABLE people_database (employee_id INTEGER PRIMARY KEY, first_name VARCHAR(50), "
                    "last_name VARCHAR(50), email VARCHAR(50), phone VARCHAR(15), pic_path VARCHAR(128) UNIQUE, "
                    "employee_role VARCHAR(50), position VARCHAR(50), department VARCHAR(50));"
                ),
                "timesheet_database": (
                    "CREATE TABLE timesheet_database (id SERIAL PRIMARY KEY, employee_id INTEGER NOT NULL "
                    "REFERENCES people_database(employee_id) ON DELETE CASCADE, clock_in TIMESTAMPTZ DEFAULT NOW(), "
                    "clock_out TIMESTAMPTZ, work_date DATE DEFAULT CURRENT_DATE);"
                ),
                "news_database" : ("CREATE TABLE news_database (id SERIAL PRIMARY KEY, src TEXT, art TEXT, url TEXT);"),
                "weather_database" : ("CREATE TABLE weather_database (key VARCHAR(255) PRIMARY KEY, value VARCHAR(255));")
                }

            for name, command in tables.items():
                self.user_handle.send_command(sql.SQL(command))

            print("Tables created successfully")

            # Insert default config data
            start_config = Setting(autorun=False).start_settings()
            for k, v in start_config.items():
                try:
                    self.user_handle.update_database("config_database", "key", "value", k, v, keep_open=True)
                except Exception as e:
                    print(f"Error inserting default config '{k}': {e}")

            # Add test data
            self.insert_test_data()

            print("@@@ Database creation complete @@@")

            # Verify table creation
            for table in tables.keys():
                self.user_handle.send_query(f"SELECT * FROM {table};")

            self.user_handle.disconnect()
            return True

        except Exception as e:
            print(f"Failure in create_database: {e}")
            import traceback
            traceback.print_exc()
            return False


    # Check if the database and required tables exist
    def check_database(self):
        print("Checking if scanner is fully initialized.")
        try:
            self.user_handle.connect()
            required_tables = [
                "config_database",
                "timesheet_database",
                "people_database",
                "email_list"
            ]
            # Validate each table exists
            for table in required_tables:
                self.user_handle.send_query(
                    sql.SQL("SELECT 1 FROM {} LIMIT 0;").format(sql.Identifier(table))
                )
            print("Database scanner is fully initialized with the required tables.")
            return True
        except OperationalError as e:
            # Missing DB or authentication failure
            if e.pgcode in ("3D000", "28P01"):
                print("!!! Failure: credentials not created !!!")
                print("Database: scanner\nor\nUser: marcus")
                return False
            # Missing table
            if e.pgcode == "42P01":
                print("Database exists, but one or more essential tables are missing.")
                return False
            # Any other OperationalError
            print(f"Database check failed\n{e}")
            return False
        except Exception as e:
            print(f"Unexpected error during database check: {e}")
            return False
        finally:
            self.user_handle.disconnect()


    # Testing method for development
    def insert_test_data(self):
        sample_people = [
            (11111111, {"first_name": "Han", "last_name": "Solo", "email": "hsolo@scanner.com","phone": "100-555-1976", "pic_path": "11111111.jpg", "employee_role": "Pilot", "position": "Scoudrel", "department": "Only in it for the money"}),
            (22222222, {"first_name": "Luke", "last_name": "Skywalker", "email": "luke@scanner.com", "phone": "100-555-1234", "pic_path": "22222222.jpg", "employee_role": "", "position": "Jedi Master", "department": "Like his father"}),
            (33333333, {"first_name": "Jaina", "last_name": "Solo", "email": "jsolo@scanner.com", "phone": "100-555-4321", "pic_path": "33333333.jpg", "employee_role": "Sword of the Jedi", "position": "", "department": "Jedi Order"}),
        ]
        for employee_id, fields in sample_people:
            try:
                self.user_handle.update_people(employee_id, fields)  # Changed from self.admin
            except Exception as e:
                print("Error adding sample data to people_database:", e)

        sample_emails = {"marcus.aurelius@scanner.com": "daily",
                        "test@scanner.com": "weekly",
                        "scanner@scanner.com": "monthly"}
        for k,v in sample_emails.items():
            try:
                self.user_handle.update_database("email_list", "key", "value",  k, v, keep_open=True)  # Changed from self.admin
            except Exception as e: 
                print("Error adding sample data to email_list:",e)


    # This method controls the flow of the entire class.
    # Call this method in order to begin initalization fo the program.
    def run(self):
        failure_detected = False
        # Check/Install PostgreSQL
        if not self.check_install():
            ans = input("PostgreSQL not found. Install automatically? (y/n): ").lower().strip()
            if ans == "y":
                if not self.install_psql():
                    print("!!! FATAL: Automatic PostgreSQL installation failed. Cannot proceed. !!!")
                    failure_detected = True
            else:
                print("!!! FATAL: PostgreSQL is required and was not installed. Cannot proceed. !!!")
                failure_detected = True
        # Exit if installation failed or was refused
        if failure_detected:
            sleep(5)
            return False

        # Check/Create Databases
        print("\n--- Database Setup ---")
        if not self.check_database():
            print("Attempting to create Database and User...")
            if not self.create_database():
                print("!!! FATAL: Database creation/verification failed. Cannot proceed. !!!")
                failure_detected = True
        else:
            print("Database already exists. Setup skipped.")


    def drop_database(self, dropDB):
        try:
            # IMPORTANT: Must be connected to a DIFFERENT database (like postgres) to drop scanner
            # Disconnect current connection first
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
            
            # Connect to postgres database (not scanner) to drop scanner
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            temp_admin.send_command(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE);").format(sql.Identifier(dropDB)))
            temp_admin.disconnect()
            print(f"Database {dropDB} deleted")
        except Exception as e:
            print(f"Failed to drop database: {e}")


    def drop_user(self, dropUser):
        try:
            # First reassign ownership and drop dependencies
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
                
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            
            # Drop all objects owned by the user
            temp_admin.send_command(sql.SQL("DROP OWNED BY {} CASCADE;").format(sql.Identifier(dropUser)))
            # Now drop the user
            temp_admin.send_command(sql.SQL("DROP USER IF EXISTS {};").format(sql.Identifier(dropUser)))
            temp_admin.disconnect()
            print(f"User {dropUser} deleted")
        except Exception as e:
            print(f"Failed to drop user '{dropUser}': {e}")


    # quick function to delete tables.
    def drop_tables(self, table_name):
        try:
            # Make sure we're connected to the scanner database
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
            
            # Check if scanner database exists first
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            
            result = temp_admin.send_query(
                "SELECT 1 FROM pg_database WHERE datname='scanner';"
            )
            
            if not result:
                print(f"Database 'scanner' does not exist, skipping table drop for {table_name}")
                temp_admin.disconnect()
                return
            
            temp_admin.disconnect()
            
            # Now connect to scanner to drop the table
            self.admin = Handler(profile="admin", dbname="scanner")
            self.admin.connect()
            self.admin.send_command(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table_name)))
            self.admin.disconnect()
            print(f"Table {table_name} deleted")
        except Exception as e:
            print(f"Failed to drop {table_name}: {e}")

            
   # function for uninstalling postgresql for clean installs.
    def uninstall_psql(self):
        # Delete in correct order: tables -> database -> user
        print("Clearing databases\n\n\n")
        # First, make sure we're connected to postgres db, not scanner
        try:
            if hasattr(self, 'admin'):
                self.admin.disconnect()
            if hasattr(self, 'user_handle'):
                self.user_handle.disconnect()
        except:
            pass
        # Reconnect to postgres database
        self.admin = Handler(profile="admin", dbname="postgres")
        self.admin.connect()
        
        # Drop the database (this will drop all tables inside it)
        self.drop_database('scanner')
        # Then drop the user
        self.drop_user('marcus')
        print("Starting uninstall of PostgreSQL\n\n\n")
        print(f"Detected OS: {self.system.title()}")
        try:
            # Detect Windows - use Chocolatey
            if self.system == "windows":
                print("Uninstalling PostgreSQL on Windows...")
                # Method 1: Try Chocolatey
                if shutil.which("choco"):
                    print("Using Chocolatey...")
                    cmd = "choco uninstall postgresql --yes"
                # Method 2: Try official uninstaller
                else:
                    print("Looking for PostgreSQL uninstaller...")
                    # Common PostgreSQL installation paths
                    possible_paths = [
                        r"C:\Program Files\PostgreSQL\18\uninstall-postgresql.exe",
                        r"C:\Program Files\PostgreSQL\17\uninstall-postgresql.exe",
                        r"C:\Program Files\PostgreSQL\16\uninstall-postgresql.exe",
                        r"C:\Program Files\PostgreSQL\15\uninstall-postgresql.exe",
                        r"C:\Program Files\PostgreSQL\14\uninstall-postgresql.exe",
                    ]
                    uninstaller = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            uninstaller = path
                            break
                    if uninstaller:
                        print(f"Found uninstaller at: {uninstaller}")
                        # Run uninstaller in unattended mode
                        cmd = f'"{uninstaller}" --mode unattended'
                    else:
                        print("PostgreSQL uninstaller not found.")
                        print("Please uninstall PostgreSQL manually:")
                        print("  1. Open Control Panel > Programs and Features")
                        print("  2. Find 'PostgreSQL' in the list")
                        print("  3. Click 'Uninstall'")
                        print("\nOr run the uninstaller directly from:")
                        print("  C:\\Program Files\\PostgreSQL\\[version]\\uninstall-postgresql.exe")
                        return False
            # Detect macOS - use Homebrew
            elif self.system == "darwin":
                print("Uninstalling PostgreSQL using Homebrew...")
                if shutil.which("brew") is None:
                    print("Homebrew not found. Cannot uninstall automatically on macOS.")
                    print("Please uninstall PostgreSQL manually:")
                    print("  - If installed via Postgres.app: Move Postgres.app to Trash")
                    print("  - If installed via installer: Run the uninstaller from /Library/PostgreSQL/")
                    return False
                cmd = "brew uninstall postgresql"
            # Detect Linux - detect package manager
            elif self.system == "linux":
                if shutil.which("apt"):
                    print("Uninstalling PostgreSQL using apt...")
                    cmd = "sudo apt remove --purge -y postgresql* && sudo apt autoremove -y"
                elif shutil.which("dnf"):
                    print("Uninstalling PostgreSQL using dnf...")
                    cmd = "sudo dnf remove -y postgresql*"
                elif shutil.which("yum"):
                    print("Uninstalling PostgreSQL using yum...")
                    cmd = "sudo yum remove -y postgresql*"
                elif shutil.which("pacman"):
                    print("Uninstalling PostgreSQL using pacman...")
                    cmd = "sudo pacman -Rns --noconfirm postgresql"
                else:
                    print("Could not detect Linux package manager.")
                    print("Please uninstall PostgreSQL manually using your distribution's package manager.")
                    return False
            else:
                print("Unsupported OS. Cannot uninstall PostgreSQL automatically.")
                print(f"Detected system: {self.system}")
                return False
            # Execute the uninstall command
            print(f"Running command: {cmd}")
            result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
            print(result.stdout.strip())
            print("^^^ PostgreSQL successfully uninstalled ^^^")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to uninstall PostgreSQL.")
            print(f"Command: {cmd}")
            print(f"Error: {e.stderr.strip()}")
            print("\nYou may need to:")
            print("  1. Run this script with administrator/sudo privileges")
            print("  2. Manually uninstall PostgreSQL using your system's package manager")
            return False
        except Exception as e:
            print(f"Unexpected error during uninstallation: {e}")
            return False
            

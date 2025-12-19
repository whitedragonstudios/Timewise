import os, platform, subprocess, sys, shutil
from datetime import datetime as dt
from psycopg2 import OperationalError, sql
from time import sleep
from classHandler import Handler
from classSettings import Setting


class Postgre_Install:
    def __init__(self):
        self.system = platform.system().lower()
        self.admin = Handler("admin")
        self.user_handle = Handler("user")
        self.redis_installed = False
        self.postgres_installed = False


    # ==================== PATH DETECTION ====================
    def get_postgresql_paths(self):
        """Returns list of common PostgreSQL installation paths"""
        return [
            # Windows paths
            r"C:\Program Files\PostgreSQL\18\bin",
            r"C:\Program Files\PostgreSQL\17\bin",
            r"C:\Program Files\PostgreSQL\16\bin",
            r"C:\Program Files\PostgreSQL\15\bin",
            r"C:\Program Files\PostgreSQL\14\bin",
            r"C:\Program Files\PostgreSQL\13\bin",
            r"C:\Program Files (x86)\PostgreSQL\16\bin",
            r"C:\Program Files (x86)\PostgreSQL\15\bin",
            # macOS paths
            r"/Library/PostgreSQL/18/bin",
            r"/Library/PostgreSQL/17/bin",
            r"/Library/PostgreSQL/16/bin",
            r"/Library/PostgreSQL/15/bin",
            r"/opt/homebrew/bin",
            r"/opt/homebrew/opt/postgresql@16/bin",
            r"/opt/homebrew/opt/postgresql@15/bin",
            r"/opt/homebrew/opt/postgresql@14/bin",
            r"/usr/local/bin",
            # Linux paths
            r"/usr/bin",
            r"/usr/pgsql-18/bin",
            r"/usr/pgsql-17/bin",
            r"/usr/pgsql-16/bin",
            r"/usr/pgsql-15/bin",
            r"/usr/lib/postgresql/18/bin",
            r"/usr/lib/postgresql/17/bin",
            r"/usr/lib/postgresql/16/bin",
            r"/usr/lib/postgresql/15/bin",
            r"/usr/lib/postgresql/14/bin",
            r"/opt/postgres/16/bin",
            r"/usr/lib/aarch64-linux-gnu/postgresql/16/bin",
            r"/usr/lib/arm-linux-gnueabihf/postgresql/15/bin",
            r"/usr/local/pgsql/bin",
            r"/opt/pgsql/bin",
            r"/var/lib/postgresql/bin",
            # WSL paths
            r"/mnt/c/Program Files/PostgreSQL/16/bin",
        ]


    def get_redis_paths(self):
        """Returns list of common Redis installation paths"""
        return [
            # Windows paths
            r"C:\Program Files\Redis\redis-server.exe",
            r"C:\Redis\redis-server.exe",
            # macOS/Linux paths
            r"/usr/local/bin/redis-server",
            r"/usr/bin/redis-server",
            r"/opt/homebrew/bin/redis-server",
            r"/opt/redis/bin/redis-server",
        ]


    # ==================== POSTGRESQL INSTALLATION ====================

    def check_postgresql(self):
        """Check if PostgreSQL is installed and accessible"""
        print("Checking for PostgreSQL installation...")
        
        # Try to connect to postgres database
        try:
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            temp_admin.disconnect()
            print("PostgreSQL server connection confirmed")
            self.postgres_installed = True
            return True
        except Exception as e:
            print(f"Cannot connect to PostgreSQL: {e}")
        
        # Search for psql binary
        psql_binary = "psql.exe" if os.name == "nt" else "psql"
        
        # Check if psql is in PATH
        if shutil.which("psql"):
            print("PostgreSQL found in system PATH")
            self.postgres_installed = True
            return True
        
        # Search known installation paths
        for path in self.get_postgresql_paths():
            psql_location = os.path.join(path, psql_binary)
            if os.path.exists(psql_location):
                print(f"Found PostgreSQL at: {psql_location}")
                self._add_to_path(path)
                self.postgres_installed = True
                return True
        
        print("!!! PostgreSQL not found on system !!!")
        return False


    def install_postgresql(self):
        """Automatically install PostgreSQL based on OS"""
        print(f"\n{'='*60}")
        print(f"Installing PostgreSQL on {self.system.title()}")
        print(f"{'='*60}\n")
        
        cmd = None
        
        if self.system == "windows":
            if shutil.which("choco"):
                print("Using Chocolatey package manager...")
                cmd = "choco install postgresql --yes -y --force"
            elif shutil.which("winget"):
                print("Using winget package manager...")
                cmd = "winget install -e --id PostgreSQL.PostgreSQL"
            else:
                print("!!! No package manager found (Chocolatey or winget required) !!!")
                print("Please install PostgreSQL manually:")
                print("  1. Download from: https://www.postgresql.org/download/windows/")
                print("  2. Or install Chocolatey: https://chocolatey.org/install")
                return False
                
        elif self.system == "darwin":
            if shutil.which("brew"):
                print("Using Homebrew package manager...")
                cmd = "brew install postgresql@16"
            else:
                print("!!! Homebrew not found !!!")
                print("Please install Homebrew first:")
                print('  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"')
                return False
                
        elif self.system == "linux":
            distro = self._get_linux_distro()
            print(f"Detected Linux distribution: {distro}")
            if shutil.which("apt"):
                print("Using apt package manager...")
                cmd = "sudo apt update && sudo apt install -y postgresql postgresql-contrib"
            elif shutil.which("dnf"):
                print("Using dnf package manager...")
                cmd = "sudo dnf install -y postgresql-server postgresql-contrib && sudo postgresql-setup --initdb && sudo systemctl enable postgresql && sudo systemctl start postgresql"
            elif shutil.which("yum"):
                print("Using yum package manager...")
                cmd = "sudo yum install -y postgresql-server postgresql-contrib && sudo postgresql-setup initdb && sudo systemctl enable postgresql && sudo systemctl start postgresql"
            elif shutil.which("pacman"):
                print("Using pacman package manager...")
                cmd = "sudo pacman -Sy --noconfirm postgresql && sudo systemctl enable postgresql && sudo systemctl start postgresql"
            elif shutil.which("zypper"):
                print("Using zypper package manager...")
                cmd = "sudo zypper install -y postgresql-server && sudo systemctl enable postgresql && sudo systemctl start postgresql"
            else:
                print("!!! Could not detect package manager !!!")
                print("Please install PostgreSQL manually using your distribution's package manager")
                return False
        else:
            print(f"!!! Unsupported operating system: {self.system} !!!")
            return False
        
        # Execute installation
        if cmd:
            try:
                print(f"\n>>> Input <<<")
                print(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
                print("\n<<< Output >>>")
                print(result.stdout.strip())
                print("\n^^^ PostgreSQL installed ^^^")
                
                # Wait for service to start
                sleep(3)
                self.postgres_installed = True
                return True
                
            except subprocess.CalledProcessError as e:
                print(f"\n!!! Installation failed !!!")
                print(f"<<< Output >>>")
                print(e.stderr.strip())
                return False
        
        return False


    # ==================== REDIS INSTALLATION ====================

    def check_redis(self):
        """Check if Redis is installed and accessible"""
        print("\nChecking for Redis installation...")
        
        # Check if redis-server is in PATH
        if shutil.which("redis-server"):
            print("Redis found in system PATH")
            self.redis_installed = True
            return True
        
        # Check common installation paths
        for path in self.get_redis_paths():
            if os.path.exists(path):
                print(f"Found Redis at: {path}")
                self._add_to_path(os.path.dirname(path))
                self.redis_installed = True
                return True
        
        print("Redis not found on system")
        return False


    def install_redis(self):
        """Automatically install Redis based on OS"""
        print(f"\n{'='*60}")
        print(f"Installing Redis on {self.system.title()}")
        print(f"{'='*60}\n")
        
        cmd = None
        
        if self.system == "windows":
            if shutil.which("choco"):
                print("Using Chocolatey package manager...")
                cmd = "choco install redis-64 --yes -y"
            elif shutil.which("winget"):
                print("Using winget package manager...")
                # Redis on Windows via Memurai (Redis-compatible)
                cmd = "winget install -e --id Memurai.Memurai-Developer"
            else:
                print("!!! No package manager found !!!")
                print("For Windows, you can:")
                print("  1. Install Chocolatey and run: choco install redis-64")
                print("  2. Download from: https://github.com/microsoftarchive/redis/releases")
                print("  3. Use Memurai (Redis-compatible): https://www.memurai.com/")
                return False
                
        elif self.system == "darwin":
            if shutil.which("brew"):
                print("Using Homebrew package manager...")
                cmd = "brew install redis && brew services start redis"
            else:
                print("!!! Homebrew not found !!!")
                return False
                
        elif self.system == "linux":
            if shutil.which("apt"):
                print("Using apt package manager...")
                cmd = "sudo apt update && sudo apt install -y redis-server && sudo systemctl enable redis-server && sudo systemctl start redis-server"
            elif shutil.which("dnf"):
                print("Using dnf package manager...")
                cmd = "sudo dnf install -y redis && sudo systemctl enable redis && sudo systemctl start redis"
            elif shutil.which("yum"):
                print("Using yum package manager...")
                cmd = "sudo yum install -y redis && sudo systemctl enable redis && sudo systemctl start redis"
            elif shutil.which("pacman"):
                print("Using pacman package manager...")
                cmd = "sudo pacman -Sy --noconfirm redis && sudo systemctl enable redis && sudo systemctl start redis"
            elif shutil.which("zypper"):
                print("Using zypper package manager...")
                cmd = "sudo zypper install -y redis && sudo systemctl enable redis && sudo systemctl start redis"
            else:
                print("!!! Could not detect package manager !!!")
                return False
        else:
            print(f"!!! Unsupported operating system: {self.system} !!!")
            return False
        
        # Execute installation
        if cmd:
            try:
                print(f"\n>>> Input <<<")
                print(f"Executing: {cmd}")
                result = subprocess.run(cmd, shell=True, check=True, text=True, capture_output=True)
                print("\n<<< Output >>>")
                print(result.stdout.strip())
                print("\n^^^ Redis installed ^^^")
                
                sleep(2)
                self.redis_installed = True
                return True
                
            except subprocess.CalledProcessError as e:
                print(f"\n!!! Installation failed !!!")
                print(f"<<< Output >>>")
                print(e.stderr.strip())
                print("\nRedis is optional. Continuing without it...")
                return False
        
        return False


    # ==================== DATABASE SETUP ====================

    def create_database(self):
        """Create database, user, tables, and populate with initial data"""
        print("Creating Database Schema")
        try:
            # Connect to postgres database as admin
            self.admin.disconnect()
            self.admin = Handler(profile="admin", dbname="postgres")
            self.admin.connect()
            # Create user
            try:
                self.admin.send_command(sql.SQL("CREATE USER marcus WITH PASSWORD 'stoic';"))
                print("User 'marcus' created")
            except Exception as e:
                if "already exists" in str(e):
                    print("User 'marcus' already exists")
                else:
                    raise

            # Create database
            try:
                self.admin.send_command(sql.SQL("CREATE DATABASE scanner OWNER marcus;"))
                print("Database 'scanner' created")
            except Exception as e:
                if "already exists" in str(e):
                    print("Database 'scanner' already exists")
                else:
                    raise

            # Switch to scanner database as marcus
            self.admin.disconnect()
            self.user_handle = Handler(profile="user", dbname="scanner")
            self.user_handle.connect()

            # Create schema
            self.user_handle.send_command(sql.SQL("CREATE SCHEMA IF NOT EXISTS public;"))
            self.user_handle.send_command(sql.SQL("SET search_path TO public;"))
            print("Schema configured")

            # Create tables
            self._create_tables()
            
            # Populate with data
            self._populate_initial_data()
            
            # Verify
            self._verify_database()
            
            self.user_handle.disconnect()
            
            print(f"\n{'='*60}")
            print("Database setup complete")
            print(f"{'='*60}\n")
            return True

        except Exception as e:
            print(f"\n!!! Database creation failed: {e} !!!")
            import traceback
            traceback.print_exc()
            return False


    def _create_tables(self):
        """Create all required database tables"""
        print("\nCreating tables...")
        tables = {
            "config_database": """
                CREATE TABLE IF NOT EXISTS config_database (
                    key VARCHAR(50) PRIMARY KEY, 
                    value VARCHAR(128)
                );""",
            "email_list": """
                CREATE TABLE IF NOT EXISTS email_list (
                    key VARCHAR(255) PRIMARY KEY, 
                    value VARCHAR(8)
                );""",
            "people_database": """
                CREATE TABLE IF NOT EXISTS people_database (
                    employee_id INTEGER PRIMARY KEY,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    email VARCHAR(50),
                    phone VARCHAR(15),
                    pic_path VARCHAR(128) UNIQUE,
                    employee_role VARCHAR(50),
                    position VARCHAR(50),
                    department VARCHAR(50)
                );""",
            "timesheet_database": """
                CREATE TABLE IF NOT EXISTS timesheet_database (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL REFERENCES people_database(employee_id) ON DELETE CASCADE,
                    clock_in TIMESTAMPTZ DEFAULT NOW(),
                    clock_out TIMESTAMPTZ,
                    work_date DATE DEFAULT CURRENT_DATE,
                    notes TEXT
                );""",
            "news_database": """
                CREATE TABLE IF NOT EXISTS news_database (
                    id SERIAL PRIMARY KEY,
                    src TEXT,
                    art TEXT,
                    url TEXT,
                    updated TIMESTAMPTZ DEFAULT NOW()
                );""",
            "weather_database": """
                CREATE TABLE IF NOT EXISTS weather_database (
                    key VARCHAR(255) PRIMARY KEY,
                    value VARCHAR(255)
                );""",
            "updates_database" : """
                CREATE TABLE IF NOT EXISTS updates_database (
                    key TEXT PRIMARY KEY, 
                    value TIMESTAMPTZ DEFAULT NOW());"""
            }

        for name, command in tables.items():
            try:
                self.user_handle.send_command(sql.SQL(command))
                print(f"  Created: {name}")
            except Exception as e:
                print(f"  !!! Failed to create {name}: {e} !!!")
                raise


    def _populate_initial_data(self):
        """Populate database with initial configuration and sample data"""
        print("\nPopulating initial data...")
        
        # Insert config data
        try:
            start_config = Setting(autorun=False).start_settings()
            for k, v in start_config.items():
                self.user_handle.update_database("config_database", "key", "value", k, v, keep_open=True)
            print("  Configuration data inserted")
        except Exception as e:
            print(f"  !!! Config data failed: {e} !!!")
            raise

        # Insert sample people
        sample_people = [
            (11111111, {
                "first_name": "Han",
                "last_name": "Solo",
                "email": "hsolo@timewise.com",
                "phone": "555-0001",
                "pic_path": "11111111.jpg",
                "employee_role": "Captain",
                "position": "Pilot",
                "department": "Flight Operations"
            }),
            (22222222, {
                "first_name": "Luke",
                "last_name": "Skywalker",
                "email": "lskywalker@timewise.com",
                "phone": "555-0002",
                "pic_path": "22222222.jpg",
                "employee_role": "Master",
                "position": "Jedi Knight",
                "department": "Force Development"
            }),
            (33333333, {
                "first_name": "Leia",
                "last_name": "Organa",
                "email": "lorgana@timewise.com",
                "phone": "555-0003",
                "pic_path": "33333333.jpg",
                "employee_role": "General",
                "position": "Leadership",
                "department": "Command"
            }),
            (44444444, {
                "first_name": "Chewbacca",
                "last_name": "",
                "email": "chewie@timewise.com",
                "phone": "555-0004",
                "pic_path": "44444444.jpg",
                "employee_role": "Co-Pilot",
                "position": "Engineer",
                "department": "Flight Operations"
            }),
        ]
        
        for employee_id, fields in sample_people:
            try:
                self.user_handle.update_people(employee_id, fields)
            except Exception as e:
                print(f"  Warning: Could not add employee {employee_id}: {e}")
        
        print("  Sample employees added")

        # Insert sample emails
        sample_emails = {
            "admin@timewise.com": "daily",
            "reports@timewise.com": "weekly",
            "hr@timewise.com": "monthly"
        }
        
        for email, freq in sample_emails.items():
            try:
                self.user_handle.update_database("email_list", "key", "value", email, freq, keep_open=True)
            except Exception as e:
                print(f"  Warning: Could not add email {email}: {e}")
        
        print("  Email list configured")

        updates = ["news", "weather", "config", "emails"]
        for column in updates:
            try:
                self.user_handle.update_database("updates_database", "key", "value", column, "NOW()", keep_open=True)
                print(f"{column} added to updates_database")
            except Exception as e:
                print(f"Warining Could not add {column} to updates_database: {e}")


    def _verify_database(self):
        """Verify all tables exist and have data"""
        print("\nVerifying database...")
        
        required_tables = {
            "config_database": 20,  # Minimum expected rows
            "people_database": 1,
            "email_list": 0,
            "timesheet_database": 0,  # Can be empty
            "news_database": 0,
            "weather_database": 0
        }
        
        for table, min_rows in required_tables.items():
            try:
                result = self.user_handle.send_query(f"SELECT COUNT(*) FROM {table};")
                count = result[0][0] if result else 0
                
                if count >= min_rows:
                    print(f"  Verified {table}: {count} rows")
                else:
                    print(f"  Warning: {table} has {count} rows (expected >= {min_rows})")
            except Exception as e:
                print(f"  !!! {table} verification failed: {e} !!!")
                raise


    def check_database(self):
        """Check if database is fully initialized with data"""
        print(f"\n{'='*20}")
        print("Checking Database Status")
        
        try:
            self.user_handle.connect()
            
            required_tables = [
                "config_database",
                "timesheet_database",
                "people_database",
                "email_list"
            ]
            
            # Check tables exist
            for table in required_tables:
                try:
                    self.user_handle.send_query(
                        sql.SQL("SELECT 1 FROM {} LIMIT 0;").format(sql.Identifier(table))
                    )
                except Exception:
                    print(f"!!! Table missing: {table} !!!")
                    return False
            
            # Check config has data
            config_data = self.user_handle.send_query("SELECT COUNT(*) FROM config_database;")
            if not config_data or config_data[0][0] == 0:
                print("!!! config_database is empty !!!")
                return False
            
            print("Database fully initialized")
            print(f"  - All tables present")
            print(f"  - Configuration loaded ({config_data[0][0]} settings)")
            return True
            
        except OperationalError as e:
            if e.pgcode in ("3D000", "28P01"):
                print("!!! Database or user credentials not found !!!")
            elif e.pgcode == "42P01":
                print("!!! One or more tables missing !!!")
            else:
                print(f"!!! Database check failed: {e} !!!")
            return False
        except Exception as e:
            print(f"!!! Unexpected error: {e} !!!")
            return False
        finally:
            self.user_handle.disconnect()


    # ==================== MAIN INSTALLATION FLOW ====================

    def run(self):
        """Main installation orchestrator"""
        print("#" + " "*20 + "#")
        print("#" + "TimeWise Gateway - Installation Wizard".center(58) + "#")
        print("#" + " "*20 + "#")
        print(f"Detected System: {self.system.title()}")
        print(f"Python Version: {sys.version.split()[0]}")
        print()
        
        failure = False
        
        # Step 1: PostgreSQL
        print("STEP 1: PostgreSQL")
        print("-" * 60)
        if not self.check_postgresql():
            print("\n>>> Input <<<")
            ans = input("PostgreSQL not found. Install automatically? (y/n): ").lower().strip()
            if ans == "y":
                if not self.install_postgresql():
                    print("\n!!! FATAL: PostgreSQL installation failed !!!")
                    failure = True
            else:
                print("\n!!! FATAL: PostgreSQL is required !!!")
                failure = True
        
        if failure:
            sleep(5)
            return False
        
        # Step 2: Redis (optional)
        print("\n\nSTEP 2: Redis (Optional - for caching)")
        print("-" * 60)
        if not self.check_redis():
            print("\n>>> Input <<<")
            ans = input("Redis not found. Install automatically? (y/n): ").lower().strip()
            if ans == "y":
                self.install_redis()
            else:
                print("\nSkipping Redis installation")
        
        # Step 3: Database Setup
        print("\n\nSTEP 3: Database Setup")
        print("-" * 60)
        if not self.check_database():
            print("\nDatabase needs initialization...")
            if not self.create_database():
                print("\n!!! FATAL: Database setup failed !!!")
                failure = True
        else:
            print("\nDatabase already configured")
        
        # Final status
        if not failure:
            print("#" + " "*58 + "#")
            print("#" + "Installation Complete!".center(58) + "#")
            print("#" + " "*58 + "#")
            print(f"{'#'*60}\n")
            print("PostgreSQL: Ready")
            print(f"Redis: {'Ready' if self.redis_installed else 'Not installed (optional)'}")
            print("Database: Ready")
            print("\n^^^ You can now start the application ^^^")
        else:
            print("#" + " "*58 + "#")
            print("#" + "Installation Failed".center(58) + "#")
            print("#" + " "*58 + "#")
            print(f"{'#'*60}\n")
            print("!!! Please fix the errors above and try again !!!")
        
        return not failure


    # ==================== UTILITY METHODS ====================

    def _add_to_path(self, path):
        """Add directory to system PATH"""
        try:
            if os.name == "nt":
                # Windows - requires admin privileges
                subprocess.run(f'setx PATH "%PATH%;{path}"', shell=True, check=False)
            else:
                # Unix-like systems
                shell_rc = os.path.expanduser("~/.bashrc")
                if self.system == "darwin":
                    shell_rc = os.path.expanduser("~/.zshrc")
                
                with open(shell_rc, "a") as f:
                    f.write(f'\nexport PATH="$PATH:{path}"\n')
                
                print(f"  Added to PATH (restart terminal to apply)")
        except Exception as e:
            print(f"  Warning: Could not add to PATH: {e}")


    def _get_linux_distro(self):
        """Get Linux distribution name"""
        try:
            if hasattr(platform, "freedesktop_os_release"):
                return platform.freedesktop_os_release().get("ID", "unknown")
        except:
            pass
        return "unknown"


    # ==================== MAINTENANCE METHODS ====================

    def drop_database(self, dbname):
        """Drop a database"""
        try:
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
            
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            temp_admin.send_command(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE);").format(sql.Identifier(dbname)))
            temp_admin.disconnect()
            print(f"Database '{dbname}' dropped")
        except Exception as e:
            print(f"!!! Failed to drop database '{dbname}': {e} !!!")


    def drop_table(self, table_name):
        """Drop a table from scanner database"""
        try:
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
            
            # Check if scanner exists
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            
            result = temp_admin.send_query("SELECT 1 FROM pg_database WHERE datname='scanner';")
            
            if not result:
                print(f"Database 'scanner' doesn't exist")
                temp_admin.disconnect()
                return
            
            temp_admin.disconnect()
            
            # Drop table
            self.admin = Handler(profile="admin", dbname="scanner")
            self.admin.connect()
            self.admin.send_command(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table_name)))
            self.admin.disconnect()
            print(f"Table '{table_name}' dropped")
        except Exception as e:
            print(f"!!! Failed to drop table '{table_name}': {e} !!!")


    def drop_user(self, username):
        """Drop a PostgreSQL user"""
        try:
            if hasattr(self, 'admin') and self.admin:
                self.admin.disconnect()
            
            temp_admin = Handler(profile="admin", dbname="postgres")
            temp_admin.connect()
            
            temp_admin.send_command(sql.SQL("DROP OWNED BY {} CASCADE;").format(sql.Identifier(username)))
            temp_admin.send_command(sql.SQL("DROP USER IF EXISTS {};").format(sql.Identifier(username)))
            temp_admin.disconnect()
            print(f"User '{username}' dropped")
        except Exception as e:
            print(f"!!! Failed to drop user '{username}': {e} !!!")


    def reset_database(self):
        """Complete database reset"""
        print("\n>>> Input <<<")
        print("WARNING: This will delete all data!")
        confirm = input("Type 'RESET' to confirm: ").strip()
        
        if confirm != "RESET":
            print("Reset cancelled")
            return False
        
        print("\nResetting database...")
        self.drop_database("scanner")
        self.drop_user("marcus")
        print("\nDatabase reset complete")
        print("Run the installer again to recreate the database")
        return True
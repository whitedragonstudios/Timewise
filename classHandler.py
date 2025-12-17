import psycopg2, os
from psycopg2 import sql

class Handler:
    def __init__(self, profile="marcus", dbname="scanner", info=False):
        # Set user and database properly
        if profile == "admin":
            self.user = "postgres"
            self.dbname = dbname or "postgres"
        elif profile == "superuser":
            self.user = "postgres"
            self.dbname = dbname or "scanner"
        else:
            self.user = "marcus"
            self.dbname = dbname or "scanner"

        self.password = "stoic"
        self.port = 5000
        self.host = "localhost"
        self.info = info
        self._shared_conn = None

    def connect(self):
        if self.info:
            print(f"""Connecting...
        ---Database: {self.dbname}
        ---User: {self.user}
        ---Port: {self.port}
        ---Host: {self.host}""")
        try:
            conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            conn.autocommit = True
            # Ensure public schema is used in this session
            with conn.cursor() as cur:
                cur.execute("SET search_path TO public;")
            return conn
        except Exception as e:
            print("Failed to connect:", e)
            raise

    def report_error(self, e):
        print("!!! PostgreSQL Error !!!")
        msg = e.pgerror.strip() if e.pgerror else str(e)
        print(f"Message: {msg}")
        if hasattr(e, 'diag') and e.diag:
            print(f"SQLSTATE: {e.pgcode}")
            if getattr(e.diag, 'message_detail', None):
                print(f"Details: {e.diag.message_detail.strip()}")
            if getattr(e.diag, 'context', None):
                print(f"Context: {e.diag.context.strip()}")
        print("\n")

    def send_command(self, cmd):
        conn = cur = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            if self.info:
                print("<<< Executing command >>>")
                print(cmd)
            cur.execute(cmd)
            conn.commit()
            if self.info:
                print(">>> Executed command <<<")
            for notice in conn.notices:
                print("NOTICE:", notice)
        except psycopg2.Error as e:
            if conn and not conn.closed:
                conn.rollback()
            self.report_error(e)
            raise
        finally:
            if cur: cur.close()
            if conn: conn.close()

    def send_query(self, query):
        conn = cur = None
        results = []
        try:
            conn = self.connect()
            cur = conn.cursor()
            if self.info:
                print("<<< Executing Query >>>")
                print(query)
            cur.execute(query)
            results = cur.fetchall()
            if self.info:
                print("--- Query Results ---")
                for row in results:
                    print(row)
                print("--- End Results ---")
            for notice in conn.notices:
                print("NOTICE:", notice)
            return results
        except psycopg2.Error as e:
            self.report_error(e)
            raise
        finally:
            if cur: cur.close()
            if conn: conn.close()

    def update_database(self, database, kname, vname, key, value, keep_open=False):
        conn = cur = None
        try:
            if keep_open:
                if not hasattr(self, "_shared_conn") or self._shared_conn is None or self._shared_conn.closed:
                    self._shared_conn = self.connect()
                conn = self._shared_conn
            else:
                conn = self.connect()

            cur = conn.cursor()
            cur.execute(
                sql.SQL("""
                    INSERT INTO {table} ({col_key}, {col_value})
                    VALUES (%s, %s)
                    ON CONFLICT ({col_key})
                    DO UPDATE SET {col_value} = EXCLUDED.{col_value};
                """).format(
                    table=sql.Identifier(database),
                    col_key=sql.Identifier(kname),
                    col_value=sql.Identifier(vname)
                ),
                (key, value)
            )
            conn.commit()
            #if self.info:
            print(f"Configuration key '{key}' updated to {value}")
        except psycopg2.Error as e:
            if conn and not conn.closed:
                conn.rollback()
            self.report_error(e)
            raise
        finally:
            if cur: cur.close()
            if not keep_open and conn and not conn.closed:
                conn.close()

    # Insert or update a person in people_database
    def update_people(self, employee_id, fields):
        messages = {"error": [], "warning": [], "info": [], "success": []}
        conn = cur = None
        try:
            conn = self.connect()
            cur = conn.cursor()
            cur.execute("SELECT employee_id FROM people_database WHERE employee_id = %s", (employee_id,))
            existing = cur.fetchone()
            
            if existing:
                update_fields = {k: v for k, v in fields.items() if v and str(v).strip()}
                if not update_fields:
                    messages["info"].append(f"No new data to update for employee {employee_id}")
                    print(f"No new data to update for employee {employee_id}")
                    return
                
                update_parts = sql.SQL(', ').join([
                    sql.SQL("{} = %s").format(sql.Identifier(k))
                    for k in update_fields.keys()
                ])
                
                query = sql.SQL("UPDATE people_database SET {updates} WHERE employee_id = %s;").format(
                    updates=update_parts
                )
                
                values = list(update_fields.values()) + [employee_id]
                messages["info"].append(f"Updated employee {employee_id}")
                if self.info:
                    print(f"Updating existing employee {employee_id} with values: {values}")
                cur.execute(query, values)
            else:
                # Employee doesn't exist - do INSERT with all fields
                columns = ['employee_id'] + list(fields.keys())
                values = [employee_id] + list(fields.values())
                placeholders = sql.SQL(', ').join([sql.Placeholder()] * len(values))
                
                query = sql.SQL("INSERT INTO people_database ({columns}) VALUES ({placeholders});").format(
                    columns=sql.SQL(', ').join(map(sql.Identifier, columns)),
                    placeholders=placeholders
                )
                messages["info"].append(f"Inserted new employee {employee_id}")
                if self.info:
                    print(f"Inserting new employee {employee_id} with values: {values}")
                cur.execute(query, values)
            
            conn.commit()
            messages["success"].append(f"Employee {employee_id} saved successfully")
            print(f"Employee {employee_id} saved successfully")
            
        except psycopg2.Error as e:
            if conn and not conn.closed:
                conn.rollback()
            self.report_error(e)
            messages["error"].append(f"Database error for employee {employee_id}\n{e}")
            raise
        finally:
            if cur: cur.close()
            if conn: conn.close()
            return messages

    def disconnect(self):
        if hasattr(self, "_shared_conn") and self._shared_conn and not self._shared_conn.closed:
            self._shared_conn.close()
            self._shared_conn = None
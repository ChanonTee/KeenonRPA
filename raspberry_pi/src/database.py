import pymssql
from dotenv import load_dotenv
import os

# Load database configuration from .env file
load_dotenv()

# Database class for handling SQL Server connections and data insertion
class Database:
    def __init__(self):
        # Set database configuration from environment variables
        self.server = os.getenv("DB_SERVER")
        self.database = os.getenv("DB_DATABASE")
        self.username = os.getenv("DB_USERNAME")
        self.password = os.getenv("DB_PASSWORD")
        
        self.conn = None
        self.cursor = None
        
    def is_database_connected(self):
        try:
            # Attempt to connect to the database
            conn = pymssql.connect(
                server=self.server, user=self.username, password=self.password, database=self.database
            )
            cursor = conn.cursor()

            # Test the connection by executing a simple query
            cursor.execute('SELECT @@VERSION')
            version = cursor.fetchone()

            # If no exception occurs and we get a version, the connection is successful
            print(f"Connected to SQL Server, version: {version[0]}")
            cursor.close()
            conn.close()
            return True
        except pymssql.Error as e:
            print(f"Database connection error: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False


    def __connect(self):
        # Establish connection to the SQL Server
        try:
            self.conn = pymssql.connect(
                server=self.server, user=self.username, password=self.password, database=self.database
            )
            self.cursor = self.conn.cursor()
        except pymssql.Error as e:
            print(f"Database connection error: {e}")
            
    def __close(self):
        # Close database connection
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            
    def __save_to_database(self, data, query):
        # Insert measurement data into the DustMeasurements table
        try:
            self.__connect()

            # Check if data is a list of tuples or a single tuple
            if isinstance(data, list):
                if all(isinstance(row, tuple) for row in data):  # Multiple rows (list of tuples)
                    self.cursor.executemany(query, data)
                else:
                    print("Each item in data list must be a tuple.")
                    return
            elif isinstance(data, tuple):  # Single row (single tuple)
                self.cursor.execute(query, data)
            else:
                print("Data format is not correct.")
                return

            self.conn.commit()
            print("Data inserted successfully!")
        except pymssql.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            self.__close()
            

    def save_measurement(self, data):
        # Insert measurement data into the DustMeasurements table
        query = """
            INSERT INTO DustMeasurements 
            (measurement_datetime, room, area, location_name, count, um01, um02, um03, um05, um07, um10, running_state, alarm_high) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        self.__save_to_database(data, query)
    
    def save_activity_log(self, data):
        # Insert activity log data into the ActivityLogs table
        query = """
            INSERT INTO ActivityLogs 
            (log_timestamp, location_name, activity) 
            VALUES (%s, %s, %s)
            """
        self.__save_to_database(data, query)

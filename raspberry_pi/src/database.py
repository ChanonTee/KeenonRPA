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

    def save_measurement(self, data):
        # Insert measurement data into the DustMeasurements table
        try:
            self.__connect()

            query = """
                INSERT INTO DustMeasurements 
                (measurement_datetime, room, area, location_name, count, um01, um03, um05, running_state, alarm_high) 
                VALUES (%s, %s, %s, %s, %d, %d, %d, %d, %d, %d)
                """

            for record in data:
                self.cursor.execute(query, record)

            self.conn.commit()
            print("Data inserted successfully!")
        except pymssql.Error as e:
            print(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            self.__close()

   
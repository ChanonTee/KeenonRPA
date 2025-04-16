from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException

from dotenv import load_dotenv
import os

import time
import datetime

# Load sensor configuration from .env file
load_dotenv()

# Sensor class to manage the communication with the SOLAIR 1100LD device over Modbus TCP
class Sensor:
    def __init__(self):
        # Initialize Modbus client with SOLAIR IP from .env file
        self.client = ModbusTcpClient(os.getenv("SOLAIR_IP"))
        self.measurement_time = int(os.getenv("MEASUREMENT_TIME", 70))  # Default 70 seconds
        self.slave = int(os.getenv("SLAVE"))

        self.is_measuring = False

    def is_sensor_connected(self):
        """
        Method to check if we can connect to SOLAIR 1100LD
        """
        print("Checking connection to SOLAIR 1100LD...")
        try:
            if self.client.connect():
                print("Connected to SOLAIR 1100LD.")
                self.client.close()  # Close the connection after checking
                return True
            else:
                print("Failed to connect to SOLAIR 1100LD.")
                return False
        except ModbusIOException as e:
            print(f"Modbus IO Error during connection: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during connection: {e}")
            return False

    def start_measurement(self):
        """
        Method to start measurement on SOLAIR 1100LD
        """
        try:
            if not self.client.is_socket_open():  # Check if socket is open
                self.client.connect()  # Only connect if not already connected

            self.client.write_register(1, 11,slave = self.slave)  # Start measurement command
            self.is_measuring = True
            print("Measurement started.")
            time.sleep(self.measurement_time)  # Wait for the measurement to complete
            self.client.write_register(1, 12,slave = self.slave)  # Stop measurement command
            self.is_measuring = False
            print("Measurement stopped.")
            self.client.close()

        except ModbusIOException as e:
            print(f"Modbus IO Error during measurement: {e}")
        except Exception as e:
            print(f"Measurement error: {e}")

    def stop_measurement(self):
        """
        Method to stop measurement on SOLAIR 1100LD
        """
        try:
            if not self.client.is_socket_open():  # Check if socket is open
                self.client.connect()  # Only connect if not already connected

            self.client.write_register(1, 12,slave = self.slave)  # Stop measurement command
            print("Measurement stopped.")
            self.client.close()

        except ModbusIOException as e:
            print(f"Modbus IO Error during stop measurement: {e}")
        except Exception as e:
            print(f"Stop measurement error: {e}")

    def read_data(self):
        """
        Method to read measurement data from SOLAIR 1100LD
        """
        try:
            if not self.client.is_socket_open():  # Check if socket is open
                self.client.connect()  # Only connect if not already connected

            # Read the record count from the register (address 40024)
            record_count = self.client.read_holding_registers(address=40024 - 40001, count=1, slave = self.slave)
            self.client.write_register(40025 - 40001, record_count.registers[0] - 1, slave = self.slave)

            # Read the actual measurement data from the register (address 30001)
            register_address = 30001 - 30001
            response = self.client.read_input_registers(register_address, count=100, slave = self.slave)

            # Check if there is an error in reading data
            if response.isError():
                print("Error reading record.")
                return None
                        
            data = {
                'measurement_datetime': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'room': 'CR11',
                'area': '1K',
                'location_name': None,
                'count': None,
                'um01': response.registers[9],
                'um02': response.registers[11],
                'um03': response.registers[17],
                'um05': response.registers[19],
                'um07': response.registers[21],
                'um10': response.registers[23],
                'running_state': 1,
                'alarm_high': None,
            }
            #print(data)
            self.client.close()
            return data 

        except ModbusIOException as e:
            print(f"Modbus IO Error during reading data: {e}")
            return None
        except Exception as e:
            print(f"Error reading data: {e}")
            return None
        


from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time
from dotenv import load_dotenv
import os

# Load sensor configuration from .env file
load_dotenv()

# Sensor class to manage the communication with the SOLAIR 1100LD device over Modbus TCP
class Sensor:
    def __init__(self):
        # Initialize Modbus client with SOLAIR IP from .env file
        self.client = ModbusTcpClient(os.getenv("SOLAIR_IP"))
        self.measurement_time = os.getenv("MEASUREMENT_TIME", 70)  # Default 70 seconds
        self.is_measuring = False

    def check_connection(self):
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

            self.client.write_register(1, 11)  # Start measurement command
            self.is_measuring = True
            print("Measurement started.")
            time.sleep(self.measurement_time)  # Wait for the measurement to complete
            self.client.write_register(1, 12)  # Stop measurement command
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

            self.client.write_register(1, 12)  # Stop measurement command
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
            record_count = self.client.read_holding_registers(address=40024 - 40001, count=1)
            self.client.write_register(40025 - 40001, record_count.registers[0] - 1)

            # Read the actual measurement data from the register (address 30001)
            register_address = 30001 - 30001
            response = self.client.read_input_registers(register_address, count=100)

            # Check if there is an error in reading data
            if response.isError():
                print("Error reading record.")
                return None
            
            print(f"Record values: {response.registers[9]}")  # Example of accessing specific data
            print(f"Record values: {response.registers}")
            data = {}
            
            # data = {
            #     'measurement_datetime': measurement_time.isoformat(),
            #     'room': room,
            #     'area': area,
            #     'location_name': location,
            #     'count': count,
            #     'um01': um_values['um01'],
            #     'um03': um_values['um03'],
            #     'um05': um_values['um05'],
            #     'running_state': random.randint(0, 1),
            #     'alarm_high': 0,
            # }

            self.client.close()
            return data 

        except ModbusIOException as e:
            print(f"Modbus IO Error during reading data: {e}")
            return None
        except Exception as e:
            print(f"Error reading data: {e}")
            return None

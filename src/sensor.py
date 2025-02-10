from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time
from src import CONFIG

class Sensor:
    def __init__(self):
        self.client = ModbusTcpClient(CONFIG["SOLAIR_IP"], port=CONFIG["SOLAIR_PORT"])
    
    def check_connection(self):
        print("Checking connection to SOLAIR 1100LD...")
        if self.client.connect():
            print("Connected to SOLAIR 1100LD.")
            self.client.close()
            return True
        print("Failed to connect to SOLAIR 1100LD.")
        return False

    def start_measurement(self):
        try:
            self.client.connect()
            self.client.write_register(1, 11)  # Start command
            print("Measurement started.")
            time.sleep(60)
            self.client.write_register(1, 12)  # Stop command
            print("Measurement stopped.")
            self.client.close()
        except Exception as e:
            print(f"Measurement error: {e}")
    
    def read_data(self):
        try:
            self.client.connect()
            result = self.client.read_holding_registers(0, 10)
            self.client.close()
            if result.isError():
                print("Failed to read data.")
                return None
            return result.registers[0]  # Assume first register holds dust level
        except Exception as e:
            print(f"Error reading data: {e}")
            return None
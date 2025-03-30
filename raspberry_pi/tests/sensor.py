from src import Sensor

def test_sensor():
    sensor = Sensor()

    # Start measurement
    sensor.start_measurement()
    
    # Read data
    data = sensor.read_data()
    if data:
        print(f"Measurement data: {data}")
    print("Done")
    
if __name__ == "__main__":
   test_sensor()
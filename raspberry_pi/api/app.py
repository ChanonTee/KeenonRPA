from src import Robot, Sensor, Database, DustLogger
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
import threading
import time
import os


# Load configuration from .env file
load_dotenv()

"""
Start API server with this command:
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

app = FastAPI()

# Initialize robot, sensor, and database objects
robot = Robot()
sensor = Sensor()
db = Database()
Logging = DustLogger()

# Start the robot server
robot.start_server_in_background()

# List to store destination points
points = []
dust_data_buffer = []
ucl_limit = int(os.getenv("UCL_LIMIT"))
max_retries = int(os.getenv("MAX_RETRIES", 3))
max_wait = int(os.getenv("MAX_WAIT", 120))

# Thread
stop_event = threading.Event()
lock = threading.Lock()
robot_thread = None  # Store the robot's thread

@app.get("/check-robot-connection")
async def check_robot_connection():
    """
    Check if the robot is connected.
    """
    if robot.is_client_connected():
        return JSONResponse(
                content={"message": "True"},
                status_code=200 
            )
    return JSONResponse(
                content={"message": "False"},
                status_code=200 
            )


class PointRequest(BaseModel):
    point: str  # Define a request model for receiving destination points

@app.post("/add-point")
async def add_point(data: PointRequest):
    """
    Add a single destination point to the robot's queue.

    This endpoint allows a user to add one destination point to the queue. 
    The robot will later visit these points and perform measurements.

    **Request body**:
    - **points**: A list of destination points to be added. Example: 
    {
        "point": 6002-IS-1K017-default
    }
    **Response**:
    - A message indicating the point that were added and The current list of destination points.
    """
    point = data.point
    points.append(point)
    print(f"Added {point} to the queue.")
    return JSONResponse(
                content={"message": f"Added {point} to the queue.", "points": points},
                status_code=200 
            )

class ListPointsRequest(BaseModel):
    points: List[str]  # Define a request model for receiving multiple destination points

@app.post("/add-points")
async def add_points(data: ListPointsRequest):
    """
    Add a list of destination points to the robot's queue.

    This endpoint allows a user to add multiple destination points at once. 
    The robot will visit these points and perform measurements.

    **Request body**:
    - **points**: A list of destination points to be added. Example: 
    {
        "points": [
           "6002-IS-1K017-default",
           "6002-IS-1K018-default",
           "6002-IS-1K019-default"
        ]
    }

    **Response**:
    - A message indicating the points that were added and The current list of destination points.
    """
    points.extend(data.points) 
    print(f"Added {data.points} to the queue.")
    return JSONResponse(
                content={"message": f"Added {data.points} to the queue.", "points": points},
                status_code=200 
            )

@app.get("/get-points")
async def get_points():
    """
    Get the remaining destination points in the queue.

    This endpoint allows the user to see the points left in the queue for the robot to visit.

    **Response**: The current list of destination points.
    """
    print(f"Get points {points}")
    return JSONResponse(
                content={"points": points if points else None},
                status_code=200 
            )

@app.get("/del-points")
async def del_points():
    """
    Delete all destination points in the queue.

    This endpoint clears the queue of all stored destination points.

    **Response**: A message indicating the queue has been cleared.
    """
    points.clear()
    print("Delete all points")
    
    return JSONResponse(
                content={"message": "Delete all points"},
                status_code=200 
            )

def go_task():
    """
    Task to move the robot through all points in the queue and perform measurements.

    This function will:
    - Move the robot to each point in the queue.
    - Perform a dust level measurement at each point.
    - Retry the measurement if the dust level exceeds the UCL (User Control Limit).
    """
    global stop_event, points, dust_data_buffer

    if not points:
        print("No points in queue.")
        return

    robot.send_command("goHome")
    time.sleep(1)
    robot.send_command("Peanut Food Delivery")
    time.sleep(3)


    while points:
        if stop_event.is_set():
            print("Interrupted: Stopping robot process...")
            return

        point = points.pop(0)  # Run in queue FIFO
        robot.send_command("clickBackButton")
        robot.send_command("Direct")
        
        if not robot.search_ui_and_click(point):
            print(f"No point found skip {point}")
            continue
        
        if stop_event.is_set():
            print("Interrupted: Stopping robot process...")
            return
        
        robot.send_command("Go")
        time.sleep(1)

        now_sec = 0
        while not robot.is_have_ui("Go"):
            
            if stop_event.is_set():
                print("Interrupted: Stopping robot process")
                return
            
            time.sleep(1)
            now_sec += 1
            print(f"Waiting {now_sec}/{max_wait}")
            
            if now_sec >= max_wait:
                print("Timeout")
                break
            
        print(f"Robot at point: {point}")

        count = 1
        um01 = None
        while count < max_retries + 1:
            print(f"Start measurement at point: {point} count: {count}/{max_retries}...")
            dust_data = {}

            sensor.start_measurement()
            dust_data = sensor.read_data()

            #  data = {
            #     'measurement_datetime': datetime.date.today(),
            #     'room': 'CR11',
            #     'area': '1K',
            #     #'location_name': 'location', 
            #     #'count': count,# Add in loop
            #     'um01': response.registers[9],
            #     'um03': response.registers[17],
            #     'um05': response.registers[19],
            #     'running_state': 1,
            #     #'alarm_high': 0,
            # }

            dust_data['location_name'] = point
            dust_data['count'] = count
            um03 = dust_data['um03']

            if um03 > ucl_limit:
                dust_data['alarm_high'] = 1
            else:
                dust_data['alarm_high'] = 0

            print(dust_data)

            try:
                list_buffer = []
                list_buffer.append(tuple(dust_data.values()))
                db.save_measurement(list_buffer)

                Logging.save_log(dust_data)
                print(f"Saved measurement at {dust_data['location_name']}, count: {dust_data['count']}")
            except Exception as e:
                print(f"Database error: {e}. Storing offline.")
                dust_data_buffer.append(list_buffer)


            if um03 > ucl_limit:
                print(f"Dust level at {dust_data['location_name']} exceeded UCL ({um01}). Retrying ...")
            else:
                break

            count += 1
            time.sleep(2)

        print(f"Finished point: {point}")

    if dust_data_buffer:
        print("Retrying to save measurements...")
        for dust_data in dust_data_buffer:
            try:
                db.save_measurement(dust_data)
                print(f"Recovered and saved {dust_data['location_name']}, count: {dust_data['count']}")
                dust_data_buffer.remove(dust_data)
            except Exception as e:
                print(f"Still unable to save {point}: {e}")

    print("All measurements completed.")

@app.get("/go")
async def go():
    """
    Start the robot process to go through all points in the queue.

    This endpoint starts the robot's task of going to all destination points in the queue 
    and performing measurements at each point.

    **Response**: A message indicating the robot process has started.
    """
    global robot_thread, stop_event
    
    # If the robot is already working
    with lock: 
        if robot_thread is not None and robot_thread.is_alive():
            return JSONResponse(
                content={"message": "Robot process is already running."},
                status_code=400 # Return a 400 Bad Request if already running
            )
            
    if not points:
        print("No points in queue.")
        return JSONResponse(
                content={"message": "No points in queue."},
                status_code=400 
            )

    stop_event.clear()
    robot_thread = threading.Thread(target=go_task, daemon=True)
    robot_thread.start()

    return JSONResponse(
                content={"message": "Robot process started."},
                status_code=200 
            )


@app.get("/stop")
async def stop():
    """
    Stop the robot process.

    This endpoint stops the robot from continuing its tasks. The task will stop at the current point.
    If the robot process hasn't started, it will return a message indicating no active process.
    
    **Response**: A message indicating the robot process is being stopped or that no process is running.
    """
    global robot_thread, stop_event

    # Stop the sensor measurement if it's running
    if sensor.is_measuring:
        sensor.stop_measurement()
        print("Sensor measurement stopped.")

    # Check if the robot process has already started
    with lock: 
        if robot_thread is None or not robot_thread.is_alive():
            return JSONResponse(
                content={"message": "No active robot process to stop."},
                status_code=400 # Return a 400 Bad Request if not running
            )

    # If the robot process is running, stop it
    stop_event.set()
    return JSONResponse(
                content={"message": "Stopping robot process..."},
                status_code=200 
            )

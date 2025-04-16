import random
from src import Robot, Database, DustLogger

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

import os
from dotenv import load_dotenv

import threading
import time

import datetime

# Load configuration from .env file
load_dotenv()

"""
Start API server with this command:
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize robot, sensor, and database objects
robot = Robot()
# sensor = Sensor()
db = Database()
logger = DustLogger()



# Start the robot server
robot.start_server_in_background()

# List to store destination points
points = []
dust_data_buffer = []
activity_buffer = []
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
    returns True if the robot is connected, otherwise False.
    """
    with lock:
        if robot.is_client_connected():
            return JSONResponse(
                    content={"message": "True"},
                    status_code=200 
                )
    return JSONResponse(
                content={"message": "False"},
                status_code=200 
            )

# @app.get("/check-sensor-connection")
# async def check_sensor_connection():
#     """
#     Check if the sensor is connected.
#     returns True if the sensor is connected and measuring, otherwise False.
#     """
#     if sensor.is_measuring or sensor.is_sensor_connected():
#         return JSONResponse(
#                     content={"message": "True"},
#                     status_code=200 
#                 )
        
#     return JSONResponse(
#                 content={"message": "False"},
#                 status_code=200 
#             )
    
@app.get("/check-database-connection")
async def check_database_connection():
    """
    Check if the database is connected.
    returns True if the database is connected, otherwise False.
    """
    if db.is_connected():
        return JSONResponse(
                    content={"message": "True"},
                    status_code=200 
                )
        
    return JSONResponse(
                content={"message": "False"},
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

@app.delete("/del-points")
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
    
  
"""
    Dust measurement mode
"""

def start_dust_task(required_send_database):
    """
    Task to move the robot through all points in the queue and perform measurements.
    """
    global stop_event, points, dust_data_buffer, activity_buffer

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
        db.save_log([(datetime.datetime.now(), point, "Going to point["+point+"]")])
        time.sleep(1)
        print(f"Robot is going to {point}...")
        
        activity = (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), point, f"Going to [{point}]")
        try:
            db.save_activity_log(activity)
            print(f"Saved activity log at {point}")
        except Exception as e:
            activity_buffer.append(activity)
            print(f"Database error: {e}. Storing offline.")

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
        db.save_log([(datetime.datetime.now(), point, "Arrived at point")])
        time.sleep(2)

        # Dust measurement
        count = 1
        while count < max_retries + 1:
            print(f"Start measurement at point: {point} count: {count}/{max_retries}...")
            db.save_log([(datetime.datetime.now(), point, "Start measurement")])
            time.sleep(5)
            dust_data = {
                'um01': int(random.uniform(0, ucl_limit * 1.5)),
                'um02': int(random.uniform(0, ucl_limit * 1.5)),
                'um03': int(random.uniform(0, ucl_limit * 1.5)),
                'um05': int(random.uniform(0, ucl_limit * 1.5)),
                'um10': int(random.uniform(0, ucl_limit * 1.5)),
                'um50': int(random.uniform(0, ucl_limit * 1.5)),
            }

            dust_data['location_name'] = point
            dust_data['count'] = count
            um03 = dust_data['um03']

            # เช็คว่าเกิน UCL หรือไม่
            if um03 > ucl_limit:
                dust_data['alarm_high'] = 1
            else:
                dust_data['alarm_high'] = 0

            print(dust_data)

            record = (
                    datetime.datetime.now(),
                    'CR11',
                    '1K',
                    dust_data['location_name'],
                    dust_data['count'],
                    dust_data['um01'],
                    dust_data['um02'],
                    dust_data['um03'],
                    dust_data['um05'],
                    dust_data['um10'],
                    dust_data['um50'],
                    1,
                    dust_data['alarm_high'],
                )
            list_buffer = [record]

            # บันทึกลง database ถ้าเปิดใช้งาน
            if required_send_database:
                try:
                    tuple_dust_data = tuple(dust_data.values())
                    print(f"Saving measurement: {list_buffer}")
                    db.save_measurement(list_buffer)
                    print(f"Saved measurement at {dust_data['location_name']}, count: {dust_data['count']}")
                    logger.save_measurement_log(dust_data)
                except Exception as e:
                    print(f"Database error: {e}. Storing offline.")
                    dust_data_buffer.append(tuple_dust_data)

            if um03 > ucl_limit:
                print(f"Dust level at {dust_data['location_name']} exceeded UCL ({um03}). Retrying ...")
                db.save_log([(datetime.datetime.now(), point, "Result fail, retry...")])
            else:
                db.save_log([(datetime.datetime.now(), point, "Result Pass")])
                break

            count += 1
            time.sleep(2)

        print(f"Finished point: {point}")
        db.save_log([(datetime.datetime.now(), point, "Finished measurement")])

    if dust_data_buffer:
        print("Retrying to save measurements...")
        try:
            db.save_measurement(dust_data)
            print(f"Recovered and saved {dust_data['location_name']}, count: {dust_data['count']}")
            dust_data_buffer.clear()
        except Exception as e:
            print(f"Still unable to save {point}: {e}")

    print("All measurements completed.")

class OperationRequest(BaseModel):
    required_send_database: bool

@app.post("/start-dust")
async def start_dust(request: OperationRequest):
    """
    Start the robot process to go through all points in the queue.

    This endpoint starts the robot's task of going to all destination points in the queue 
    and performing measurements at each point.

    **Request Body**:
    - required_send_database (bool): Whether to send measurement data to the database.

    **Response**: A message indicating the robot process has started.
    """
    global robot_thread, stop_event

    with lock:
        if robot_thread is not None and robot_thread.is_alive():
            return JSONResponse(
                content={"message": "Robot process is already running."},
                status_code=400
            )

    if not points:
        return JSONResponse(
            content={"message": "No points in queue."},
            status_code=400
        )

    stop_event.clear()

    robot_thread = threading.Thread(
        target=start_dust_task,
        args=(request.required_send_database,),  
        daemon=True
    )
    robot_thread.start()

    return JSONResponse(
        content={"message": "Robot process started."},
        status_code=200
    )


@app.get("/stop-dust")
async def stop_dust():
    """
    Stop the robot process.

    This endpoint stops the robot from continuing its tasks. The task will stop at the current point.
    If the robot process hasn't started, it will return a message indicating no active process.
    
    **Response**: A message indicating the robot process is being stopped or that no process is running.
    """
    global robot_thread, stop_event

    # Stop the sensor measurement if it's running
    # if sensor.is_measuring:
    #     sensor.stop_measurement()
    #     print("Sensor measurement stopped.")

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

"""
    Transportation mode
"""

def start_transportation_task():
    """
        Task to move the robot through all points in the queue.
        This function will:
        
    """
    
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


@app.post("/start-transportation")
async def start_transportation():
    """
    Start the robot process to go through all points in the queue.
 
    **Response**: A message indicating the robot process has started.
    """
    global robot_thread, stop_event

    with lock:
        if robot_thread is not None and robot_thread.is_alive():
            return JSONResponse(
                content={"message": "Robot process is already running."},
                status_code=400
            )

    if not points:
        return JSONResponse(
            content={"message": "No points in queue."},
            status_code=400
        )

    stop_event.clear()

    robot_thread = threading.Thread(
        target=start_transportation_task,
        daemon=True
    )
    robot_thread.start()

    return JSONResponse(
        content={"message": "Robot process started."},
        status_code=200
    )
    
@app.get("/stop-transportation")
async def stop_transportation():
    """
    Stop the robot process.

    This endpoint stops the robot from continuing its tasks. The task will stop at the current point.
    If the robot process hasn't started, it will return a message indicating no active process.
    
    **Response**: A message indicating the robot process is being stopped or that no process is running.
    """
    global robot_thread, stop_event

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
    
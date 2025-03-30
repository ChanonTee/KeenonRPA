import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from src import Robot, Sensor, Database, CONFIG
import threading
from typing import List

"""
Start API server with this command:
python -m uvicorn api.app-async:app --host 0.0.0.0 --port 8000
python -m uvicorn api.app-async:app --host 0.0.0.0 --port 8000 --log-level debug --reload
"""

app = FastAPI()

# Initialize robot, sensor, and database objects
robot = Robot()
sensor = Sensor()
db = Database()

robot.start_server()

# List to store destination points
points = []
data_buffer = []
ucl_limit = CONFIG['UCL_LIMIT']
max_retries = CONFIG['MAX_RETRIES'] 

# Events for stopping and preventing duplicate tasks
stop_event = threading.Event()
go_task_running = threading.Event()  # Track if go_task is already running

class PointRequest(BaseModel):
    point: str  

@app.post("/send-point")
async def send_point(data: PointRequest):
    points.append(data.point)
    print(f"Added {data.point} to the queue.")
    return {"message": points}

class ListPointsRequest(BaseModel):
    points: List[str]

@app.post("/send-points")
async def send_points(data: ListPointsRequest):
    points.extend(data.points)
    print(f"Added {data.points} to the queue.")
    return {"message": points}

@app.get("/get-points")
async def get_points():
    return {"points": points if points else None}

@app.get("/del-points")
async def del_points():
    points.clear()
    print("Delete all points")
    return {"message": "Delete all points"}

def check_stop():
    """Check if stop_event is set. If true, clear go_task_running and return True."""
    if stop_event.is_set():
        print("Interrupted: Stopping robot process")
        go_task_running.clear()
        return True
    return False

async def go_task():
    """Task for walking (Run in Background with asyncio)"""
    global points, data_buffer

    if not points:
        print("No points to go.")
        go_task_running.clear()  # Mark task as finished
        return

    stop_event.clear()
    go_task_running.set()

    await asyncio.to_thread(robot.send_command, "goHome")
    if check_stop(): return  

    await asyncio.to_thread(robot.send_command, "Peanut")
    if check_stop(): return  

    while points:
        if check_stop(): return  

        point = points.pop(0)
        await asyncio.to_thread(robot.send_command, "clickBackButton")
        if check_stop(): return  

        await asyncio.to_thread(robot.send_command, "Direct")
        if check_stop(): return  

        if not await asyncio.to_thread(robot.search_ui_and_click, point):
            continue

        await asyncio.to_thread(robot.send_command, "Go")
        if check_stop(): return  

        await asyncio.sleep(1)

        sec = 0
        max_wait = 120
        while not await asyncio.to_thread(robot.is_have_ui, "Go"):
            if check_stop(): return
            await asyncio.sleep(1)
            sec += 1
            if sec >= max_wait:
                print("Timeout")
                break
        print(f"Robot at point: {point}")

        count = 1
        dust_level = None
        while count < max_retries + 1:
            if check_stop(): return  
            print(f"Start measurement at point: {point} count: {count}/{max_retries}...")

            sensor.start_measurement()
            dust_level = sensor.read_data()

            if dust_level is None:
                print(f"Measurement failed at {point}. Retrying...")
            elif dust_level <= ucl_limit:
                print(f"Dust level at {point} is within range: {dust_level}")
                break  
            else:
                print(f"Dust level at {point} exceeded UCL ({dust_level}). Retrying {count}/{max_retries}...")

            try:
                db.save_measurement(point, dust_level, count)
                print(f"Saved measurement at {point}: {dust_level}: {count}")
            except Exception as e:
                print(f"Database error: {e}. Storing offline.")
                data_buffer.append((point, dust_level, count))

            count += 1
            await asyncio.sleep(2)

        print(f"Finished point: {point}")

    if data_buffer:
        print("Retrying to save measurements...")
        for point, dust_level in data_buffer:
            try:
                db.save_measurement(point, dust_level, count)
                print(f"Recovered and saved {point}: {dust_level}: {count}")
                data_buffer.remove((point, dust_level, count))
            except Exception as e:
                print(f"Still unable to save {point}: {e}")

    print("All measurements completed.")
    go_task_running.clear()  # Mark task as finished


@app.get("/go")
async def go():
    """Start robot process asynchronously."""
    global stop_event, go_task_running

    if go_task_running.is_set():  # Check if task is already running
        return {"message": "Robot process is already running."}

    stop_event.clear()  # Reset stop flag before starting
    go_task_running.set()  # Mark task as running

    asyncio.create_task(go_task())  # Start the task asynchronously

    return {"message": "Robot process started asynchronously."}

@app.get("/stop")
async def stop():
    """Stop the robot process."""
    global stop_event

    stop_event.set()  # Signal to stop

    return {"message": "Stopping robot process..."}

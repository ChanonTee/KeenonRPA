from fastapi import FastAPI
from pydantic import BaseModel
from src import Robot, Sensor, Database
import threading
import time

"""
Start API server with this command:
python -m uvicorn api.app:app --host 0.0.0.0 --port 8000
"""

app = FastAPI()

# Initialize robot, sensor, and database objects
robot = Robot()
sensor = Sensor()
db = Database()

# Start the robot server
robot.start_server()

# List to store destination points
points = []
stop_event = threading.Event()
robot_thread = None  # Store the robot's thread

class PointRequest(BaseModel):
    point: str  # Define a request model for receiving destination points

@app.post("/send-point")
async def send_point(data: PointRequest):
    """Add a destination point to the queue."""
    point = data.point
    points.append(point)
    print(f"Added {point} to the queue.")
    return {"message": points}

@app.get("/get-points")
async def get_points():
    """Return the remaining destination points."""
    print(f"Get points {points}")
    return {"points": points if points else None}

@app.get("/del-points")
async def del_points():
    """Delete all destination points."""
    points.clear()
    print("Delete all points")
    return {"message": "Delete all points"}

def go_task():
    """Task for walking (Run in Thread)"""
    global stop_event, points

    if not points:
        print("No points to go.")
        return

    robot.send_command("goHome")
    robot.send_command("Peanut")

    while points:
        if stop_event.is_set():
            print("Interrupted: Stopping robot process...")
            return

        point = points.pop(0)  # ลบ point ที่ไปแล้ว
        robot.send_command("clickBackButton")
        robot.send_command("Direct")
        robot.search_ui_and_click(point)
        robot.send_command("Go")
        time.sleep(1)

        sec = 0
        max_wait = 120
        while not robot.is_have_ui("Go"):
            if stop_event.is_set():
                print("Interrupted: Stopping robot process")
                return
            time.sleep(1)
            sec += 1
            print(f"Waiting {sec}/{max_wait}")
            if sec >= max_wait:
                print("Timeout")
                break

        print(f"Finished point: {point}")

@app.get("/go")
async def go():
    """Go to point in list and """
    global robot_thread, stop_event
    stop_event.clear()

    if robot_thread is None or not robot_thread.is_alive():
        robot_thread = threading.Thread(target=go_task, daemon=True)
        robot_thread.start()

    return {"message": "Robot process started."}

@app.get("/stop")
async def stop():
    """หยุดการทำงานของหุ่นยนต์"""
    stop_event.set()
    return {"message": "Stopping robot process..."}

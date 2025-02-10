from src import Robot
import threading

def test_robot():
    robot = Robot()
    
    server_thread = threading.Thread(target=robot.start_server, daemon=True)
    server_thread.start()
    
    robot.wait_for_rpa_connection()
    
    robot.move_to_point("A001")
    robot.move_to_point("A002")


if __name__ == "__main__":
    test_robot()
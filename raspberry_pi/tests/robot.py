from src import Robot
import time

def test_robot():
    robot = Robot()
    
    robot.start_server()
    time.sleep(1)
    robot.send_command("goHome")
    time.sleep(1)
    robot.send_command("Clock")
    time.sleep(1)
    robot.send_command("clickBackButton")
    time.sleep(1)
    robot.send_command("goHome")
    time.sleep(1)
    robot.send_command("Settings")
    time.sleep(1)
    # response = robot.send_command("getFullUI")
    # time.sleep(1)
    # print(robot.is_have_ui("Display"))
    # time.sleep(1)
    # print(robot.is_have_ui("Security"))
    time.sleep(1)
    print(robot.search_ui("plaweq"))
    time.sleep(1)
    
if __name__ == "__main__":
    test_robot()
    
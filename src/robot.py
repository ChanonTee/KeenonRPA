import socket
import time
import threading
from src import CONFIG

class Robot:
    def __init__(self):
        self.server_ip = CONFIG["RPA_IP"]
        self.server_port = CONFIG["RPA_PORT"]
        self.server_thread = None
        self.server_socket = None

    def start_server(self):
        """ เริ่มต้น Socket Server เพื่อรับคำสั่งจาก Android """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.server_port))
        self.server_socket.listen(5)
        print("Server started, waiting for connection...")

        while True:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Connected to Android device at {addr}")
                # ใช้ threading เพื่อรองรับหลาย connection
                #threading.Thread(target=self._handle_client, args=(client_socket,), daemon=True).start()
                self._handle_client(client_socket)
            except Exception as e:
                print(f"Error in connection: {e}")

    def _handle_client(self, client_socket):
        """ จัดการ Connection จาก Client """
        try:
            initial_command = client_socket.recv(1024).decode('utf-8').strip()
            if initial_command != "start connection rpa":
                print("Invalid initial command from client. Closing connection.")
                return

            client_socket.sendall("Handshake accepted\n".encode())
            print("RPA connection established. Waiting for commands...")

            while True:
                command = client_socket.recv(1024).decode('utf-8').strip()
                if not command:
                    break
                if command.lower() == 'done':
                    print("Exiting session.")
                    break
                print(f"Executing command: {command}")
                client_socket.sendall(f"Command received: {command}\n".encode())

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            print("Closing client socket.")
            client_socket.close()

    def start_rpa_server_in_thread(self):
        """ รัน RPA Server ใน Thread แยกเพื่อไม่ให้บล็อคโปรแกรมหลัก """
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    def wait_for_rpa_connection(self, timeout=30):
        """ รอให้ RPA Server พร้อมใช้งาน โดยมี timeout """
        print("Waiting for RPA connection...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.send_command_to_rpa("ping"):
                print("RPA connection established.")
                return True
            time.sleep(2)

        print("Timeout: RPA server is not responding.")
        return False

    def send_command_to_rpa(self, command):
        """ ส่งคำสั่งไปยัง RPA server พร้อม handshake """
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5)  # ป้องกันการค้าง
            client.connect((self.server_ip, self.server_port))
            client.sendall("start connection rpa\n".encode())

            handshake_resp = client.recv(1024).decode('utf-8')
            if "Handshake accepted" not in handshake_resp:
                print("Handshake failed.")
                client.close()
                return None

            client.sendall(f"{command}\n".encode())
            response = client.recv(4096).decode('utf-8')
            print(f"Send command: {command}, Response: {response}")

            client.close()
            return response
        except socket.timeout:
            print("Timeout error: Unable to reach RPA server.")
            return None
        except Exception as e:
            print(f"Error sending command to RPA: {e}")
            return None

    def move_to_point(self, point):
        """ สั่งให้ RPA เคลื่อนที่ไปยังตำแหน่งที่กำหนด """
        print(f"Moving to measurement spot {point}...")
        commands = ["goHome", "Peanut", "clickBackButton", "measuringSpot", point]
        for command in commands:
            self.send_command_to_rpa(command)
            time.sleep(1) # wait for click
        time.sleep(3) # wait for robot moving

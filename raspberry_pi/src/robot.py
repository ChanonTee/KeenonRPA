import socket
import time
import re
from src import CONFIG

class Robot:
    def __init__(self):
        self.server_ip = CONFIG["RPA_IP"]
        self.server_port = CONFIG["RPA_PORT"]
        self.server_socket = None
        self.client_socket = None

    def start_server(self):
        """ เริ่มต้น Socket Server เพื่อรับคำสั่งจาก Android """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.server_port))
        self.server_socket.listen(1)
        print("Server started, waiting for connection...")

        while (self.client_socket == None):
            try :
                self.client_socket, addr = self.server_socket.accept()
                print(f"Connected to Android device at {addr}")
                print("client:", self.client_socket)
                
            except Exception as e:
                print(f"Error in connection: {e}")

    def receive_large_response(self):
        self.client_socket.settimeout(10)  # Set timeout to avoid infinite hanging
        full_response = []
        try:
            while True:
                chunk = self.client_socket.recv(4096).decode('utf-8')
                if not chunk:
                    print("Connection closed by client.")
                    break
                if chunk.strip() == "[END]":  # Signal that all chunks are received
                    break
                full_response.append(chunk)
        except socket.timeout:
            print("Socket timeout reached. No data received.")
        return ''.join(full_response)
    
    def send_command(self, command):
        
        try:
            print(f"Sending command: {command}")
            self.client_socket.sendall((command + '\n').encode())

            if command == "getFullUI":  # Handle large responses
                print("Waiting for full response...")
                response = self.receive_large_response()
                print("Full Response Received:\n")
                time.sleep(1)
                return response

            else:  # Handle regular commands
                response = self.client_socket.recv(4096).decode('utf-8')
                if not response:
                    print("No response received.")
                print("Response:", response)
                time.sleep(1)
                return response
            
        except Exception as e:
            print(f"Error handling client: {e}")
          
    # Check ui in screen
    def is_have_ui(self, ui: str) -> bool:
        full_ui = None
        full_ui = self.send_command("getFullUI")
        time.sleep(1)
        if full_ui is None:
            return False
        pattern = rf'Text: {re.escape(ui)},' 
        return re.search(pattern, full_ui) is not None
    
    # Try to search ui in screen with scroll
    def search_ui(self, ui: str) -> bool:
        
        found_ui = False
        
        if self.is_have_ui(ui):
            found_ui = True
        
        # Try scrolling down
        response = ''
        scroll_count = 0
        while scroll_count <= 10:
            response = str(self.send_command("scrollDown"))
            if "No scrollable" in response:
                break  
            
            if self.is_have_ui(ui):
                found_ui = True
                break
            scroll_count += 1

        # Reset scrolling up to top 
        response = ''
        scroll_count = 0
        while scroll_count <= 10:
            response = str(self.send_command("scrollUp"))
            if "No scrollable" in response:
                break 

            if self.is_have_ui(ui):
                found_ui = True
            scroll_count += 1
        
        return found_ui  
    
    def search_ui_and_click(self, ui: str) -> bool:
        
        if self.is_have_ui(ui):
            self.send_command(ui)
            return True
        
        # Try scrolling down
        response = ''
        scroll_count = 0
        while scroll_count <= 10:
            response = str(self.send_command("scrollDown"))
            if "No scrollable" in response:
                break  
            
            if self.is_have_ui(ui):
                self.send_command(ui)
                return True
            scroll_count += 1
        
        # Reset scrolling up to top 
        response = ''
        scroll_count = 0
        while scroll_count <= 10:
            response = str(self.send_command("scrollUp"))
            if "No scrollable" in response:
                break 

            if self.is_have_ui(ui):
                self.send_command(ui)
                return True
            scroll_count += 1

        
        return False  
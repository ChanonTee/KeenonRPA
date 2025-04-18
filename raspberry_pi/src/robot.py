import socket
import time
from dotenv import load_dotenv
import os
import threading
import re

# Load configuration from .env file
load_dotenv()

class Robot:
    def __init__(self):
        """Initialize the robot server with settings from .env file"""
        self.server_bind = os.getenv("RPA_BIND", "0.0.0.0")
        self.server_port = int(os.getenv("RPA_PORT", 12345))
        self.server_socket = None
        self.client_socket = None
        self.lock = threading.Lock()


    def __start_server(self):
        """Start the TCP server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.server_bind, self.server_port))
        self.server_socket.listen(1)
        print(f"Server listening on {self.server_bind}:{self.server_port}")

        self.__heartbeat()
            
    def __heartbeat(self):
        while True:
            # Wait for a client to connect
            if self.client_socket is None:
                print("Waiting for Android device to connect...")
                self.client_socket, addr = self.server_socket.accept()
                print(f"Connected to Android device at {addr}")
            else:
                # Check if the client is still connected
                if not self.is_client_connected():
                    print("Client disconnected, waiting for reconnect...")
                    self.cleanup_client()
                        
            time.sleep(10) # Hearthbeat time
        
            
    def start_server_in_background(self):
        """Start the TCP server in a new thread"""
        thread = threading.Thread(target=self.__start_server, daemon=True)
        thread.start()


    def is_client_connected(self):
        """Check if the client is still connected"""
        try:
            with self.lock:
                self.client_socket.sendall(('ping' + '\n').encode())
                response = self.client_socket.recv(1024).decode('utf-8')
                if response.strip() == "pong":
                    #print("Client is still connected.")
                    return True
                #print("Client is not responding to ping.")
                return False
        except (socket.error, socket.timeout):
            #print("Client is not connected.")
            return False
        except Exception as e:
            #print(f"Unexpected error: {e}")
            return False    
       
        
    def cleanup_client(self):
        """Close and reset client socket"""
        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception:
            pass
        self.client_socket = None

    def receive_large_response(self):
        """Receive a large response from the client in chunks"""
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
        """Send command to the Android device and receive response"""
        try:
            while not self.is_client_connected():
                print("Robot is not connected waiting for reconnect")
                self.cleanup_client()
                time.sleep(12)
                
            if command == "getFullUI":  # Handle large responses
                print(f"Sending command: {command}")
                with self.lock:
                    self.client_socket.sendall((command + '\n').encode())
                    print("Waiting for full response...")
                    response = self.receive_large_response()
                print("Full Response Received:\n")
                time.sleep(2)
                return response

            # Handle regular commands
            print(f"Sending command: {command}")
            with self.lock:
                self.client_socket.sendall((command + '\n').encode())
                response = self.client_socket.recv(1024).decode('utf-8')
            if not response:
                print("No response received.")
            print("Response:", response)
            time.sleep(2)
            return response

        except Exception as e:
            print(f"Error handling client: {e}")
            return None


    def is_have_ui(self, ui: str) -> bool:
        """Check if a specific UI element is present on the screen"""
        full_ui = self.send_command("getFullUI")
        time.sleep(1)
        if full_ui is None:
            return False
        pattern = rf'Text: {re.escape(ui)},'  # Regex pattern to search for UI element
        return re.search(pattern, full_ui) is not None

    def search_ui(self, ui: str) -> bool:
        """Try searching for a UI element by scrolling the screen"""
        found_ui = False

        if self.is_have_ui(ui):
            found_ui = True

        # Try scrolling down
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
        """Search for a UI element and click it if found"""
        if self.is_have_ui(ui):
            self.send_command(ui)
            return True

        # Try scrolling down
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

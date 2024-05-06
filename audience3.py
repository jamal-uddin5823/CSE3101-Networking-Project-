import cv2
import socket
import pickle
import threading
from queue import Queue
 
class Audience:
    server_ip = socket.gethostbyname(socket.gethostname())
    server_port = 6666
 
    def __init__(self,host,port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ip = host
        self.port = port
        self.s.bind((self.ip, self.port))
        print('Connected to audience at', self.ip, self.port)
        self.s.sendto(b'INIT',(Audience.server_ip, Audience.server_port))
        self.frame_queue = Queue()
        self.stop_event = threading.Event()
        self.receive_thread = threading.Thread(target=self.receive_frames)
        self.display_thread = threading.Thread(target=self.display_frames, args=('Audience 3',))
 
    def start(self):
        self.receive_thread.start()
        self.display_thread.start()
 
    def stop(self):
        print('Cleaning up...')
        self.stop_event.set()
        # self.receive_thread.join()
        print('Waiting for display thread to finish...')
        self.display_thread.join()
        print('Destroying windows...')
        cv2.destroyAllWindows()
        self.s.close()
        exit()
 
 
    def receive_frames(self):
        while not self.stop_event.is_set():
            try:
                data, _ = self.s.recvfrom(1000000)
                if data == b'quit':  # Check for 'quit' signal
                    print("Quitting...")
                    self.stop()
 
                data = pickle.loads(data)
                self.frame_queue.put(data)
            except (ConnectionResetError, OSError):
                print("Connection reset or error occurred. Exiting...")
                self.stop()
 
    def display_frames(self, window_name):
        while not self.stop_event.is_set():
            if not self.frame_queue.empty():
                data = self.frame_queue.get()
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                cv2.imshow(window_name, img)
                if cv2.waitKey(25) == ord('q'):
                    self.stop()
            else:
                continue
 
if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = socket.gethostbyname(socket.gethostname())
    port = 6669
 
    audience = Audience(ip,port)
    audience.start()
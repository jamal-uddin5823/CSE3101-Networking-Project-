import cv2
import socket
import pickle
import threading
from queue import Queue
 
class VideoStreamer:
    def __init__(self, server_ip, server_port):
        print("Accessing camera...")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000)
        self.server_ip = server_ip
        self.server_port = server_port
        print('Connected to audience at', server_ip, server_port)
        self.s.bind((server_ip, server_port))
        self.clients = []
        self.stop_event = threading.Event()
        self.frame_queue = Queue()
        self.accept_thread = threading.Thread(target=self.accept_Connection)
        self.video_stream_thread = threading.Thread(target=self.video_stream)
        self.display_thread = threading.Thread(target=self.display_frames)

    
 
    def video_stream(self):
        while not self.stop_event.is_set() and self.cap.isOpened():
            ret, img = self.cap.read()
            if not ret:
                print("Error reading frame")
                continue
            self.frame_queue.put(img)
            ret, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
            x_as_bytes = pickle.dumps(buffer)
            try:
                for client in self.clients:
                    self.s.sendto((x_as_bytes), client)
            except (ConnectionError, OSError) as e:
                print(f'Error: {e}')
                self.stop_event.set()
                break
 
    def display_frames(self):
        cv2.namedWindow('Streamer')
        while not self.stop_event.is_set():
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                cv2.imshow('Streamer', frame)
                if cv2.waitKey(25) == ord('q'):
                    print("Quitting...")
                    for client in streamer.clients:
                        streamer.s.sendto(b'quit', client)
                    streamer.stop()
        #             break
        # cv2.destroyWindow('Streamer')
 
    def accept_Connection(self):
        print("Waiting for connections")
        while not self.stop_event.is_set():
            try:
                data, addr = self.s.recvfrom(1000000)
                if data == b'INIT':
                    print(f'Connection established with {addr}')
                    self.clients.append(addr)
                else:
                    print("Connection rejected")
            except:
                self.stop_event.set()
                break
 
    def start(self):
        self.accept_thread.start()
        self.video_stream_thread.start()
        self.display_thread.start()
 
    def stop(self):
        print('Cleaning up...')
        self.stop_event.set()
        print('Destroying window...')
        cv2.destroyAllWindows()
        print('Closing camera...')
        self.cap.release()
        print('Closing video stream thread...')
        self.video_stream_thread.join()
        print('Closing accept thread...')
        self.accept_thread.join()
        print('Closing display thread...')
        self.display_thread.join()
        exit()
 
if __name__ == "__main__":
    server_ip = socket.gethostbyname(socket.gethostname())
    server_port = 6666
    streamer = VideoStreamer(server_ip, server_port)
    streamer.start()
 
    if cv2.waitKey(25) == ord('q'):
        print("Quitting...")
        for client in streamer.clients:
            streamer.s.sendto(b'quit', client)
        streamer.stop()
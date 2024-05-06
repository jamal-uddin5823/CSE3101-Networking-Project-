import cv2
import socket
import pickle
import threading
from queue import Queue

class VideoStreamer:
    def __init__(self, server_ip, server_port):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000)
        self.server_ip = server_ip
        self.server_port = server_port
        self.clients = [(server_ip, server_port),(server_ip, server_port+1)]
        self.stop_event = threading.Event()
        self.frame_queue = Queue()
        self.video_stream_thread = threading.Thread(target=self.video_stream)
        self.display_thread = threading.Thread(target=self.display_frames)

    def video_stream(self):
        while not self.stop_event.is_set() and self.cap.isOpened():
            ret, img = self.cap.read()
            if not ret:
                print("Error reading frame")
                continue
            print('Reading image')
            self.frame_queue.put(img)
            ret, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
            print('Encoding image')
            x_as_bytes = pickle.dumps(buffer)
            try:
                for client in self.clients:
                    self.s.sendto((x_as_bytes), client)
            except (ConnectionError, OSError) as e:
                print(f'Error: {e}')
                break

    def display_frames(self):
        while not self.stop_event.is_set():
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                cv2.imshow('Streamer', frame)
                if cv2.waitKey(1) == ord('q'):
                    self.stop_event.set()
                    for client in self.clients:
                        self.s.sendto(b'quit', client)
                   

    def start(self):
        self.video_stream_thread.start()
        self.display_thread.start()

    def stop(self):
        self.stop_event.set()
        self.video_stream_thread.join()
        self.display_thread.join()
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    server_ip = socket.gethostbyname(socket.gethostname())
    server_port = 6666

    streamer = VideoStreamer(server_ip, server_port)
    streamer.start()
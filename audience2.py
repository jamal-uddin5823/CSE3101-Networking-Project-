import cv2
import socket
import pickle
import threading
from queue import Queue

def receive_frames(s, frame_queue, stop_event):
    while not stop_event.is_set():
        try:
            data, _ = s.recvfrom(1000000)
            if data == b'quit':  # Check for 'quit' signal
                stop_event.set()
                break
            data = pickle.loads(data)
            frame_queue.put(data)
        except (ConnectionResetError, OSError):
            print("Connection reset or error occurred. Exiting...")
            stop_event.set()
            break

def display_frames(frame_queue, window_name, stop_event):
    while not stop_event.is_set():
        if not frame_queue.empty():
            data = frame_queue.get()
            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
            cv2.imshow(window_name, img)
            cv2.waitKey(1)
        else:
            continue

if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = socket.gethostbyname(socket.gethostname())
    port = 6667
    s.bind((ip, port))

    frame_queue = Queue()
    stop_event = threading.Event()

    receive_thread = threading.Thread(target=receive_frames, args=(s, frame_queue, stop_event))
    receive_thread.start()

    display_thread = threading.Thread(target=display_frames, args=(frame_queue, 'Audience 2', stop_event))
    display_thread.start()

    display_thread.join()
    receive_thread.join()

    cv2.destroyAllWindows()
    s.close()
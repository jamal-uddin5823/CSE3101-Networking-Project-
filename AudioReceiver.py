import cv2
import socket
import pickle
import threading
import pyaudio
from queue import Queue

class Audience:
    server_ip = socket.gethostbyname(socket.gethostname())
    server_video_port = 8000
    server_audio_port = 8001

    def __init__(self, host, video_port, audio_port, window_name='Audience'):
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ip = host
        self.video_port = video_port
        self.audio_port = audio_port
        self.video_socket.bind((self.ip, self.video_port))
        self.audio_socket.bind((self.ip, self.audio_port))
        print(f'Connected to video stream at {self.ip}:{self.video_port}')
        print(f'Connected to audio stream at {self.ip}:{self.audio_port}')
        self.video_socket.sendto(b'INIT_VIDEO', (Audience.server_ip, Audience.server_video_port))
        print('Sent video init message')
        self.audio_socket.sendto(b'INIT_AUDIO', (Audience.server_ip, Audience.server_audio_port))
        self.frame_queue = Queue()
        self.audio_queue = Queue()
        self.stop_event = threading.Event()
        print('Opening threads...')
        self.receive_video_thread = threading.Thread(target=self.receive_frames)
        self.receive_audio_thread = threading.Thread(target=self.receive_audio)
        self.display_thread = threading.Thread(target=self.display_frames, args=(window_name,))
        self.audio = pyaudio.PyAudio()
        self.audio_stream = self.audio.open(format=pyaudio.paInt16,
                                             channels=1,
                                             rate=44100,
                                             frames_per_buffer=1024,
                                             output=True)

    def start(self):
        self.receive_video_thread.start()
        self.receive_audio_thread.start()
        self.display_thread.start()

    def stop_video(self):
        self.video_socket.sendto(b'quit', (Audience.server_ip, Audience.server_video_port))
        print('Cleaning up...')
        self.stop_event.set()
        self.video_socket.close()
        print('Destroying windows...')
        cv2.destroyAllWindows()
        print('Closing sockets and streams...')
        self.video_socket.close()

    def stop_audio(self):
        self.audio_socket.sendto(b'quit', (Audience.server_ip, Audience.server_audio_port))
        self.audio_socket.close()
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.audio.terminate()


    def stop(self):
        self.stop_video()
        self.stop_audio()
        # self.video_socket.sendto(b'quit', (Audience.server_ip, Audience.server_video_port))
        # self.audio_socket.sendto(b'quit', (Audience.server_ip, Audience.server_audio_port))
        # print('Cleaning up...')
        # self.stop_event.set()
        # # self.receive_video_thread.join()
        # # self.receive_audio_thread.join()
        # print('Waiting for display thread to finish...')
        # # self.display_thread.join()
        # print('Destroying windows...')
        # cv2.destroyAllWindows()
        # print('Closing sockets and streams...')
        # self.video_socket.close()
        # self.audio_socket.close()
        # self.audio_stream.stop_stream()
        # self.audio_stream.close()
        # self.audio.terminate()
        exit()

    def receive_frames(self):
        while not self.stop_event.is_set():
            try:
                # print("Receiving video...")
                data, _ = self.video_socket.recvfrom(1000000)
                if data == b'quit':
                    print("Quitting...")
                    self.stop()
                data = pickle.loads(data)
                self.frame_queue.put(data)
            except (ConnectionResetError, OSError) as e:
                print("Connection reset or error occurred. Exiting...",e)
                self.stop()

    def receive_audio(self):
        while not self.stop_event.is_set():
            try:
                # print("Receiving audio...")
                audio_data, _ = self.audio_socket.recvfrom(1000000)
                if audio_data == b'quit':
                    print("Quitting...")
                    self.stop()
                self.audio_queue.put(audio_data)
            except (ConnectionResetError, OSError):
                print("Connection reset or error occurred. Exiting...")
                self.stop()

    def display_frames(self, window_name):
        while not self.stop_event.is_set():
            if not self.frame_queue.empty():
                data = self.frame_queue.get()
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                cv2.imshow(window_name, img)

            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get()
                self.audio_stream.write(audio_data)

            if cv2.waitKey(25) == ord('q'):
                print("Quitting...")
                self.stop()
            else:
                continue



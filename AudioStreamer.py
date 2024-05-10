import cv2
import pyaudio
import socket
import pickle
import threading
from queue import Queue
import wave

class StreamingServer:
    def __init__(self, server_ip, video_port, audio_port, chunk_size=1024):
        self.server_ip = server_ip
        self.video_port = video_port
        self.audio_port = audio_port
        self.chunk_size = chunk_size

        self.video_clients = []
        self.audio_clients = []

        # Video setup
        print("Accessing camera...")
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)
        self.cap.set(4, 480)
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.video_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000)
        self.video_socket.bind((server_ip, video_port))
        self.stop_event = threading.Event()
        self.frame_queue = Queue()

        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.audio_input_stream = self.audio.open(format=pyaudio.paInt16,
                                                  channels=1,
                                                  rate=44100,
                                                  input=True,
                                                  frames_per_buffer=self.chunk_size)
        self.audio_frames = []
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1000000)
        self.audio_socket.bind((server_ip, audio_port))

        self.accept_video_thread = threading.Thread(target=self.accept_video_connection)
        self.accept_audio_thread = threading.Thread(target=self.accept_audio_connection)
        self.video_stream_thread = threading.Thread(target=self.video_stream)
        self.audio_stream_thread = threading.Thread(target=self.stream_audio)
        self.display_thread = threading.Thread(target=self.display_frames)

    def video_stream(self):
        print(f"Video streamer listening on {self.server_ip}:{self.video_port}")
        while not self.stop_event.is_set() and self.cap.isOpened():
            ret, img = self.cap.read()
            if not ret:
                print("Error reading frame")
                continue
            self.frame_queue.put(img)
            ret, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 30])
            x_as_bytes = pickle.dumps(buffer)
            try:
                for client in self.video_clients:
                    self.video_socket.sendto(x_as_bytes, client)
            except (ConnectionError, OSError) as e:
                print(f'Video Error: {e}')
                self.stop_event.set()
                break

    def stream_audio(self):
        print(f"Audio streamer listening on {self.server_ip}:{self.audio_port}")
        while not self.stop_event.is_set():
            try:
                audio_data = self.audio_input_stream.read(self.chunk_size)
                self.audio_frames.append(audio_data)
                for client in self.audio_clients:
                    self.audio_socket.sendto(audio_data, client)
            except (ConnectionError, OSError) as e:
                print(f'Audio Error: {e}')
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
                    for client in self.video_clients:
                        self.video_socket.sendto(b'quit', client)
                    for client in self.audio_clients:
                        self.audio_socket.sendto(b'quit', client)
                    self.stop()
                    break

    def accept_video_connection(self):
        print("Waiting for video connections...")
        while not self.stop_event.is_set():
            try:
                data, addr = self.video_socket.recvfrom(1000000)
                if data == b'INIT_VIDEO':
                    print(f'Video connection established with {addr}')
                    self.video_clients.append(addr)
                elif data == b'quit':
                    print(f'Video connection closed by {addr}')
                    self.video_clients.remove(addr)
                else:
                    print("Video connection rejected")
            except:
                self.stop_event.set()
                break

    def accept_audio_connection(self):
        print("Waiting for audio connections...")
        while not self.stop_event.is_set():
            try:
                data, addr = self.audio_socket.recvfrom(1000000)
                if data == b'INIT_AUDIO':
                    print(f'Audio connection established with {addr}')
                    self.audio_clients.append(addr)
                elif data == b'quit':
                    print(f'Audio connection closed by {addr}')
                    self.audio_clients.remove(addr)
                else:
                    print("Audio connection rejected")
            except:
                self.stop_event.set()
                break

    def start(self):
        self.accept_video_thread.start()
        self.accept_audio_thread.start()
        self.video_stream_thread.start()
        self.audio_stream_thread.start()
        self.display_thread.start()

    def stop(self):
        self.video_socket.close()
        self.audio_socket.close()
        print('Cleaning up...')
        self.stop_event.set()
        print('Destroying window...')
        cv2.destroyAllWindows()
        print('Closing camera...')
        self.cap.release()
        print('Closing video stream thread...')
        self.video_stream_thread.join()
        print('Closing audio stream thread...')
        self.audio_stream_thread.join()
        print('Closing accept video thread...')
        # self.accept_video_thread.join()
        print('Closing accept audio thread...')
        # self.accept_audio_thread.join()
        self.audio_input_stream.stop_stream()
        self.audio_input_stream.close()
        self.audio.terminate()
        print('Saving audio to file...')
        sound_file = wave.open("output.wav", "wb")
        sound_file.setnchannels(1)
        sound_file.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
        sound_file.setframerate(44100)
        sound_file.writeframes(b''.join(self.audio_frames))
        sound_file.close()
        print('Closing display thread...')
        self.display_thread.join()

        exit()

# Usage example
streaming_server = StreamingServer(socket.gethostbyname(socket.gethostname()), 8000, 8001)
streaming_server.start()

if cv2.waitKey(25) == ord('q'):
    print("Quitting... from here")
    for client in streaming_server.video_clients:
        streaming_server.video_socket.sendto(b'quit', client)
        streaming_server.audio_socket.sendto(b'quit', client)
    streaming_server.stop()

# Wait for Ctrl+C or some other condition to stop
# streaming_server.stop()
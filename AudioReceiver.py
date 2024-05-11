import cv2
import socket
import pickle
import threading
import pyaudio
from queue import Queue
import tkinter
import tkinter.scrolledtext
from tkinter import PhotoImage, Toplevel, simpledialog
from tkinter import filedialog
import tqdm # type: ignore
import os

class Audience:
    server_ip = socket.gethostbyname(socket.gethostname())
    server_video_port = 8000
    server_audio_port = 8001
    server_chat_port = 9000

    def __init__(self, host, video_port, audio_port, window_name='Audience'):
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.chat_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.ip = host
        self.video_port = video_port
        self.audio_port = audio_port


        self.video_socket.bind((self.ip, self.video_port))
        self.audio_socket.bind((self.ip, self.audio_port))
        self.chat_socket.connect((self.ip, Audience.server_chat_port))

        print(f'Connected to video stream at {self.ip}:{self.video_port}')
        print(f'Connected to audio stream at {self.ip}:{self.audio_port}')
        print(f'Connected to chat server at {self.ip}:{Audience.server_chat_port}')

        msg = tkinter.Tk()
        msg.withdraw()

        self.nickname = simpledialog.askstring(
            "Nickname", "Please choose a nickname", parent=msg)
        self.gui_done = False

        self.running = True

        # gui_thread = threading.Thread(target=self.gui_loop)

        self.chat_receive_thread = threading.Thread(target=self.receive)


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
        
    def gui_loop(self):
        self.win = tkinter.Tk()
        self.win.configure(bg="lightgray")

        self.chat_label = tkinter.Label(
            self.win, text="Chat: ", bg="lightgray")
        self.chat_label.configure(font=("Arial", 12))
        self.chat_label.pack(padx=20, pady=5)

        self.text_area = tkinter.scrolledtext.ScrolledText(self.win)
        self.text_area.pack(padx=20, pady=5)
        self.text_area.config(state='disabled')

        self.msg_label = tkinter.Label(
            self.win, text="message: ", bg="lightgray")
        self.msg_label.configure(font=("Arial", 12))
        self.msg_label.pack(padx=20, pady=5)

        self.input_area = tkinter.Text(self.win, height=3)
        self.input_area.pack(padx=20, pady=5)

        self.send_button = tkinter.Button(
            self.win, text="Send Text", command=self.write)
        self.send_button.config(font=("Arial", 12))
        self.send_button.pack(padx=20, pady=5)
        
        self.select_file_button = tkinter.Button(
            self.win, text="Select File", command=self.selectFile)
        self.select_file_button.config(font=("Arial", 12))
        self.select_file_button.pack(padx=50, pady=5)

        self.send_file_button = tkinter.Button(
            self.win, text="Send File", command=self.sendFile)
        self.send_file_button.config(font=("Arial", 12))
        self.send_file_button.pack(padx=50, pady=5)

        self.gui_done = True

        self.win.protocol("WM_DELETE_WINDOW", self.stop)

        self.win.mainloop()

    def write(self):
        print('entered write')
        try:
            message = f"{self.nickname} : {self.input_area.get('1.0', 'end')}"
            print(f'Message: {message}')
            
            self.chat_socket.send(("_me_" + message).encode('utf-8'))
            print('Message sent')
            self.input_area.delete('1.0', 'end')
        except OSError as e:
            print(f"Error sending message: {e}")

        
    def receive(self):
        print("entered into the receive method")
        while self.running:
            try:
                message = self.chat_socket.recv(1024)
                print(f'Message received: {message}')
                message = message.decode('utf-8')
                print(f'Server Nickname received : {message}')
                if message == 'NICK':
                    print("Client nickname: " + self.nickname)
                    self.chat_socket.send(self.nickname.encode('utf-8'))

                    print('Client nickname: (Meherun) sent to the server')
                if message.startswith('FILE'):
                    file,nickname = message.split(' ')
                    self.receiveFile(nickname)
                else:
                    if self.gui_done:
                        self.text_area.config(state='normal')
                        self.text_area.insert('end', message)
                        self.text_area.yview('end')
                        self.text_area.config(state='disabled')

            except ConnectionAbortedError:
                break
            except Exception as e:
                print("Error",e)
                self.chat_socket.close()
                break

    def selectFile(self):
        global filename
        filename = filedialog.askopenfilename(initialdir=os.getcwd(
        ), title="Select Image File", filetypes=(('Text files', '*.txt'), ('All files', '*.*')))
    
    def sendFile(self):
        global filename
        try:
            self.chat_socket.send('file'.encode('utf-8'))
            with open(filename,'rb') as f:
                content = f.read()
            lst = filename.split('/')
            filepath = lst[-1]
            response = {
                'status': 'OK',
                'filename': filepath,
                'content': content
            }
            success = True

        except FileNotFoundError:
            print('File does not exist')
            response = {
                'status': 'ERROR',
            }
            success = False

        response = pickle.dumps(response)
        self.chat_socket.send(f'{len(response)}'.encode())
        print(f'file sent size: {len(response)}')

        total_size = len(response)

        with tqdm.tqdm(total=total_size,unit='B',unit_scale=True,unit_divisor=1024) as progress: 
            sent_len = 0
            chunk_size = 4096

            while sent_len < total_size:
                chunk = response[sent_len:sent_len+chunk_size]
                sent_len += len(chunk)
                self.chat_socket.send(chunk)
                print(chunk)
                progress.update(len(chunk))


        if success: print(f'Uploaded {filename}')
        else: print('Try again.')

    def receiveFile(self,nickname):
        try:
            print('entered into the receiveFile method')
            message = self.chat_socket.recv(1024)
            print(f'Message received: {message}')
            message = pickle.loads(message)
            print(f'Message received: {message}')
            filename = message['filename']
            content = message['content']
            print(f'Filename: {filename}')
            print(f'Content: {content}')
            if not os.path.exists(self.nickname):
                os.makedirs(self.nickname)
            filepath=os.path.join(self.nickname,filename)
            with open(filepath, 'wb') as f:
                f.write(content)

            print(f'File received: {filename}')

            if self.gui_done:
                self.text_area.config(state='normal')
                self.text_area.insert('end', f'{nickname} sent a file: {filename}\n')
                self.text_area.yview('end')
                self.text_area.config(state='disabled')
            
        except Exception as e:
            print(f'Error: {e}')

    def start(self):
        self.receive_video_thread.start()
        self.receive_audio_thread.start()
        self.display_thread.start()
        self.chat_receive_thread.start()
        self.gui_loop()

    def stop_chat(self):
        self.running = False
        self.win.destroy()
        self.chat_socket.close()

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
        self.stop_chat()
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



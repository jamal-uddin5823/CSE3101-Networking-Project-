import struct
import os
import pickle
import socket
import threading
import tkinter
import tkinter.scrolledtext
from tkinter import PhotoImage, Toplevel, simpledialog
from tkinter import filedialog
import tqdm # type: ignore
from tkinter import ttk

HOST = socket.gethostbyname(socket.gethostname())
PORT = 9002
sock: socket.socket

# TCP Reno Parameters
SSTHRESH = 65535  # Initial slow start threshold
CWND = 1  # Initial congestion window size

# Flow Control Parameters
RWND = 65535  # Receiver window size

class Client:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect((host, port))

        self.client_ip, self.client_port = self.sock.getsockname()
        print(f"Client IP: {self.client_ip}, Port: {self.client_port}")

        msg = tkinter.Tk()
        msg.withdraw()

        self.nickname = simpledialog.askstring(
            "Nickname", "Please choose a nickname", parent=msg)
        self.gui_done = False

        self.running = True

        receive_thread = threading.Thread(target=self.receive)

        receive_thread.start()

    def gui_loop(self):
        self.win = tkinter.Tk()
        self.win.title("ShouldStream")

        # Create a frame to contain all elements
        main_frame = ttk.Frame(self.win)
        main_frame.pack(fill=tkinter.BOTH, expand=True)

        # Create labels and text areas
        self.chat_label = ttk.Label(main_frame, text="Chat Room", font=("Georgia", 20))
        self.chat_label.pack(padx=20, pady=(20, 5), anchor="center")

        self.text_area = tkinter.scrolledtext.ScrolledText(main_frame, font=("Georgia", 17))
        self.text_area.pack(fill=tkinter.BOTH, expand=True, padx=20, pady=5)

        self.msg_label = ttk.Label(main_frame, text="Text Your Message", font=("Georgia", 20))
        self.msg_label.pack(padx=20, pady=(5, 5), anchor="center")

        self.input_area = tkinter.Text(main_frame, height=3, font=("Georgia", 17))
        self.input_area.pack(fill=tkinter.BOTH, expand=True, padx=20, pady=(0, 5))

        # Create buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(padx=20, pady=(0, 20), anchor="e")

        self.send_button = ttk.Button(button_frame, text="Send Text", command=self.write)
        self.send_button.pack(side=tkinter.LEFT, padx=(0, 10))

        self.select_file_button = ttk.Button(button_frame, text="Select File", command=self.selectFile)
        self.select_file_button.pack(side=tkinter.LEFT, padx=(0, 10))

        self.send_file_button = ttk.Button(button_frame, text="Send File", command=self.sendFile)
        self.send_file_button.pack(side=tkinter.LEFT)

        # Make the window resizable
        self.win.resizable(True, True)

        self.gui_done = True
        self.win.protocol("WM_DELETE_WINDOW", self.stop)
        self.win.mainloop()

    def write(self):
        print('entered write')
        try:
            message = f"{self.nickname} : {self.input_area.get('1.0', 'end')}"
            
            self.sock.send(("_me_" + message).encode('utf-8'))
            print('Message sent')
            # ack=self.sock.recv(1024)
            # if ack.decode('utf-8') == 'ACK':
            #     print('Message sent')
            # else:
            #     raise OSError('ACK Message not received')
            self.input_area.delete('1.0', 'end')
        except OSError as e:
            print(f"Error sending message: {e}")

    def receive(self):
        print("entered into the receive method")
        while self.running:
            try:
                message = self.sock.recv(1024)
                print(f'Message received: {message}')
                message = message.decode('utf-8')
                print(f'Message received: {message}')
                print(f'Server Nickname received : {message}')
                if message == 'NICK':
                    print("Client nickname: " + self.nickname)
                    self.sock.send(self.nickname.encode('utf-8'))

                    print('Client nickname: (Meherun) sent to the server')
                if message.startswith('FILE'):
                    self.receiveFile(message)
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
                self.sock.close()
                break

    def stop(self):
        self.running = False
        self.win.destroy()
        self.sock.close()
        exit(0)

    def selectFile(self):
        global filename
        filename = filedialog.askopenfilename(initialdir=os.getcwd(
        ), title="Select Image File", filetypes=(('Text files', '*.txt'), ('All files', '*.*')))
               
    def sendFile(self):
        global filename
        try:
            self.sock.send('file'.encode('utf-8'))

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
        self.sock.send(f'{len(response)}'.encode())
        print(f'file sent size: {len(response)}')

        total_size = len(response)

        with tqdm.tqdm(total=total_size,unit='B',unit_scale=True,unit_divisor=1024) as progress: 
            sent_len = 0
            chunk_size = 4096

            while sent_len < total_size:
                chunk = response[sent_len:sent_len+chunk_size]
                sent_len += len(chunk)
                self.sock.send(chunk)
                print(chunk)
                progress.update(len(chunk))


        if success: print(f'Uploaded {filename}')
        else: print('Try again.')
        
    def receiveFile(self,message):
        rwnd = RWND

        try:
            file, filename, total_size = message.split(' ')
            print(f'Receiving file: {filename}\nTotal size: {total_size}')
            total_size = int(total_size)
            data = b''
            received_size = 0
            expected_seq_num = 0

            while received_size < total_size:
                header = self.sock.recv(5)
                seq_num, chunk_len = struct.unpack('!IB', header)

                if seq_num == expected_seq_num:
                    print('Received chunk')
                    chunk = self.sock.recv(chunk_len)
                    print(f'Chunk size: {len(chunk)}')
                    print(f'Chunk: {chunk}')
                    data += chunk
                    received_size += chunk_len

                    # Send ACK
                    print(f'Sending ACK: {seq_num + chunk_len} to server {self.sock}')
                    self.sock.send(struct.pack('!I', seq_num + chunk_len))
                    expected_seq_num += chunk_len
                else:
                    print(f'Expected: {expected_seq_num}, Received: {seq_num}')
                    # Duplicate or out-of-order packet
                    self.sock.send(struct.pack('!I', expected_seq_num))

            content = data.decode('utf-8')
            response = {
                'status': 'OK',
                'filename': filename,
                'content': content
            }

            if not os.path.exists(self.nickname):
                os.makedirs(self.nickname)

            filepath = os.path.join(self.nickname, filename)
            with open(filepath, 'wb') as f:
                f.write(content.encode('utf-8'))

            print(f'File received: {filename}')

        except Exception as e:
            print(f'Error: {e}')

client = Client(HOST, PORT)
client.gui_loop()
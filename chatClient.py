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

HOST = socket.gethostbyname(socket.gethostname())
PORT = 9000
sock: socket.socket

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

        # gui_thread = threading.Thread(target=self.gui_loop)

        receive_thread = threading.Thread(target=self.receive)

        # gui_thread.start()
        receive_thread.start()

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

        self.recv_file_button = tkinter.Button(
            self.win, text="Receive File", command=self.receiveFile)
        self.recv_file_button.config(font=("Arial", 12))
        self.recv_file_button.pack(padx=50, pady=5)

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
                print(f'Server Nickname received : {message}')
                if message == 'NICK':
                    print("Client nickname: " + self.nickname)
                    self.sock.send(self.nickname.encode('utf-8'))

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
            # ack=self.sock.recv(1024)
            # if ack.decode('utf-8') == 'ACK':
            #     print('File sending started')
            # else:
            #     raise OSError('ACK file not received')
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
        
    def receiveFile(self,nickname):
        try:
            print('entered into the receiveFile method')
            message = self.sock.recv(1024)
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

client = Client(HOST, PORT)
client.gui_loop()
import socket
import threading
import pickle
import os
import tqdm

HOST = socket.gethostbyname(socket.gethostname())
PORT = 9000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))

server.listen()

clients = []
nicknames = []


def broadcast(message):
    for client in clients:
        client.send(message)


def broadcastFile(filepath):
    print("starting to broadcast the file")

    filename = os.path.basename(filepath)

    print(filepath)
    print(filename)

    for client in clients:
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            response = {
                'status': 'OK',
                'filename': filename,
                'content': content
            }
            success = True

            print('file opened')
        except FileNotFoundError:
            print('File does not exist')
            response = {
                'status': 'ERROR',
            }
            success = False

        print(response)
        response = pickle.dumps(response)

        total_size = len(response)

        with tqdm.tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as progress:
            sent_len = 0
            chunk_size = 4096

            while sent_len < total_size:
                chunk = response[sent_len:sent_len+chunk_size]
                sent_len += len(chunk)
                client.send(chunk)
                # progress.update(len(chunk))

        if success:
            print(f'Broadcast {filename} to Client: {client}')
        else:
            print('Try again.')


def receive():
    while True:
        try:
            client, address = server.accept()
            print(f"Connected with {str(address)}")

            print("connection done")

            client.send("NICK".encode('utf-8'))
            nickname = client.recv(1024).decode('utf-8')

            print(nickname)

            nicknames.append(nickname)
            clients.append(client)

            print(f"Nickname of the client is {nickname}")
            broadcast(f"{nickname} connected to the server!\n".encode('utf-8'))
            print("broadcast nickname done")

            client.send("Connected to the server".encode('utf-8'))

            chat_thread = threading.Thread(target=handle, args=(client,))
            chat_thread.start()

        except:
            print("something is wrong")

# handle

def handle(client):
    while True:
        try:
            print("handle client entered")
            message = client.recv(1024).decode('utf-8')
            print("handle client entered 2")
            print(message)
            code = message[:3]
            print("code : " + code)

            if (code == '_m_'):
                message = message[3:]
                message = message.encode('utf-8')

                print(message)
                print(f"{nicknames[clients.index(client)]}")
                broadcast(message)
                print("broadcast message done")
            else:
                receiveFile(client)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]

            nicknames.remove(nickname)
            break


def receiveFile(client):
    try:
        print("into receive method")
        length = client.recv(1024)  # 39 in client
        print(length)
        length = length.decode()
        response = b''
        got_len = 0
        while got_len < int(length):
            data = client.recv(1024)
            print(data)
            response += data
            got_len += len(data)

        response = pickle.loads(response)

        if response['status'] == 'ERROR':
            return

        filepath = os.path.join('./server_files', response['filename'])
        print(filepath)

        with open(filepath, 'wb') as f:
            f.write(response['content'])

        print('Received')
        broadcastFile(filepath)

    except Exception as e:
        print(f"Error: {e}")


print("Server running...")

receive()
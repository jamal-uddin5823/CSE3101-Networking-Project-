import socket
import threading
import pickle
import os
import tqdm # type: ignore
import struct

HOST = socket.gethostbyname(socket.gethostname())
PORT = 9002

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))

server.listen()

clients = []
nicknames = []

SSTHRESH = 65535  # Initial slow start threshold
CWND = 1  # Initial congestion window size

# Flow Control Parameters
RWND = 65535  # Receiver window size


def broadcast(message):
    for client in clients:
        client.send(message)


def broadcastFile(filepath):
    global clients,HOST,PORT
    print("Starting to broadcast the file")
    filename = os.path.basename(filepath)
    print(filepath)
    print(filename)
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        response = {
            'status': 'OK',
            'filename': filename,
            'content': content
        }
        success = True
        print('File opened')
    except FileNotFoundError:
        print('File does not exist')
        response = {
            'status': 'ERROR',
        }
        success = False

    content = response['content']
    total_size = len(content)

    for client in clients:
        print(f'Broadcasting {filename} to Client: {client}')
        client.send(f'FILE {filename} {total_size}'.encode('utf-8'))

    # TCP Reno Congestion Control
    ssthresh = SSTHRESH
    cwnd = CWND
    rwnd = RWND
    duplicate_acks = 0

    sent_len = 0
    chunk_size = min(cwnd, rwnd)
    seq_num = 0

    print(f'Total size: {total_size}')
    with tqdm.tqdm(total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as progress:
        print(f'Sent length: {sent_len}\n total size: {total_size}')
        while sent_len < total_size:
            chunk = content[sent_len:sent_len + chunk_size]
            print(f'Chunk size: {len(chunk)}')
            for client in clients:
                client.send(struct.pack('!IB', seq_num, len(chunk)) + chunk)
                seq_num += len(chunk)
                sent_len += len(chunk)
                progress.update(len(chunk))

                ack_count = 0
                ack_seq_num = seq_num

                while ack_count < len(clients):
                    print(f'Waiting for ACK {(HOST,PORT)}')
                    ack = client.recv(5)
                    if ack:  # Check if data was received
                        print(f'ACK: {ack}')
                        ack_seq_num, = struct.unpack('!I', ack[:4])

                        if ack_seq_num == seq_num:
                            # Successful transmission
                            ack_count += 1
                            duplicate_acks = 0
                            cwnd = min(cwnd + 1, rwnd)
                        else:
                            # Duplicate ACK
                            duplicate_acks += 1
                            if duplicate_acks == 3:
                                # Triple duplicate ACK, enter fast retransmit and fast recovery
                                ssthresh = cwnd // 2
                                cwnd = ssthresh + 3
                                # Retransmit the lost packet
                                for client in clients:
                                    client.send(struct.pack('!IB', ack_seq_num, len(chunk)) + chunk)
                            elif duplicate_acks > 3:
                                # Packet loss detected
                                cwnd += 1

                chunk_size = min(cwnd, rwnd)
                print(f'Chunk size: {chunk_size}')

    if success:
        for client in clients:
            print(f'Broadcasted {filename} to Client: {client}')
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
            # client.send('ACK'.encode('utf-8'))
            print("handle client entered 2")
            print(message)
            code = message[:4]
            print("code : " + code)

            if (code == '_me_'):
                message = message[4:]
                message = message.encode('utf-8')

                print(message)
                print(f"{nicknames[clients.index(client)]}")
                broadcast(message)
                print("broadcast message done")
            elif (code == 'file'):
                receiveFile(client)
            else:
                raise Exception("Invalid code")
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
        print(f'Length: {length}')
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
        print(f'Filepath: {filepath}')

        print(f'Received content: {response["content"]}')

        with open(filepath, 'wb') as f:
            f.write(response['content'])

        print('Received')
        broadcastFile(filepath)

    except Exception as e:
        print(f"Error: {e}")


print("Server running...")

receive()

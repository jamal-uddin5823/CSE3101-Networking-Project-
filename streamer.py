from VideoStreamer import VideoStreamer
from AudioStreamer import AudioStreamer
import socket
import cv2

if __name__ == "__main__":
    server_ip = socket.gethostbyname(socket.gethostname())
    server_video_port = 6666
    streamer = VideoStreamer(server_ip, server_video_port)
    streamer.start()
 
    if cv2.waitKey(25) == ord('q'):
        print("Quitting... from here")
        for client in streamer.clients:
            streamer.s.sendto(b'quit', client)
        streamer.stop()
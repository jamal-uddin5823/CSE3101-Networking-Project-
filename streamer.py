from StreamingServer import StreamingServer
import socket
import cv2


# Usage example
streaming_server = StreamingServer(socket.gethostbyname(socket.gethostname()), 8000, 8001,9000)
streaming_server.start()

if cv2.waitKey(25) == ord('q'):
    print("Quitting... from here")
    for client in streaming_server.video_clients:
        streaming_server.video_socket.sendto(b'quit', client)
        streaming_server.audio_socket.sendto(b'quit', client)
    streaming_server.stop()

# Wait for Ctrl+C or some other condition to stop
# streaming_server.stop()
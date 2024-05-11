from StreamClient import Audience
import socket


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ip = socket.gethostbyname(socket.gethostname())
port = 6667

audience = Audience(ip,6666,6667,'Audience 1')
audience.start()
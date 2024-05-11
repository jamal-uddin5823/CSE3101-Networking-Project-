from StreamClient import Audience
import socket


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ip = socket.gethostbyname(socket.gethostname())
port = 6667

audience = Audience(ip,5555,5556,'Audience 2')
audience.start()
from Audience import Audience
import socket


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip = socket.gethostbyname(socket.gethostname())
    port = 6669
 
    audience = Audience(ip,port,'Audience 3')
    audience.start()
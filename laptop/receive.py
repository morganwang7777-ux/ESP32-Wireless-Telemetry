import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
sock.bind(("0.0.0.0", 5005))   # listen on port 5005
print("Listening for ESP32 on port 5005... (Ctrl+C to stop)")

while True:
    data, sender = sock.recvfrom(1024)        # wait for one message
    print(sender[0], data.decode())
import socket
import subprocess
import threading

def start_server():
    s = socket.socket()
    s.bind(('0.0.0.0', 5003))
    s.listen(1)
    conn, addr = s.accept()
    data = conn.recv(1024).decode()
    print("--- WRK2 REQUEST ---")
    print(data)
    print("--------------------")
    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n")
    conn.close()
    s.close()

t = threading.Thread(target=start_server)
t.start()

cmd = [
    "C:\\Users\\daksh\\AppData\\Local\\Programs\\DockerDesktop\\resources\\bin\\docker.EXE", "run", "--rm", "--network", "host",
    "-v", "c:\\Users\\daksh\\.gemini\\antigravity-ide\\scratch\\DeathStarBench\\hotelReservation\\wrk2\\scripts\\hotel-reservation\\mixed-workload_type_1.lua:/script.lua",
    "dsb-wrk2", "-t", "1", "-c", "1", "-d", "2s", "-R", "1", "-L", "-s", "/script.lua", "http://localhost:5003"
]
subprocess.run(cmd)
t.join()

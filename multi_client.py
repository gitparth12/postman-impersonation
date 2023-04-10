import socket
import os

path = "./postman-impersonation/e2e_tests/"

in_files = []
all_files = os.listdir(path)
for file in all_files:
    if file.endswith(".in"):
        file_abs = os.path.abspath(path) + "/" + file
        in_files.append(file_abs)

for test in in_files:

    f = open(test, "r")
    request_list_raw = f.read().splitlines()
    request_list = []
    f.close()
    for req in request_list_raw:
        req_actual = req.strip() + "\r\n"
        request_list.append(req_actual)

    out_path = test[:-2] + "out"
    out_file = open(out_path, "w")
    server_responses = []

    client = socket.socket()
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.connect((socket.gethostbyname(socket.gethostname()), 1025))


    with client:
        while True:
            pass







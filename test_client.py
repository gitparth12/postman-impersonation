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

        # recv the 220 thingy 
        server_responses.append(f"S: {client.recv(1024).decode('ascii')}")

        for request in request_list:
        
            server_responses.append(f"C: {request}")
            client.send(request.encode("ascii"))
            response = client.recv(1024).decode('ascii')
            if "250 AUTH CRAM-MD5" in response:
                ls  = response.split("\r\n")
                server_responses.append(f"S: {ls[0]}\r\n")
                server_responses.append(f"S: {ls[1]}\r\n")
            else:
                server_responses.append(f"S: {response}")

    
    for r in server_responses:
        line = r.strip("\n")
        out_file.write(line)
    out_file.close()






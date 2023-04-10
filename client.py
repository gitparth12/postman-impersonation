import os
import socket
import sys
import datetime
import base64
import hmac
import re

# Visit https://edstem.org/au/courses/8961/lessons/26522/slides/196175 to get
PERSONAL_ID = '72E92A'
PERSONAL_SECRET = 'debbd77a26da3d9b5c804fe25181269b'

def check_date(date: str) -> bool:
    """
    Checks the format of date.

    Args:
        date: string variable with just the date, no special characters.

    Returns:
        boolean to indicate whether the date is valid or not.
    """
    try:
        date_format = datetime.datetime.strptime(date, "%a, %d %b %Y %X %z")
        return True
    except ValueError:
        return False


def check_email(email: str) -> bool:
    """Checks the given email against the specification."""
    if re.match(r"<[A-Za-z0-9](?:[A-Za-z0-9]|-)*(?:.[A-Za-z0-9](?:[A-Za-z0-9]|-)*)*@[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-[A-Za-z0-9])*\.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*>", email):
        return True
    return False


def parse_config_file() -> dict:
    """
    Reads command line arguments and parses the config file.

    Returns:
        connection_info: dictionary with all the information from the config file
    """
    if len(sys.argv) == 1:
        sys.exit(1)
    else:
        filepath = sys.argv[1]
    if not os.access(filepath, os.R_OK):
        # print("can't access config file")
        sys.exit(2)
    temp_dict = {}
    try:
        with open(filepath) as file:
            for line in file:
                line = line.strip()
                arr = line.split('=')
                if arr[0] == "server_port" and int(arr[1]) > 1024:
                    temp_dict.update({"server_port": int(arr[1])})
                elif arr[0] == "send_path":
                    temp_dict.update({"send_path": arr[1]})
            if len(temp_dict) != 2:
                # print("incomplete config file")
                sys.exit(2)
        return temp_dict
    except FileNotFoundError:
        sys.exit(1)

connection_info = parse_config_file()
"""
Dictionary that has all the information from the config file provided.
"""

def parse_email_file(filepath: str) -> dict:
    """
    Reads a mail transaction file and puts all commands into a list, post error checking.

    Args:
        filepath: path to the mail transaction file, obtained from the config file.
    
    Returns:
        values: dictionary containing all information from the file and the integer represents the number of recipients.
            Contains:
                from_user: str
                to_users: list
                date: str
                subject: str
                body: list
    """

    try:
        with open(filepath) as file:
            values = {}
            # Checking From value
            line = file.readline().strip()
            arr = line.split(': ')
            if arr[0] != "From":
                return {}
            elif not check_email(arr[1]):
                return {}
            values.update({"from_user": arr[1]})

            # Checking To values
            line = file.readline().strip()
            arr = line.split(': ')
            if arr[0] != "To":
                return {}
            emails = arr[1].split(",")
            valid_rcpts = []
            for email in emails:
                if check_email(email):
                    valid_rcpts.append(email)
            values.update({"to_users": valid_rcpts})

            # Checking Date value according to RFC 5322 standard
            line = file.readline().strip()
            temp = line.split(": ")
            if not check_date(temp[1]):
                return {}
            values.update({"date": temp[1]})

            # Checking Subject value
            line = file.readline().strip()
            arr = line.split(": ")
            if arr[0] != "Subject":
                return {}
            values.update({"subject": arr[1]})

            # Storing body in values
            body = []
            for line in file:
                body.append(line.strip())
            values.update({"body": body})
    except FileNotFoundError:
        return {}
    
    return values


def send_email(abs_filepath: str, sock: socket.socket, data: dict) -> None:
    """
    Communicates with the server in order to send an email using the SMTP protocol.

    Args:
        sock: the client socket connected to the server.
        data: the dictionary containing all necessary information for a plain text email.
    """
    with sock:
        # Send the EHLO message, and print sent and received messages
        sent = f"EHLO {socket.gethostbyname(socket.gethostname())}\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")
        if received.endswith('AUTH CRAM-MD5\r\n'):
            if 'auth' in abs_filepath.lower():
                sent = 'AUTH CRAM-MD5\r\n'
                print(f'C: {sent}', end='', flush=True)
                sock.send(sent.encode())
                authenticate(sock)
        # Send the MAIL FROM command
        
        sent = "MAIL FROM:" + data["from_user"] + "\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")

        # Send the RCPT TO commands
        recipients = data["to_users"]
        for rcpt in recipients:
            sent = f"RCPT TO:{rcpt}\r\n"
            print(f"C: {sent}", end="")
            sock.send(sent.encode())
            received = sock.recv(1024).decode('ascii')
            print(f"S: {received}", end="")
        
        # Send the DATA command
        sent = "DATA\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")

        # Send the Date value
        sent = "Date: " + data["date"] + "\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")

        # Send the Subject value
        sent = "Subject: " + data["subject"] + "\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")

        # Send the body of the mail
        body = data["body"]
        for line in body:
            line = line + "\r\n"
            print(f"C: {line}", end="")
            sock.send(line.encode())
            received = sock.recv(1024).decode('ascii')
            print(f"S: {received}", end="")
        
        # Send the end of mail
        print("C: .\r\n", end="")
        sock.send(b".\r\n")
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")

        # Send the QUIT command
        sent = "QUIT\r\n"
        print(f"C: {sent}", end="")
        sock.send(sent.encode())
        received = sock.recv(1024).decode('ascii')
        print(f"S: {received}", end="")


def get_email_files(dir_path: str) -> list:
    """
    Returns a list of valid filepaths in the given send_path directory from the config file.

    Args:
        dir_path: the path to the directory where email files are stored
    """
    file_list = []

    # Checking if a valid directory exists
    if not os.path.isdir(dir_path):
        sys.exit(2)
    
    files = os.listdir(dir_path)
    # Sorting the files alphabetically
    files.sort()
    for file in files:
        if file.endswith(".txt"):
            file_list.append(dir_path + "/" + file)
    
    return file_list
    

def authenticate(server: socket.socket) -> None:
    """
    Handles authentication requests to the server.
    
    Args:
        server: the socket object to send and receive data from the server
    """
    received = server.recv(1024).decode('ascii') # string along with the status code
    print(f'S: {received}', end='', flush=True)

    if received.startswith("334"):
        ls = received.strip().split()
    else:
        return
    challenge = base64.b64decode(ls[1].encode()) # encoded challenge

    digest = hmac.new(key=PERSONAL_SECRET.encode(), msg=challenge, digestmod='md5').hexdigest()
    digest = f'{PERSONAL_ID} {digest}\r\n' # digest with username
    sent = base64.b64encode(digest.encode()) # encoded digest with username
    print(f'C: {sent.decode("ascii")}\r\n', end='', flush=True)
    server.send(sent)

    received = server.recv(1024).decode('ascii')
    print(f'S: {received}', end='', flush=True)


def setup_client_socket() -> socket.socket:
    """
    Sets up a client socket connection to the server for communication over a network. If 
    the client cannot connect, after 20 seconds, the program automatically exits with an error.

    Returns:
        A client socket connected to the USYD mail server.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # allows us to relaunch the application quickly without having to worry about "address already 
    # in use errors"
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Sets timeout of socket: we will use this to check if we can connect to the server
    sock.settimeout(20)

    try:
        # Connect to server
        sock.connect((socket.gethostname(), connection_info["server_port"]))
        recv = sock.recv(1024).decode('ascii')
        print(f"S: {recv}", end="")
        # if recv[:3] != "220":
        #     print('C: Cannot establish connection\r')
        #     sys.exit(3)
    except socket.error:
        print("C: Cannot establish connection\r")
        sys.exit(3)

    return sock


def main() -> None:
    """Main method of the program."""
    files = get_email_files(connection_info['send_path'])
    for file in files:
        values = parse_email_file(file)
        if len(values) == 0:
            print(f"C: /home{file[1:]}: Bad formation\r")
            continue
        sock = setup_client_socket()
        send_email(os.path.expanduser(connection_info['send_path'])+'/'+file, sock, values)

    sys.exit(0)


if __name__ == "__main__":
    main()
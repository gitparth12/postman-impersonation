import os
import socket
import sys
import re
from dataclasses import dataclass
import datetime
import secrets
import base64
import hmac
import signal


# Visit https://edstem.org/au/courses/8961/lessons/26522/slides/196175 to get
PERSONAL_ID = '72E92A'
PERSONAL_SECRET = 'debbd77a26da3d9b5c804fe25181269b'


@dataclass(frozen=False)
class Email:
    """
    A dataclass containing all necessary information to send a plain text email.
    """
    from_user: str
    """The sender of the email."""

    recipients: list[str]
    """All recipients of the email as a list."""

    date: str
    """The date the email was sent. (may be empty)"""

    subject: str
    """The subject of the email. (may be empty)"""

    body: list[str]
    """The body of the email as a list."""

    def store_email(self, filepath: str, authenticated: bool, filename: str = "unknown.txt") -> None:
        """
        Puts the email into a file and stores it.
        """
        if "~" in filepath:
            if authenticated:
                _ = f"{os.path.expanduser(filepath)}/auth.{filename}"
            else:
                _ = f"{os.path.expanduser(filepath)}/{filename}"
        else:
            if authenticated:
                _ = f"{os.path.abspath(filepath)}/auth.{filename}"
            else:
                _ = f"{os.path.abspath(filepath)}/{filename}"
        with open(_, 'w') as file:
            # Writing sender
            file.write(f"From: {self.from_user}\n")

            # Writing recipient(s)
            file.write("To: ")
            for count, recipient in enumerate(self.recipients):
                if count == len(self.recipients) - 1:
                    file.write(f"{recipient}\n")
                else:
                    file.write(f"{recipient},")
            
            # Writing date
            file.write(f"Date: {self.date}\n")

            # Writing subject
            file.write(f"{self.subject}\n")

            # Writing body
            for count, line in enumerate(self.body):
                if count == len(self.body) - 1:
                    file.write(line)
                else:
                    file.write(f"{line}\n")


def auth_command(client: socket.socket) -> bool:
    """
    Used to deal with an AUTH request by client.

    Args:
        client: the client socket object connected to server port
    """
    # send challenge to client
    challenge = secrets.token_urlsafe(27).encode() # matches the example given in spec
    encoded = base64.b64encode(challenge).decode('ascii')
    client.send(f'334 {encoded}\r\n'.encode())
    print(server_print(f'334 {encoded}\r\n'),end='', flush=True)

    # get digest from client
    received = client.recv(1024).decode('ascii') # encoded base64 and while sending
    print(client_print(received), end='', flush=True)
    if received.strip() == "*":
        # Cancel authentication with 501
        sent = '501 Syntax error in parameters or arguments\r\n'
        print(server_print(sent), end='', flush=True)
        client.send(sent.encode())
        return False
    try:
        decoded = base64.b64decode(received).decode('ascii').strip() # should be the string with username and digest
    except Exception:
        # When answer cannot be decoded
        sent = '501 Syntax error in parameters or arguments\r\n'
        print(server_print(sent), end='', flush=True)
        client.send(sent.encode())
        return False
    ls = decoded.split()
    received_digest = ls[1] # this should be a string

    # recreate hmac digest
    new_digest = hmac.new(key=PERSONAL_SECRET.encode(), msg=challenge, digestmod='md5').hexdigest() # should be a string
    
    authenticated = hmac.compare_digest(new_digest, received_digest)
    if authenticated:
        sent = '235 Authentication successful\r\n'
        client.send(sent.encode())
        print(server_print(sent), end="", flush=True)
    else:
        sent = '535 Authentication credentials invalid\r\n'
        client.send(sent.encode())
        print(server_print(sent), end="", flush=True)
    return authenticated


def server_print(line: str) -> str:
    """Prints given string to stdout, prepended with S: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"S: {string}\r\n"
    return to_print


def client_print(line: str) -> str:
    """Prints given string to stdout, prepended with C: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"C: {string}\r\n"
    return to_print


def check_from_email(email: str) -> bool:
    """Checks the RCPT TO line against a regex setting to validate email."""
    if re.match(r"MAIL FROM:<[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*(?:.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*)@[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-[A-Za-z0-9])*\.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*>", email):
        return True
    else:
        return False


def check_to_email(email: str) -> bool:
    """Checks the RCPT TO line against a regex setting to validate email."""
    if re.match(r"RCPT TO:<[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*(?:.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*)@[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-[A-Za-z0-9])*\.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*>", email):
        return True
    else:
        return False


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


def parse_config_file() -> dict:
    """
    Reads command line arguments and parses the config file.

    Returns:
        connection_info: dictionary with all the information from the config file
            server_port: the port the server listens on
            inbox_path: the filepath where email files are to be stored
    """
    if len(sys.argv) == 1:
        print("no config file given")
        sys.exit(1)
    else:
        filepath = sys.argv[1]
    if not os.access(filepath, os.R_OK):
        print("can't access config file")
        sys.exit(2)
    temp_dict = {}
    try:
        with open(filepath) as file:
            for line in file:
                line = line.strip()
                arr = line.split('=')
                if arr[0] == "server_port" and int(arr[1]) > 1024:
                    temp_dict.update({"server_port": int(arr[1])})
                elif arr[0] == "inbox_path":
                    temp_dict.update({"inbox_path": arr[1]})
            if len(temp_dict) != 2:
                print("incomplete config file")
                sys.exit(2)
        return temp_dict
    except FileNotFoundError:
        print("config not found")
        sys.exit(1)

connection_info = parse_config_file()
"""
Dictionary that has all the information from the config file provided.
    server_port: the port the server listens on
    inbox_path: the filepath where email files are to be stored
"""


def ehlo_command(clientsocket: socket.socket, arr: list, line: str) -> None:
    """
    Deals with the ehlo command sent by client.

    Args:
        clientsocket: the client socket the server is accepting from
        arr: the list containing the client's message split by space
        line: the whole string received from client
    """
    if len(arr) != 2:
        sent = "501 Syntax error in parameters or arguments\r\n"
        print(f"S: {sent}", end="")
        clientsocket.send(sent.encode())
        return
    
    address = arr[1]
    temp = arr[1].split(".")
    # Should be four 8 bit fields
    try:
        if len(temp) == 4:
            for field in temp:
                if int(field) > 255:
                    raise ValueError
        else:
            raise ValueError
    except ValueError:
        sent = "501 Syntax error in parameters or arguments\r\n"
        print(f"S: {sent}", end="", flush=True)
        clientsocket.send(sent.encode())
        return
    
    sent = f"250 {socket.gethostbyname(socket.gethostname())}\r\n250 AUTH CRAM-MD5\r\n"
    print(server_print(sent), end="", flush=True)
    clientsocket.send(sent.encode())


def mail_command(clientsocket: socket.socket, arr: list, line: str, authenticated: bool) -> str:
    """
    Deals with the MAIL command sent by client.

    Args:
        clientsocket: the client socket the server is accpeting from
        arr: the list containing the client's message split by whitespace
        line: the whole string received from client

    Returns:
        boolean value indicating whether the mail was received successfully or not
    """
    from_user = ''
    to_users = []
    date = ''
    subject = ''
    body = []
    # Checking MAIL FROM command
    if line[-2:] != "\r\n" or not check_from_email(line.strip()):
        sent = "501 Syntax error in parameters or arguments\r\n"
        print(f"S: {sent}", end="", flush=True)
        clientsocket.send(sent.encode())
        return 'failure'
    # Storing from user
    temp = line.strip().split(':')
    from_user = temp[1]
    # Sending reply to client and logging
    sent = "250 Requested mail action okay completed\r\n"
    print(f"S: {sent}", end="", flush=True)
    clientsocket.send(sent.encode())

    
    # Checking RCPT TO
    got_rcpt = False
    received = ""
    while True:
        received = clientsocket.recv(1024).decode('ascii')
        if not received:
            print("S: Connection lost\r\n", end="", flush=True)
            return 'failure'
        print(client_print(received), end="", flush=True)
        if received[:4] == "RSET":
            if received == "RSET\r\n":
                sent = "250 Requested mail action okay completed\r\n"
                print(server_print(sent), end="", flush=True)
                clientsocket.send(sent.encode())
                return 'failure'
            else:
                sent = "501 Syntax error in parameters or arguments\r\n"
                print(f"S: {sent}", end="", flush=True)
                clientsocket.send(sent.encode())
                continue
        elif received[:4] == "EHLO":
            ehlo_command(clientsocket, received.strip().split(' '), received)
            return 'failure'
        elif received == "QUIT\r\n":
            return received
        elif received[:4] == "NOOP":
            if received == "NOOP\r\n":
                sent = "250 Requested mail action okay completed\r\n"
                print(server_print(sent), end="", flush=True)
                clientsocket.send(sent.encode())
                continue
            else:
                sent = "501 Syntax error in parameters or arguments\r\n"
                print(server_print(sent), end="", flush=True)
                clientsocket.send(sent.encode())
                continue
        elif received[:4] == "AUTH":
            sent = "503 Bad sequence of commands\r\n"
            print(server_print(sent), end='', flush=True)
            clientsocket.send(sent.encode())
            continue

        # If the DATA command is passed before RCPT TO
        if received[:4] == "DATA":
            if received == "DATA\r\n" and not got_rcpt:
                sent = "503 Bad sequence of commands\r\n"
                print(server_print(sent),end="", flush=True)
                clientsocket.send(sent.encode())
                continue
            elif received == "DATA\r\n" and got_rcpt: # We are done with rcpt data
                sent = "354 Start mail input end <CRLF>.<CRLF>\r\n"
                print(server_print(sent),end="", flush=True)
                clientsocket.send(sent.encode())
                break
            else:
                sent = "501 Syntax error in parameters or arguments\r\n"
                print(f"S: {sent}", end="", flush=True)
                clientsocket.send(sent.encode())
                continue
        
        if received[:4] == "RCPT" and not check_to_email(received.strip()):
            sent = "501 Syntax error in parameters or arguments\r\n"
            print(f"S: {sent}", end="", flush=True)
            clientsocket.send(sent.encode())
            continue
        elif check_to_email(received.strip()):
            # Storing recipients in list
            temp = received.strip().split(':')
            to_users.append(temp[1])
            # Sending reply to client
            sent = "250 Requested mail action okay completed\r\n"
            print(server_print(sent), end="", flush=True)
            clientsocket.send(sent.encode())
            got_rcpt = True
            continue
        else:
            sent = "503 Bad sequence of commands\r\n"
            print(server_print(sent),end="", flush=True)
            clientsocket.send(sent.encode())
            continue
    
    # Checking date field
    # (since we know DATA command was given earlier in the loop)
    while True:
        received = clientsocket.recv(1024).decode('ascii')
        if not received:
            print("S: Connection lost\r\n", end="", flush=True)
            return 'failure'
        print(client_print(received), end="", flush=True)
        
        if received[:6] == "Date: ":
            temp = received.strip().split(': ')
            # Storing date in variable
            if check_date(temp[1]):
                date = temp[1] # else: date will remain an empty string
            else:
                date = ''
        elif received[:9] == "Subject: ":
            # Checking validity of subject
            if received.count("\r\n") == 1:
                subject = received.strip()
            else:
                subject = ''
        else:
            body.append(received.strip())
        # Sending reply to client
        sent = "354 Start mail input end <CRLF>.<CRLF>\r\n"
        print(server_print(sent), end="", flush=True)
        clientsocket.send(sent.encode())
        break
    
    # Checking subject field
    while True:
        received = clientsocket.recv(1024).decode('ascii')
        if not received:
            print("S: Connection lost\r\n", end="", flush=True)
            return 'failure'
        print(client_print(received), end="", flush=True)
        
        if received[:9] == "Subject: ":
            # Checking validity of subject
            if received.count("\r\n") == 1:
                subject = received.strip() # else: subject will remain an empty string
        else:
            body.append(received.strip())
        # Sending reply to client
        sent = "354 Start mail input end <CRLF>.<CRLF>\r\n"
        print(server_print(sent), end="", flush=True)
        clientsocket.send(sent.encode())
        break
    
    # Storing body and ending mail
    while True:
        received = clientsocket.recv(1024).decode('ascii')
        if not received:
            print("S: Connection lost\r\n", end="", flush=True)
            return 'failure'
        print(client_print(received), end="", flush=True)
        
        # Ending mail
        if received == ".\r\n":
            email = Email(from_user, to_users, date, subject, body)
            if date != '':
                # Mon, 14 Sep 1987 23:07:00 +1000
                date_format = datetime.datetime.strptime(date, "%a, %d %b %Y %X %z")
                unix_time = datetime.datetime.timestamp(date_format)
                email.store_email(connection_info['inbox_path'], authenticated, str(int(unix_time))+".txt")
            else:
                email.store_email(connection_info['inbox_path'], authenticated)
            from_user = ''
            to_users = []
            date = ''
            subject = ''
            body = []
            # Sending reply to client
            sent = "250 Requested mail action okay completed\r\n"
            print(server_print(sent), end="", flush=True)
            clientsocket.send(sent.encode())
            return 'success'

        body.append(received.strip())
        # Sending reply to client
        sent = "354 Start mail input end <CRLF>.<CRLF>\r\n"
        print(server_print(sent), end="", flush=True)
        clientsocket.send(sent.encode())


def quit_command(clientsocket: socket.socket, arr: list, line: str) -> bool:
    """
    Deals with the quit command sent by client.

    Args:
        clientsocket: the clienat socket the server is accepting from
        arr: the list containing the client's message split by space
    """

    # If command doesn't match exactly and there's additional special characters
    if line != "QUIT\r\n":
        sent = "501 Syntax error in parameters or arguments\r\n"
        print(f"S: {sent}", end="", flush=True)
        clientsocket.send(sent.encode())
        return False
    
    sent = "221 Service closing transmission channel\r\n"
    print(f"S: {sent}", end='', flush=True)
    clientsocket.send(sent.encode())
    return True


def setup_server_socket() -> socket.socket:
    """
    Sets up a server socket connection to the client for communication over a network.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # allows us to relaunch the application quickly without having to worry about "address already 
    # in use errors"
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Since the server runs indefinitely, timeout is not needed
    # sock.settimeout(20)

    # Start listening for connections
    sock.bind((socket.gethostbyname(socket.gethostname()), connection_info["server_port"]))
    
    # Allowing a queue of 10 connections
    sock.listen(10)

    return sock
        

def execute_server(server: socket.socket, clientsocket: socket.socket, order: int, pid: int) -> None:
    """
    Processes the whole flow of the server for a client connection. Every forked child process is ran through this.

    Args:
        server: socket object that is listening on server port
        clientsocker: socker object returned when connection was accepted
        order: the index of the child process from main
        pid: the process id of current process
    """
    # If number of child processes > 0, append [order][pid] before every print statement
    # If client has been authenticated in the session
    authenticated = False

     # Sending setup message
    sent = "220 Service ready\r\n"
    print(f"S: {sent}", end='', flush=True)
    clientsocket.send(sent.encode())
    ehlo_done = False
    while True:
        # EHLO command
        received = clientsocket.recv(1024).decode('ascii')
        if not received:
            print("S: Connection lost\r\n", end="", flush=True)
            break
        print(f"C: {received}", end='', flush=True)
        arr = received.strip().split(' ')
        if received[:4] == "EHLO": # EHLO command
            ehlo_command(clientsocket, arr, received)
            ehlo_done = True
        elif received[:4] == "AUTH":
            if received == "AUTH CRAM-MD5\r\n":
                if not authenticated:
                    if auth_command(clientsocket):
                        authenticated = True
                else:
                    sent = "503 Bad sequence of commands\r\n"
                    print(server_print(sent), end='', flush=True)
                    clientsocket.send(sent.encode())
            elif received[-2:] == "\r\n":
                sent = "504 Unrecognized authentication type\r\n"
                print(server_print(sent), end='', flush=True)
                clientsocket.send(sent.encode())
        elif received[:4] == "MAIL" and ehlo_done:
            response = mail_command(clientsocket, arr, received, authenticated)
            if response not in ('success', 'failure'):
                if quit_command(clientsocket, response.strip().split(' '), response):
                    break
        elif received == "RSET\r\n":
            sent = "250 Requested mail action okay completed\r\n"
            print(server_print(sent), end='', flush=True)
            clientsocket.send(sent.encode())
        elif received[:4] == "NOOP":
            if received == "NOOP\r\n":
                sent = "250 Requested mail action okay completed\r\n"
                print(server_print(sent), end="", flush=True)
                clientsocket.send(sent.encode())
            else:
                sent = "501 Syntax error in parameters or arguments\r\n"
                print(server_print(sent), end="", flush=True)
                clientsocket.send(sent.encode())
            continue
        elif received[:4] == "QUIT": # QUIT command
            if(quit_command(clientsocket, arr, received)):
                break
        # elif received == "DATA\r\n": # command out of sequence
        else:
            sent = "503 Bad sequence of commands\r\n"
            print(server_print(sent), end='', flush=True)
            clientsocket.send(sent.encode())

    clients.remove(clientsocket)
    clientsocket.close()


def handler(signal_received, frame):
    # Handle any cleanup here
    if len(children) > 1:
        print('S: SIGINT received, closing\r\n', end='', flush=True)
    for client in clients:
        client.close()
    # for pid in children:
    #     os.kill(pid, signal.SIGINT)
    exit(0)

clients = []
"""Global list of all open client connections."""
children = []
"""Global list of PIDs of all child processes created by fork."""

def main():
    """Main method of the program, runs the whole thing."""
    server = setup_server_socket()
    signal.signal(signal.SIGINT, handler)

    i = 0
    while i <= 10:
        client, addr = server.accept()
        clients.append(client)
        child_pid=os.fork()
        if child_pid == 0:
            children.append(os.getpid())
            execute_server(server, client, i, os.getpid())
            os.kill(os.getpid(), signal.SIGINT)
            # kill –s ABRT pid
            break
        else:
            i += 1

if __name__ == '__main__':
    main()
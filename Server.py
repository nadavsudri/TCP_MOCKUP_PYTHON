import json
import socket,json
import random

"""I would oop this way better but its not necessary"""
## connecting a socket to given ip and port
def listener_connection(ip, port)->socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((ip, port))
    sock.listen()
    return sock

## sending window size limitations
def response(socket:socket.socket,file:str, size:int = 1024,win_size = 4,timeout=4,dynamic:bool = False ):
    response = {"message":file,"maximum_msg_size":size,"window_size":win_size,"timeout":timeout,"dynamic_msg_size":dynamic}
    socket.send(json.dumps(response).encode())

## checks if a file's content is of valid format
def is_format(data:str) -> bool:
    pass

### Receiving the first confing request
def receive_config_request(client_socket):

    ## get the request from the socket
    # convert it to JSON
    config_request = client_socket.recv(1024).decode()
    config_request = json.loads(config_request)

    ## distinguish the types of request (from text or file)
    if config_request["type"] == "F" or config_request["type"] == "f":
        # if passed using a file
        response = open_file_json(input("Please enter the file path: "))
        client_socket.send(response.encode())
        return json.loads(response)
    if config_request["type"] == "T" or config_request["type"] == "t":

        ## requesting from user for parameters
        message_file = input("Please enter the file path: ")
        msg_size = input("Please enter the message size: ")
        window_size = input("Please enter the window size: ")
        timeout = input("Please enter the timeout: ")
        dynamic_msg_size = input("Please enter the dynamic message size [T/F]: ")
        dynamic_msg_size = True if dynamic_msg_size == "T" or dynamic_msg_size=="t" else False

        ## assembling the dictionary response
        conf = {"message": message_file, "maximum_msg_size":int(msg_size), "window_size": int(window_size), "timeout": int(timeout),
                "dynamic_message_size": dynamic_msg_size}
        ## send response JSON
        client_socket.send(json.dumps(conf).encode())
        return conf
    return None

def random_size():
    return random.randint(1,8)

### receive a message from the client
def receive_message(client_socket):
    pass

## opening a file containing JSON format
def open_file_json(file:str):
    with open(file) as f:
        data=  f.read()
        return json.dumps(data)

#sending ack for a given sequence
def send_ack(socket:socket.socket,ack:int,dynamic:bool = False):
    if dynamic:
        ack_msg = json.dumps({"ack":ack,"dynamic_message_size":True,"message_size":random_size()})
    else:
        ack_msg = json.dumps({"ack":ack,"dynamic_message_size":False})
    socket.send(ack_msg.encode()+b"\n")

#reciving message
def recv_msg(socket:socket.socket,config):
    buffer = b""
    message = ""
    while True:
        buffer += socket.recv(4096)

        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            data = json.loads(line.decode())
            msg = data["message"]
            seq = data["seq"]
            is_last = data["is_last"]
            message += msg
            print("got message:", msg)
            send_ack(socket, seq,config["dynamic_message_size"])
            print("sending ack",seq)

            if is_last:
                print("last arrived")
                return message

def main():

    # accept connection via 3 way handshake
    listener_sock = listener_connection("127.0.0.1", 5555)

    #open and accept socket
    client_socket, client_address = listener_sock.accept()
    print("Client connected", client_address)

    #Atemppting to make 3-way handshake
    is_connected = False
    while not is_connected:
        data = client_socket.recv(1024).decode()
        if data =="SIN":
            client_socket.send("SIN/ACK".encode())
            data = client_socket.recv(1024).decode()
            if data == "ACK":
                is_connected = True
                break
        print("Connection failed, Retrying...")

    config =receive_config_request(client_socket)

    #printing when connected
    print("Connected", is_connected)

    #loop as long connection is established
    while is_connected:
        data = recv_msg(client_socket,config)
        if not data:
                continue
        # if data =="WIN_SIZE":
                # response(client_socket,)#incomplete!!
        print("Received: ", data)

main()
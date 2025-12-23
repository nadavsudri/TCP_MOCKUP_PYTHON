import json
import socket
import sys
import time
from collections import deque


## start of connection (3way handshake)
def start_connection(socket:socket.socket,port=5555,ip="127.0.0.1"):
    socket.connect((ip, port))
    socket.send("SIN".encode()) # send SIN
    data_rcv = socket.recv(1024).decode()
    if data_rcv == "SIN/ACK": # Recive SIN / ACK
        socket.send("ACK".encode()) # Send last Ack
    return True # return true to verify an establishment.

recv_buffer = b""
def recv_json(sock):
    global recv_buffer
    while b"\n" not in recv_buffer:
        recv_buffer += sock.recv(4096)

    line, recv_buffer = recv_buffer.split(b"\n", 1)
    return json.loads(line.decode())

## send request for window size (only after handshake)
def ask_for_config(socket:socket.socket, source):
    #send the request with source
    request = {"request":"config","type":source}
    socket.send(json.dumps(request).encode())
    data_rcv = socket.recv(1024).decode()
    print("RAW FROM SERVER:", json.loads(data_rcv.rstrip("\n")))
    data_rcv = json.loads(data_rcv)
    ##if the data is wrapped twice
    if isinstance(data_rcv, str):
        data_rcv = json.loads(data_rcv)
    return data_rcv

#segmenting the data by @num sizes (len//maxmsgsize)
def segment_msg(data: str, max_len: int):
    return [data[i:i+max_len] for i in range(0, len(data), max_len)]

def send_indexed(socket:socket.socket,str:str,index:int):
    data = {"data":str,"index":index}

def add_headers(source:bytes,m,is_last:bool):
    """
    add the headres to a given string
    :param source: 
    :param m: 
    :param is_last: 
    :return: bytes
    """""
    msg_with_headers = {"message":source.decode(),"seq":m,"is_last":is_last}
    return json.dumps(msg_with_headers).encode("utf-8")

#handels sending a non-dynamic window size message

def send_message(socket:socket.socket,source:str,config:dict):
    ##this method is the main implementation of the reliable data transform mechanism
    ##as studied in RESHATOT TIKSHORET course.

    #don't do anything if no data was sent
    if not source:
        return

    ## extracting config data from the config dictionary
    max_len = config["maximum_msg_size"]
    window_size = config["window_size"]
    timeout = config["timeout"]
    dynamic = config["dynamic_message_size"]

    #encode the data
    encoded_data = source.encode("utf-8")
    #initiallize parameters for the function
    last_sent = 0
    last_ack = 0
    bytes_sent = 0
    new_size = False
    pending_size = None
    window=[]
    timer = time.time()

    #the main loop of the method
    while True:
        #send the unsent packets in the window
        first = True
        while last_sent-last_ack < window_size and not new_size:
            ##if the given size is new -> don't send new messages
            if bytes_sent >= len(encoded_data):
                break

            ## if the message sent is the first one after a message size has been changed,
            ## the idea is to stop the stream until the window is fully sent
            if first:
                timer = time.time()
                first = False

            ## use chunking and "buffer" to separate the data
            chunk = encoded_data[bytes_sent : bytes_sent + max_len]

            ##send the data with a flag saying the segment is the last one
            ## adding the headres to the packet
            if bytes_sent+len(chunk) ==len(encoded_data):
                to_send =  add_headers(chunk, last_sent, True)
            else:
                to_send = add_headers(chunk, last_sent, False)

            ## appending the sent message to a window
            window.append(to_send)
            ## sending the message via the socket
            socket.send(to_send+b"\n")
            #updating the total bytes_sent
            bytes_sent += len(chunk)
            last_sent += 1

        ### if the message sent completly -> return
        if bytes_sent == len(encoded_data) and last_ack == last_sent:
            print("Finished")
            return
        #get the responses
        res = recv_json(socket)
        ack = res["ack"]

        if ack == 5:
            print("")

        print("Ack: ", ack)

        #  if the response from the server included the flag, change the msg size
        if res["dynamic_message_size"]:
            dynamic = res["dynamic_message_size"]
            if max_len != res["message_size"]:
                new_size = True
                # saving the new size for when the window is empty
                pending_size = res["message_size"]
        if last_ack == last_sent:
            new_size = False


        #if the received ack is biggest, then the last acked packet -> move the window
        if ack>last_ack-1:
            last_ack = ack+1
            window = [pkt for pkt in window if json.loads(pkt.decode())["seq"] >= last_ack]
            timer = time.time()

        ##if the new size flag is true (new size has been asked for)
        ##and the window is empty, change the sizeing and set the flags to false.
        if new_size and last_ack == last_sent:
            max_len = pending_size
            new_size = False
            pending_size = None
            continue

        ## if you haven't received a moving window ack till timeout -> resend the window
        ## after the retransmitting, the clock is set to 0 again
        time.sleep(timeout + 1)
        if time.time() - timer > timeout:
            print("im looking for timeout")
            for unsacked in window:
                socket.send(unsacked+b"\n")
            timer = time.time()


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    start_connection(sock)
    work_type =input("File or Type [F/T] >>>  ")
    config = ask_for_config(sock, work_type)
    while True:
        data = input("> ")
        send_message(sock,data,config)

if __name__ == "__main__":
    main()

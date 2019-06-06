import socket
import os
import sys
import time
import _thread
from timer import Timer
import random
import hashlib
    
# Set address and port
serverAddress = "pear.cs.umass.edu"
serverPort = 8888
SENDER_ADDR = (serverAddress, serverPort)

WINDOW_SIZE = 10
WAIT_INTERVAL = 0.05
TIMEOUT_DURATION = 0.5

BUFFER_SIZE = 2048
SEQ_SIZE = 4
HASH_SIZE = 56
PACKET_SIZE = 1988
#Packet Length specify the size of the whole packet include header 2048 B
PACKET_LENGTH = PACKET_SIZE + SEQ_SIZE + HASH_SIZE

filename1 = ''    # read file
filename2 = ''    #  write file

# NAME
NAME_SENDER = b'sender'
NAME_REC = b'reciever'

# global 
base = 0
ack_thread = _thread.allocate_lock()

#set timeout duration for timer
timer = Timer(TIMEOUT_DURATION)

# extract the packet 
def packet_unpack(data):
    # bytes from 0 to HASH_SIZE-1: checksum
    checksum = data[:HASH_SIZE]
    # byts from HASH_SIZE to SEQ_SIZE + HASH_SIZE-1: sequence number
    # remaim bytes are data
    seq_num = int.from_bytes(data[HASH_SIZE: SEQ_SIZE + HASH_SIZE], byteorder = 'little', signed = True)
    
    return checksum, seq_num, data[SEQ_SIZE+HASH_SIZE:]

# each packet cantains checksum + seq + data
def packet_build(seq_num, data = b''):
    message = seq_num.to_bytes(SEQ_SIZE, byteorder = 'little', signed = True) + data
    checksum = hash(message)
    return checksum + message

def hash(message):
    return hashlib.sha224(message).hexdigest().encode('utf-8') 

def connect(sock):
    data = b''
    message = b'NAME ' + NAME_SENDER
    while b'OK' not in data: 
        sent = sock.sendto(message, SENDER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)
    
    data = b''
    message = b'LIST'
    while NAME_REC not in data:
        # print(data)
        sent = sock.sendto(message, SENDER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)
    
    data = b''
    message = b'CONN ' + NAME_REC
    while b'OK' not in data and NAME_REC not in data:  
        sent = sock.sendto(message, SENDER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)

# get window size
def get_window_size(num_packets):
    global base
    # in case the number of remaining packets is less than the size of windows
    return min(WINDOW_SIZE, num_packets - base)

def sender(sock, filename):
    global base
    global timer
    global ack_thread

    # open the file
    try:
        file = open(filename1, 'rb')
    except IOError:
        print('Fail to open the file', filename1)
        return
    
    # load file and make packets in buffer
    packets = []
    seq_num = 0
    while True:
        # first packet is for indicating the file name
        if (seq_num == 0):
            data = filename2.encode() 
            packets.append(packet_build(seq_num,data))
            seq_num = seq_num + 1
        else:  
            data = file.read(PACKET_SIZE)
            if not data:
                break
            packets.append(packet_build(seq_num,data))
            seq_num = seq_num + 1
           
    file.close()
   
    # connect to receiver
    connect(sock)
    print('connected to reciever')

    # number of packets
    num_packets = len(packets)
    pkt_send_next = 0
    base = 0
    window_size = get_window_size(num_packets)

    # receiver ack thread
    _thread.start_new_thread(ack_receiver, (sock,))

    # until send all packets
    while base < num_packets:
        # blocks until a call to release()
        ack_thread.acquire()
        # send every packets in the window 
        while pkt_send_next < base + window_size:
            # print(len(packets[pkt_send_next]))
            sock.sendto(packets[pkt_send_next],SENDER_ADDR)
            print('Sent packet', pkt_send_next)
            pkt_send_next = pkt_send_next + 1

        # Start the timer
        if not timer.running():
            print('start timer')
            timer.start()

        # wait to get ack or timeout
        while timer.running() and not timer.timeout():
            #  set the state to unlocked and returns immediately
            ack_thread.release()
            print('waiting for ACK')
            time.sleep(WAIT_INTERVAL)
            ack_thread.acquire()

        if timer.timeout():
            # timed out
            print('timeout')
            # stop the timer 
            timer.stop()
            pkt_send_next = base
        else:
            window_size = get_window_size(num_packets)
            print('shifted window to: %d-%d' %(base,base+window_size))
        ack_thread.release()

    # send empty data, tell the receiver that it received entire the file  
    sock.sendto(b'', SENDER_ADDR)
    sock.sendto(b'', SENDER_ADDR)
    sock.sendto(b'', SENDER_ADDR)

    # quit from the server
    sent = sock.sendto(b'.', SENDER_ADDR)
    sent = sock.sendto(b'QUIT', SENDER_ADDR)
    sock.close()

# receive ack thread
def ack_receiver(sock):
    global base
    global timer
    global ack_thread

    while True:
        # recieve packet which contains ack from the receiver
        pkt, _ = sock.recvfrom(BUFFER_SIZE)

        checksum, ack, data = packet_unpack(pkt)
        message = ack.to_bytes(SEQ_SIZE, byteorder = 'little', signed = True) + data
        # if it got an good ACK which it is not corrupted
        if (hash(message)== checksum):
            print('received ACK', ack)
            if (ack >= base):
                ack_thread.acquire()
                new_base = ack + 1
                base = new_base
                print('updated base', base)
                # stop timer
                timer.stop()
                ack_thread.release()
        else: print('bad ACK')

def main():
    global serverAddress, serverPort,filename1,filename2
    print(len(sys.argv))
    try:
        if (len(sys.argv) != 8):
            raise Exception

        if ('plum' in sys.argv[2]):
            serverAddress = 'plum.cs.umass.edu'
        
        if ('pear' in sys.argv[2]):
            serverAddress = 'pear.cs.umass.edu'
        
        if (sys.argv[4].isdigit()):
            serverPort = sys.argv[4]
        else:          
            raise Exception

        if ('-t' in sys.argv[5]):
            filename1 = sys.argv[6]
            filename2 = sys.argv[7]
        
        print(serverAddress)
    
    except:
        print("Please enter valid arguments, Example:")
        print("\"python3 ChatClientSender.py -s plum -p 8888 -t testfile1 testfile2\"")
        print("\"python3 ChatClientSender.py -s pear -p 8888 -t testfile1 testfile2\"")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender(sock,filename1)
    sock.close()


if __name__ == '__main__':
    main()

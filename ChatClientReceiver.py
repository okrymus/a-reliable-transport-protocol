import socket
import os
import hashlib


# Set address and port
serverAddress = "pear.cs.umass.edu"
serverPort = 8888
RECEIVER_ADDR = (serverAddress, serverPort)

SEQ_SIZE = 4
HASH_SIZE = 56
PACKET_SIZE = 1988

filename2 = 'output.txt'
NAME_SENDER = b'sender'
NAME_REC = b'reciever'
BUFFER_SIZE = 2048

def packet_unpack(data):
    checksum = data[:HASH_SIZE]
    seq_num = int.from_bytes(data[HASH_SIZE:SEQ_SIZE+HASH_SIZE], byteorder = 'little', signed = True)
    return checksum, seq_num, data[SEQ_SIZE+HASH_SIZE:]

def packet_build(seq_num, data = b''):
    message = seq_num.to_bytes(SEQ_SIZE, byteorder = 'little', signed = True) + data
    checksum = hash(message)
    # print(checksum.encode())
    return checksum + message

def hash(message):
    return hashlib.sha224(message).hexdigest().encode('utf-8') 

def connect(sock):
    data = b''
    message = b'NAME ' + NAME_REC
    while b'OK' not in data: 
        sent = sock.sendto(message, RECEIVER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)
    
    data = b''
    message = b'LIST'
    while NAME_SENDER not in data:
        sent = sock.sendto(message, RECEIVER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)
    
    data = b''
    message = b'CONN ' + NAME_SENDER
    while b'OK' not in data and NAME_SENDER not in data:  
        sent = sock.sendto(message, RECEIVER_ADDR)
        data, server = sock.recvfrom(BUFFER_SIZE)  

def reciever(sock):
    # connect to sender
    connect(sock)
    print('connected to sender')
    
    expected_pkt = 0
    while True:
        # receive packet
        pkt, _ = sock.recvfrom(BUFFER_SIZE)
        if not pkt:
            print(len(pkt))
            break
        
        # print(len(pkt))
        checksum, seq_num, data = packet_unpack(pkt)
        message = seq_num.to_bytes(SEQ_SIZE, byteorder = 'little', signed = True) + data
        # check that no corrupted in data
        if (hash(message) == checksum):
            if seq_num == expected_pkt:
                print('received expected packet')
                pkt = packet_build(expected_pkt)
                sock.sendto(pkt,RECEIVER_ADDR)
                expected_pkt += 1
                if(seq_num != 0):
                    file.write(data)
                else:
                    # open the file to write
                    # the filename is given by the sender in the first packet
                    try:
                        print(data.decode('utf-8'))
                        file = open(data.decode('utf-8'), 'wb')
                    except IOError:
                        print('Unable to open', data.decode)
                        return
            else:
                # send ack to the sender
                pkt = packet_build(expected_pkt-1)
                sock.sendto(pkt,RECEIVER_ADDR)
                print('sent ACK', expected_pkt - 1)

        else: print('bad packet')
    
    file.close()

    sent = sock.sendto(b'.', RECEIVER_ADDR)
    sent = sock.sendto(b'QUIT', RECEIVER_ADDR)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    reciever(sock)
    sock.close()


if __name__ == '__main__':
    main()


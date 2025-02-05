import sys
import socket
import selectors
import types
import logging
import os
import time

# log to a file
log_file = 'server.log'
# if the file does not exist in the current directory, create it
if not os.path.exists(log_file):
    with open(log_file, 'w') as f:
        pass
logging.basicConfig(filename=log_file, level=logging.INFO)

sel = selectors.DefaultSelector()

host, port = sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
logging.info("Listening on %s:%d at %s", host, port, time.strftime("%Y-%m-%d %H:%M:%S"))
lsock.setblocking(False)
sel.register(lsock, selectors.EVENT_READ, data=None)

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    logging.info("Accepted connection from %s at %s", addr, time.strftime("%Y-%m-%d %H:%M:%S"))
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)

def service_connection(key, mask):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(4096)  # Should be ready to read
        if recv_data:
            data.outb += recv_data
        else:
            logging.info('Closing connection to %s at %s', data.addr, time.strftime("%Y-%m-%d %H:%M:%S"))
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            logging.info("Echoing %r to %s at %s", data.outb, data.addr, time.strftime("%Y-%m-%d %H:%M:%S"))
            sent = sock.send(b'Message Received')  # Should be ready to write
            data.outb = data.outb[sent:]


try:
    while True:
        events = sel.select(timeout=None)
        for key, mask in events:
            if key.data is None:
                accept_wrapper(key.fileobj)
            else:
                service_connection(key, mask)
                
except KeyboardInterrupt:
    logging.error("KeyboardInterrupt, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
finally:
    sel.close()
import sys
import socket
import selectors
import types
import threading

if len(sys.argv) != 3:
    print("Usage: python client.py <host> <port>")
    sys.exit(1)
host = sys.argv[1]
port = int(sys.argv[2])

sel = selectors.DefaultSelector()


def start_connection(
                    host: str,
                    port: int,
                    selector: selectors.DefaultSelector
                    ) -> tuple[socket.socket, types.SimpleNamespace]:
    '''
    Start a connection to the server.

    Parameters
    ----------
    host : str
        The host to connect to.
    port : int
        The port to connect to.
    selector : selectors.DefaultSelector
        Where to register the connection.
    '''

    # Create a socket and connect to the server.
    server_addr = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    try:
        sock.connect_ex(server_addr)
    except Exception as e:
        print("Connection error:", e)
        sys.exit(1)
    
    # Register the socket with the selector to send events.
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    data = types.SimpleNamespace(addr=server_addr, inb=b"", outb=b"")
    selector.register(sock, events, data=data)
    return sock, data

def service_connection(key, mask):
    '''
    Service a connection.

    Parameters
    key : selectors.SelectorKey
        The key for the connection.
    mask : int
        The mask of events that occurred on the connection.
    '''
    # ge the socket
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(4096)
        if recv_data:
            print("Received:", recv_data.decode())
        else:
            print("Closing connection to", data.addr)
            sel.unregister(sock)
            sock.close()
    if mask & selectors.EVENT_WRITE and data.outb:
        sent = sock.send(data.outb)
        data.outb = data.outb[sent:]

def event_loop():
    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                service_connection(key, mask)
    except KeyboardInterrupt:
        print("Interrupted, exiting")
    finally:
        sel.close()

conn, conn_data = start_connection(host, port, sel)
threading.Thread(target=event_loop, daemon=True).start()

# Read user input from the command line and send to server.
try:
    while True:
        msg = input("Enter message to send (or empty to quit): ")
        if not msg:  # Exit if no message is entered.
            print("Exiting input loop.")
            break
        # Append the encoded message to outb.
        conn_data.outb += msg.encode()
except KeyboardInterrupt:
    print("Input interrupted, exiting")
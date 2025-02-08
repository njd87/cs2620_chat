import sys
import socket
import selectors
import types
import logging
import os
import time
import sqlite3
from comm_server import Bolt

# log to a file
log_file = 'logs/server.log'
db_file = 'data/messenger.db'

# if the file does not exist in the current directory, create it
if not os.path.exists(log_file):
    with open(log_file, 'w') as f:
        pass


logging.basicConfig(
    filename=log_file, 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def setup():
    '''
    Set up the server.
    '''
    global sel, log_file

    # check if the log file exists
    if not os.path.exists(log_file):
        logging.error("Log file does not exist, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        sys.exit(1)

    # check if the database file exists
    if not os.path.exists(db_file):
        logging.error("Database file does not exist, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
        sys.exit(1)

    # create basic selector
    sel = selectors.DefaultSelector()

    # check arguments for host and port
    host, port = sys.argv[1], int(sys.argv[2])

    # set up socket
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((host, port))
    lsock.listen()
    logging.info("Listening on %s:%d at %s", host, port, time.strftime("%Y-%m-%d %H:%M:%S"))
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)

def accept_wrapper(sock: socket.socket) -> None:
    '''
    Accept a connection and register it with the selector.

    Parameters
    ----------
    sock : socket.socket
        The socket to accept a connection on.
    '''
    conn, addr = sock.accept()
    logging.info("Accepted connection from %s at %s", addr, time.strftime("%Y-%m-%d %H:%M:%S"))
    conn.setblocking(False)

    # register the connection with the selector
    data = Bolt(sel=sel, sock=conn, addr=addr)
    sel.register(conn, selectors.EVENT_READ, data=data)

def main_loop() -> None:
    '''
    Main loop for the server.
    '''
    try:
        while True:
            # listen for events
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    try:
                        key.data.process_events(mask)
                    except Exception as e:
                        # If the connection is closed by the peer, log and clean up without breaking the loop.
                        logging.info("Connection closed by peer: %s at %s", key.fileobj, time.strftime("%Y-%m-%d %H:%M:%S"))
                        try:
                            sel.unregister(key.fileobj)
                        except Exception:
                            pass
                        try:
                            key.fileobj.close()
                        except Exception:
                            pass
            # Continue looping for new connections
    except KeyboardInterrupt:
        logging.error("KeyboardInterrupt, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S"))
    finally:
        sel.close()
        sys.exit(0)


if __name__ == "__main__":
    setup()
    main_loop()
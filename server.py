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
log_file = "logs/server.log"
db_file = "data/messenger.db"

# if the file does not exist in the current directory, create it
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        pass


logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def setup():
    """
    Set up the server.
    """
    global sel, log_file

    # check if the log file exists
    if not os.path.exists(log_file):
        logging.error(
            "Log file does not exist, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S")
        )
        sys.exit(1)

    # check if the database file exists
    if not os.path.exists(db_file):
        logging.error(
            "Database file does not exist, exiting at %s",
            time.strftime("%Y-%m-%d %H:%M:%S"),
        )
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
    logging.info(
        "Listening on %s:%d at %s", host, port, time.strftime("%Y-%m-%d %H:%M:%S")
    )
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)


def accept_wrapper(sock: socket.socket) -> None:
    """
    Accept a connection and register it with the selector.

    Parameters
    ----------
    sock : socket.socket
        The socket to accept a connection on.
    """
    conn, addr = sock.accept()
    logging.info(
        "Accepted connection from %s at %s", addr, time.strftime("%Y-%m-%d %H:%M:%S")
    )
    conn.setblocking(False)

    # register the connection with the selector
    data = Bolt(sel=sel, sock=conn, addr=addr)
    sel.register(conn, selectors.EVENT_READ, data=data)


def main_loop() -> None:
    """
    Main loop for the server.
    """
    try:
        connected_users = {}
        while True:
            # listen for events
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    try:
                        # back to server contains information a bolt might want to communicate back to the main server
                        back_to_server = key.data.process_events(mask)
                        if back_to_server:
                            if "new_user" in back_to_server:
                                logging.info(
                                    "New user %s at %s",
                                    back_to_server["new_user"],
                                    time.strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                connected_users[back_to_server["new_user"]] = {
                                    "socket" : key.fileobj,
                                    "bolt" : key.data
                                }
                                logging.info("Connected users: %s", connected_users)
                            elif "new_message" in back_to_server:
                                print("HEEEERRRRREEEEE")
                                logging.info(
                                    "Message from %s to %s at %s",
                                    back_to_server["new_message"]["sender"],
                                    back_to_server["new_message"]["recipient"],
                                    time.strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                print("HEEEERRRRREEEEE2")
                                # TODO: let recipient know they have a message if they are connected
                                if back_to_server["new_message"]["recipient"] in connected_users:
                                    connected_users[back_to_server["new_message"]["recipient"]]["bolt"].create_response(new_message=back_to_server["new_message"]["sent_message"])
                                    connected_users[back_to_server["new_message"]["recipient"]]["bolt"].write()
                                    print("HEEEERRRRREEEEE3")
                    except Exception as e:
                        # If the connection is closed by the peer, log and clean up without breaking the loop.
                        logging.error(
                            "Connection closed by peer: %s at %s",
                            key.fileobj,
                            time.strftime("%Y-%m-%d %H:%M:%S")
                        )
                        logging.error("Exception: %s", e)
                        try:
                            sel.unregister(key.fileobj)

                            # remove user from connected users
                            for user in connected_users:
                                if connected_users[user] == key.fileobj:
                                    logging.info(
                                        "Removing user %s at %s",
                                        user,
                                        time.strftime("%Y-%m-%d %H:%M:%S"),
                                    )
                                    del connected_users[user]

                            logging.info("Connected users: %s", connected_users)
                        except Exception:
                            pass
                        try:
                            key.fileobj.close()
                        except Exception:
                            pass
            # Continue looping for new connections
    except KeyboardInterrupt:
        logging.error(
            "KeyboardInterrupt, exiting at %s", time.strftime("%Y-%m-%d %H:%M:%S")
        )
    finally:
        sel.close()
        sys.exit(0)


if __name__ == "__main__":
    setup()
    main_loop()

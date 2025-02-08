import sys
import socket
import selectors
import types
import threading
import tkinter as tk
from comm_client import Bolt

sel = selectors.DefaultSelector()

class ClientUI:
    def __init__(self, host, port):
        self.root = tk.Tk()
        self.root.title("Messenger")
        self.root.geometry("400x400")

        # start connection
        self.conn, self.conn_data = start_connection(host, port)
        threading.Thread(target=event_loop, daemon=True).start()

        self.setup_register()

        self.root.mainloop()
        
    def send_register_request(self, username, password):
        # create a request
        self.conn_data.request = {
            "action": "register",
            "username": username,
            "passhash": password,
            "encoding": "utf-8"
        }

    def setup_register(self):
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack()
        self.login_label = tk.Label(self.login_frame, text="Enter your username:")
        self.login_label.pack()
        self.login_entry = tk.Entry(self.login_frame)
        self.login_entry.pack()
        self.login_password_label = tk.Label(self.login_frame, text="Enter your password:")
        self.login_password_label.pack()
        self.login_password_entry = tk.Entry(self.login_frame)
        self.login_password_entry.pack()
        self.login_button = tk.Button(self.login_frame, text="Register", command=lambda: self.send_register_request(self.login_entry.get(), self.login_password_entry.get()))
        self.login_button.pack()



    def setup_main(self):
        '''
        Main is set up into 3 components.

        On the left side is a list of all available users.
        - This is a listbox that is populated with all users.
        - There are buttons on the bottom for "Prev" and "Next" to scroll through the list.

        In the middle is the chat window.
        - This is a text widget that displays the chat history.
        - It is read-only.

        On the right side is the chat entry and settings.
        - It has a text entry for typing messages and a button under that says "send".
        - There is a button that says "Settings" at the bottom opens a new window.
        '''

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack()

        self.users_frame = tk.Frame(self.main_frame)
        self.users_frame.pack(side=tk.LEFT)
        self.users_label = tk.Label(self.users_frame, text="Users")
        self.users_label.pack()
        self.users_listbox = tk.Listbox(self.users_frame)
        self.users_listbox.pack()
        self.users_prev_button = tk.Button(self.users_frame, text="Prev")
        self.users_prev_button.pack(side=tk.LEFT)
        self.users_next_button = tk.Button(self.users_frame, text="Next")
        self.users_next_button.pack(side=tk.RIGHT)

        self.chat_frame = tk.Frame(self.main_frame)
        self.chat_frame.pack(side=tk.TOP)
        self.chat_text = tk.Text(self.chat_frame)
        self.chat_text.pack()

        self.chat_entry_frame = tk.Frame(self.main_frame)
        self.chat_entry_frame.pack(side=tk.RIGHT)
        self.chat_entry = tk.Entry(self.chat_entry_frame)
        self.chat_entry.pack()
        self.send_button = tk.Button(self.chat_entry_frame, text="Send")
        self.send_button.pack()
        self.settings_button = tk.Button(self.chat_entry_frame, text="Settings")
        self.settings_button.pack()

    def setup_delete(self):
        self.delete_frame = tk.Frame(self.root)
        self.delete_frame.pack()
        self.delete_label = tk.Label(self.delete_frame, text="Are you sure you want to delete your account?\n(Enter account details to confirm)")
        self.delete_label.pack()

        self.confirm_username_label = tk.Label(self.delete_frame, text="Enter your username:")
        self.confirm_username_label.pack()

        self.confirm_username_entry = tk.Entry(self.delete_frame)
        self.confirm_username_entry.pack()

        self.confirm_password_label = tk.Label(self.delete_frame, text="Enter your password:")
        self.confirm_password_label.pack()

        self.confirm_password_entry = tk.Entry(self.delete_frame)
        self.confirm_password_entry.pack()

        self.delete_button = tk.Button(self.delete_frame, text="Delete")
        self.delete_button.pack()
        self.cancel_button = tk.Button(self.delete_frame, text="Cancel")
        self.cancel_button.pack()


def start_connection(
                    host: str,
                    port: int
                    ) -> tuple[socket.socket, types.SimpleNamespace]:
    '''
    Start a connection to the server.
    Most of this code is from lecture notes.

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
    data = Bolt(sel=sel, sock=sock, addr=server_addr)
    sel.register(sock, events, data=data)
    return sock, data

def event_loop():
    try:
        while True:
            events = sel.select(timeout=1)
            for key, mask in events:
                if key.data:
                    key.data.process_events(mask)
    except KeyboardInterrupt:
        print("Interrupted, exiting")
    finally:
        sel.close()

if len(sys.argv) != 3:
    print("Usage: python client.py <host> <port>")
    sys.exit(1)

host = sys.argv[1]
port = int(sys.argv[2])

if __name__ == "__main__":
    client_ui = ClientUI(host, port)
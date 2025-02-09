import sys
import socket
import selectors
import types
import threading
import tkinter as tk
from comm_client import Bolt

sel = selectors.DefaultSelector()


class ClientUI:
    """
    The client UI for the messenger.

    The client UI is a tkinter application that has a few different states:
    - User Entry
    - Login
    - Register
    - Main
    - Delete

    The user entry is the first screen that asks for a username.
    The login screen asks for a username and password.
    The register screen asks for a username and password.

    The main screen has a list of users, a chat window, and a chat entry.

    The delete screen asks for a username and password to confirm deletion.

    The client UI is responsible for sending requests to the server and processing responses.

    Parameters
    ----------
    host : str
        The host to connect to.
    port : int
        The port to connect to.
    """

    def __init__(self, host, port):
        """
        Initialize the client UI.
        """
        self.root = tk.Tk()
        self.root.title("Messenger")
        self.root.geometry("1200x1200")

        self.credentials = None

        # start connection
        # MUST be run in separate thread
        self.conn, self.conn_data = start_connection(host, port)
        threading.Thread(target=event_loop, daemon=True).start()

        # setup first screen
        self.setup_user_entry()

        # these are variables that are used to store data from the server

        # online users
        self.users = []

        # current messages in conversation
        self.loaded_messages = []

        # incoming pings
        self.incoming_pings = []

        # undelivered messages
        self.undelivered_messages = []
        self.n_undelivered = 0

        # user that is currently being messaged
        self.connected_to = None

        # run the tkinter main loop
        self.root.mainloop()


    """
    Functions starting with "check_" are used to check for responses from the server.
    These are to be run when in different states of the tkinter window.

    Once a response is received, the response is processed and the window is updated accordingly.
    Then, the function "returns" to make sure it doesn't keep looking for the response.
    """

    def check_user_entry_response(self):
        """
        Check for a response to the user entry.
        Sends request to check if the username exists.
        """
        if self.conn_data.response:
            # no matter what, we destroy the user entry screen
            self.destroy_user_entry()
            # username exists, send to login
            if self.conn_data.response["result"]:
                self.conn_data.response = None
                self.setup_login()
                return
            # username does not exist, send to register
            else:
                self.conn_data.response = None
                self.setup_register()
                return

        self.root.after(100, self.check_user_entry_response)

    def check_login_response(self):
        """
        Check for a response to the login.
        Deals with logic of when login has correct and incorrect credentials.
        """
        if self.conn_data.response:
            # logged in successfully - passhash matches
            if self.conn_data.response["result"]:
                self.users = self.conn_data.response["users"]
                self.n_undelivered = self.conn_data.response["n_undelivered"]
                self.conn_data.response = None
                self.credentials = self.login_entry.get()
                self.login_frame.destroy()
                self.setup_undelivered()
                return
            # login failed, incorrect username/password
            else:
                self.conn_data.response = None
                self.login_failed_label.pack()
                self.login_frame.destroy()
                self.setup_login()
                return

        self.root.after(100, self.check_login_response)

    def check_register_response(self):
        """
        Check for a response to the register.
        If the username already exists, show a label.
        If the passwords do not match, show a label.

        Otherwise, move to the main screen.
        """
        if self.conn_data.response:
            if self.conn_data.response["result"]:
                self.users = self.conn_data.response["users"]
                self.conn_data.response = None
                self.credentials = self.register_entry.get()
                self.register_frame.destroy()
                self.setup_main()
                return
            else:
                self.conn_data.response = None
                self.register_username_exists_label.pack()
                self.register_passwords_do_not_match_label.forget_pack()
                return

        self.root.after(100, self.check_register_response)

    def check_load_chat_request(self):
        """
        Check for a response to the load chat request.
        """
        if self.conn_data.response and "messages" in self.conn_data.response:
            self.loaded_messages = self.conn_data.response["messages"]
            self.conn_data.response = None
            self.rerender_messages()
            return

        self.root.after(100, self.check_load_chat_request)

    def check_send_message_request(self):
        """
        Check for a response to the send message request.
        """
        if self.conn_data.response:
            self.conn_data.response = None
            self.loaded_messages += [
                (self.credentials, self.connected_to, self.chat_entry.get())
            ]
            self.chat_entry.delete(0, tk.END)
            self.rerender_messages()
            self.rerender_pings()
            return

        self.root.after(100, self.check_send_message_request)

    def check_new_message_request(self):
        """
        Check for a response to the new message request.
        """
        if self.conn_data.response and "sent_message" in self.conn_data.response:
            if self.connected_to == self.conn_data.response["sender"]:
                self.loaded_messages += [
                    (self.connected_to, self.credentials, self.conn_data.response["sent_message"], self.conn_data.response["message_id"])
                ]
                self.conn_data.response = None
                self.rerender_messages()
            
            self.incoming_pings += (
                self.conn_data.response["sender"],
                self.conn_data.response["sent_message"]
                )
            self.rerender_pings()
            return

        self.root.after(100, self.check_new_message_request)
    
    def check_undelivered_request(self):
        """
        Check for a response to the undelivered request.
        """
        if self.conn_data.response and "undelivered_messages" in self.conn_data.response:
            self.undelivered_messages = self.conn_data.response["undelivered_messages"]
            self.conn_data.response = None
            self.rerender_undelivered()
            return

        self.root.after(100, self.check_undelivered_request)

    """
    Functions starting with "send_" are used to send requests to the server.

    These are used when the user interacts with the tkinter window.
    """

    def send_logreg_request(self, action, username, password, confirm_password=None):
        """
        Send a login or register request to the server, depending on the action.

        Parameters
        ----------
        action : str
            The action to take. Either "login" or "register".
        username : str
            The username to send.
        password : str
            The password to send.
        confirm_password : str
            The confirm password to send. Only used for registration.
        """
        if action == "register" and password != confirm_password:
            self.register_passwords_do_not_match_label.pack()
        # create a request
        self.conn_data.request = {
            "action": action,
            "username": username,
            "passhash": password,
            "encoding": "utf-8",
        }

    def send_user_check_request(self, username):
        """
        Send a request to check if the username exists.

        Parameters
        ----------
        username : str
            The username to check.
        """
        # create a request
        if not username:
            return
        self.conn_data.request = {
            "action": "check_username",
            "username": username,
            "encoding": "utf-8",
        }

    def send_chat_load_request(self, username):
        """
        Send a request to load the chat for the selected user.
        To be done whenever a user wants to start messaging someone.

        Parameters
        ----------
        username : str
            The username to load the chat for.
        """
        # create a request
        self.conn_data.request = {
            "action": "load_chat",
            "user1": self.credentials,
            "user2": username,
            "encoding": "utf-8",
        }

        self.connected_to = username

        self.root.after(100, self.check_load_chat_request)

    def send_message_request(self, message):
        """
        Send a request to send a message to the connected user.

        Parameters
        ----------
        message : str
            The message to send.
        """
        # create a request
        self.conn_data.request = {
            "action": "send_message",
            "sender": self.credentials,
            "recipient": self.connected_to,
            "message": message,
            "encoding": "utf-8",
        }

        self.root.after(100, self.check_send_message_request)
    
    def send_undelivered_request(self, n_messages):
        """
        Send a request to view undelivered messages.

        Parameters
        ----------
        n_messages : int
            The number of messages to view.
        """
        # create a request
        self.conn_data.request = {
            "action": "view_undelivered",
            "user": self.credentials,
            "n_messages": n_messages,
            "encoding": "utf-8",
        }
        self.root.after(100, self.check_undelivered_request)

    """
    Functions starting with "setup_" are used to set up the state of the tkinter window.

    Each setup function has a corresponding "destroy_" function to remove the widgets from the window.
    """

    def setup_user_entry(self):
        """
        Set up the user entry screen.

        Has:
        - A label that says "Enter username:"
        - An entry for the user to enter their username.
        - A button that says "Enter" to submit the username.
        """
        self.user_entry_frame = tk.Frame(self.root)
        self.user_entry_frame.pack()
        self.user_entry_label = tk.Label(self.user_entry_frame, text="Enter username:")
        self.user_entry_label.pack()
        self.user_entry = tk.Entry(self.user_entry_frame)
        self.user_entry.pack()
        self.user_entry_button = tk.Button(
            self.user_entry_frame,
            text="Enter",
            command=lambda: self.send_user_check_request(self.user_entry.get()),
        )
        self.user_entry_button.pack()
        self.root.after(100, self.check_user_entry_response)

    def destroy_user_entry(self):
        """
        Destroy the user entry screen.
        """
        self.user_entry_frame.destroy()

    def setup_login(self):
        """
        Set up the login screen.

        Has:
        - A label that says "Enter your username:"
        - An entry for the user to enter their username.
        - A label that says "Enter your password:"
        - An entry for the user to enter their password.
        - A button that says "Login" to submit the login.
        - A label that says "Login failed, username/password incorrect" that is hidden by default.
        """
        self.login_frame = tk.Frame(self.root)
        self.login_frame.pack()
        self.login_label = tk.Label(self.login_frame, text="Enter your username:")
        self.login_label.pack()
        self.login_entry = tk.Entry(self.login_frame)
        self.login_entry.pack()
        self.login_password_label = tk.Label(
            self.login_frame, text="Enter your password:"
        )
        self.login_password_label.pack()
        self.login_password_entry = tk.Entry(self.login_frame)
        self.login_password_entry.pack()
        self.login_button = tk.Button(
            self.login_frame,
            text="Login",
            command=lambda: self.send_logreg_request(
                "login", self.login_entry.get(), self.login_password_entry.get()
            ),
        )
        self.login_button.pack()
        self.login_failed_label = tk.Label(
            self.login_frame, text="Login failed, username/password incorrect"
        )
        self.root.after(100, self.check_login_response)

    def destroy_login(self):
        """
        Destroy the login screen.
        """
        self.login_frame.destroy()

    def setup_undelivered(self):
        """
        Set up the undelivered screen.

        Has:
        - A label that says "Undelivered messages"
        - A listbox that has all the undelivered messages.
        - A button that says "Resend" to resend the selected message.
        """
        self.undelivered_frame = tk.Frame(self.root)
        self.undelivered_frame.pack()

        # say a label with "Welcome Back"
        self.welcome_back_label = tk.Label(self.undelivered_frame, text=f"Welcome back, {self.credentials}!")
        self.welcome_back_label.pack()

        self.undelivered_label = tk.Label(self.undelivered_frame, text=f"You have {self.n_undelivered} new messages")
        self.undelivered_label.pack()

        # put a number entry for number of messages to view
        self.undelivered_number_label = tk.Label(self.undelivered_frame, text="Enter number of messages to view:")
        self.undelivered_number_label.pack()

        # from 0 to n_undelivered
        self.undelivered_number_entry = tk.Entry(self.undelivered_frame)
        self.undelivered_number_entry.pack()

        # submit button
        self.undelivered_number_button = tk.Button(
            self.undelivered_frame,
            text="Submit",
            command=lambda: self.send_undelivered_request(self.undelivered_number_entry.get()),
        )
        self.undelivered_number_button.pack()

        # listbox with undelivered messages
        self.undelivered_listbox = tk.Listbox(self.undelivered_frame)
        for message in self.undelivered_messages:
            self.undelivered_listbox.insert(tk.END, message)
        self.undelivered_listbox.pack()

    def destroy_undelivered(self):
        """
        Destroy the undelivered screen.
        """
        self.undelivered_frame.destroy()

    def setup_register(self):
        """
        Set up the register screen.

        Has:
        - A label that says "Enter your username - reg:"
        - An entry for the user to enter their username.
        - A label that says "Enter your password - reg:"
        - An entry for the user to enter their password.
        - A label that says "Confirm your password - reg:"
        - An entry for the user to confirm their password.
        - A button that says "Register" to submit the registration.
        - A label that says "Passwords do not match" that is hidden by default.
        - A label that says "Username already exists" that is hidden by default.
        """
        self.register_frame = tk.Frame(self.root)
        self.register_frame.pack()
        self.register_label = tk.Label(
            self.register_frame, text="Enter your username - reg:"
        )
        self.register_label.pack()
        self.register_entry = tk.Entry(self.register_frame)
        self.register_entry.pack()
        self.register_password_label = tk.Label(
            self.register_frame, text="Enter your password - reg:"
        )
        self.register_password_label.pack()
        self.register_password_entry = tk.Entry(self.register_frame)
        self.register_password_entry.pack()
        self.register_password_confirm_label = tk.Label(
            self.register_frame, text="Confirm your password - reg:"
        )
        self.register_password_confirm_label.pack()
        self.register_password_confirm_entry = tk.Entry(self.register_frame)
        self.register_password_confirm_entry.pack()
        self.register_button = tk.Button(
            self.register_frame,
            text="Register",
            command=lambda: self.send_logreg_request(
                "register",
                self.register_entry.get(),
                self.register_password_entry.get(),
            ),
        )
        self.register_button.pack()
        self.register_passwords_do_not_match_label = tk.Label(
            self.register_frame, text="Passwords do not match"
        )
        self.register_username_exists_label = tk.Label(
            self.register_frame, text="Username already exists"
        )

        self.root.after(100, self.check_register_response)

    def destroy_register(self):
        """
        Destroy the register screen.
        """
        self.register_frame.destroy()

    def setup_main(self):
        """
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
        """
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack()

        self.logged_in_label = tk.Label(
            self.main_frame, text=f"Logged in as {self.credentials}"
        )
        self.logged_in_label.pack()

        self.users_frame = tk.Frame(self.main_frame)
        self.users_frame.pack(side=tk.LEFT)
        self.users_label = tk.Label(self.users_frame, text="Users")
        self.users_label.pack()

        self.users_listbox = tk.Listbox(self.users_frame)
        for user in self.users:
            self.users_listbox.insert(tk.END, user)

        self.users_listbox.pack()
        self.users_prev_button = tk.Button(self.users_frame, text="Prev")
        self.users_prev_button.pack(side=tk.LEFT)
        self.message_button = tk.Button(
            self.users_frame,
            text="Message",
            command=lambda: self.send_chat_load_request(
                self.users_listbox.get(tk.ACTIVE)[0]
            ),
        )
        self.message_button.pack(side=tk.LEFT)
        self.users_next_button = tk.Button(self.users_frame, text="Next")
        self.users_next_button.pack(side=tk.RIGHT)

        self.ping_frame = tk.Frame(self.main_frame)
        self.ping_frame.pack(side=tk.BOTTOM)

        self.incoming_pings_label = tk.Label(self.ping_frame, text="Incoming Pings")
        self.incoming_pings_label.pack()
        self.incoming_pings_listbox = tk.Listbox(self.ping_frame)
        for ping in self.incoming_pings:
            self.incoming_pings_listbox.insert(tk.END, ping)
        self.incoming_pings_listbox.pack()

        self.chat_frame = tk.Frame(self.main_frame)
        self.chat_frame.pack(side=tk.TOP)

        self.chat_text = tk.Listbox(self.chat_frame)
        self.chat_text.config(state=tk.DISABLED)

        if self.connected_to:
            # add text to chat frame saying "Messages with {self.connected_to}"
            self.chat_text.insert(tk.END, f"Messages with {self.connected_to}\n")

        self.chat_text.pack()

        # add text to chat frame
        for message in self.loaded_messages:
            self.chat_text.insert(tk.END, f"{message[0]}: {message[2]}\n")

        self.chat_entry_frame = tk.Frame(self.main_frame)
        self.chat_entry_frame.pack(side=tk.RIGHT)
        self.chat_entry = tk.Entry(self.chat_entry_frame)
        self.chat_entry.pack()
        self.send_button = tk.Button(
            self.chat_entry_frame,
            text="Send",
            command=lambda: [self.send_message_request(self.chat_entry.get())],
        )
        self.send_button.pack()
        self.settings_button = tk.Button(self.chat_entry_frame, text="Settings")
        self.settings_button.pack()

        self.root.after(100, self.check_new_message_request)

    def destroy_main(self):
        """
        Destroy the main screen.
        """
        self.main_frame.destroy()

    def rerender_messages(self):
        """
        Rerender the messages in the chat window.
        Needs to be called whenever new messages are received or sent.
        """
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.insert(tk.END, f"Messages with {self.connected_to}\n")
        for message in self.loaded_messages:
            self.chat_text.insert(tk.END, f"{message[0]}: {message[2]}\n")

        self.root.after(100, self.check_new_message_request)
    
    def rerender_pings(self):
        """
        Rerender the pings in the ping windows.
        Needs to be called whenever new pings are received.
        """
        self.incoming_pings_listbox.delete(0, tk.END)
        for ping in self.incoming_pings:
            self.incoming_pings_listbox.insert(tk.END, f"{ping[0]}: {ping[1]}")
    
    def rerender_users(self):
        """
        Rerender the users in the users listbox.
        Needs to be called whenever new users are received.
        """
        self.users_listbox.delete(0, tk.END)
        for user in self.users:
            self.users_listbox.insert(tk.END, user)
    
    def rerender_undelivered(self):
        """
        Rerender the undelivered messages in the undelivered listbox.
        Needs to be called whenever new undelivered messages are received.
        """
        self.undelivered_listbox.delete(0, tk.END)
        for message in self.undelivered_messages:
            self.undelivered_listbox.insert(tk.END, f"{message[0]}: {message[2]}")

        # remove submit button
        self.undelivered_number_button.pack_forget()

        # add "Go to Home" button
        self.go_home_button = tk.Button(
            self.undelivered_frame,
            text="Go to Home",
            command=lambda: [self.destroy_undelivered(), self.setup_main()],
        )
        self.go_home_button.pack()

    def setup_delete(self):
        self.delete_frame = tk.Frame(self.root)
        self.delete_frame.pack()
        self.delete_label = tk.Label(
            self.delete_frame,
            text="Are you sure you want to delete your account?\n(Enter account details to confirm)",
        )
        self.delete_label.pack()

        self.confirm_username_label = tk.Label(
            self.delete_frame, text="Enter your username:"
        )
        self.confirm_username_label.pack()

        self.confirm_username_entry = tk.Entry(self.delete_frame)
        self.confirm_username_entry.pack()

        self.confirm_password_label = tk.Label(
            self.delete_frame, text="Enter your password:"
        )
        self.confirm_password_label.pack()

        self.confirm_password_entry = tk.Entry(self.delete_frame)
        self.confirm_password_entry.pack()

        self.delete_button = tk.Button(self.delete_frame, text="Delete")
        self.delete_button.pack()
        self.cancel_button = tk.Button(self.delete_frame, text="Cancel")
        self.cancel_button.pack()


"""
The rest of the code is for setting up the connection and running the client.
"""


def start_connection(
    host: str, port: int
) -> tuple[socket.socket, types.SimpleNamespace]:
    """
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
    """

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
    """
    Event loop for the client.
    Run in separate thread.
    """
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

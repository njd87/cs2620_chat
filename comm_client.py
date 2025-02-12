import io
import json
import logging
import os
import selectors
import struct
import sys
import parse_helpers
import socket
import tkinter as tk

# log to a file
log_file = "logs/client_bolt.log"

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

class Bolt:
    """
    A class that handles data communication, protocols, and database access.

    Bidreictional
    Object
    Logging
    Transmitter
    """

    def __init__(self, sel, sock, addr, gui, protocol_type="json"):
        """
        Initialize the Bolt object.
        We need to keep the selector, socket, and address here, as well as the gui on the client side.

        Instream + outstream are used to store data coming in and going out.

        Parameters
        ----------
        sel : selectors.DefaultSelector
            The selector object.
        sock : socket.socket
            The socket object.
        addr : tuple
            The address of the client.
        gui : tkinter.Tk
            The tkinter GUI object.
        protocol_type : str
            The protocol type to use (default is 'json').
        """

        self.sel = sel
        self.sock = sock
        self.addr = addr
        self.gui = gui
        self.protocol_type = protocol_type

        # where to store data either coming in or going out
        # necessary for storage before protocol encoding/decoding
        self.instream = b""
        self.outstream = b""

        # necessary for json header (json header is variable)
        self._header_len = None

        self.header = None
        self.response = None
        self.responded = None
        self.request = None
        self.request_created = False

    def process_events(self, mask):
        '''
        Process events for the given socket whenever the selector detects an event.
        '''
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()

    def read(self):
        '''
        Read in info from instream and process it.

        First reads raw bytes, then reads header length, then reads header, then reads response.
        '''
        self._read()
        # print("Length of read bytes:", len(self.instream))

        if self._header_len is None:
            self.process_header_len()

        if self._header_len is not None:
            if self.header is None:
                self.process_header()

        if self.header is not None:
            if self.response is None:
                self.process_response()

        if self.response is not None:
            if self.responded is None:
                self.respond()

    def _read(self):
        '''
        Read in raw bytes from the socket.
        '''
        try:
            data = self.sock.recv(4096)
        except BlockingIOError:
            pass
        else:
            if data:
                self.instream += data
            else:
                raise RuntimeError("Peer closed.")

    def process_header_len(self):
        '''
        Process the header length.

        For json and custom, the length is represented as a 2 byte unsigned integer.
        '''
        if self.protocol_type == "json" or self.protocol_type == "custom":
            processlen = 2
            if len(self.instream):
                self._header_len = struct.unpack(">H", self.instream[:processlen])[0]
                self.instream = self.instream[processlen:]
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def process_header(self):
        '''
        Process the header of the message.

        More information on how this works can be found in comments within this function.
        '''
        if self.protocol_type == "json":
            '''
            For json, the header is a json object that contains the following fields:
            - byteorder
            - content-length
            - content-encoding
            '''
            hdrlen = self._header_len
            if len(self.instream) >= hdrlen:
                self.header = self._byte_decode(self.instream[:hdrlen], "utf-8")
                self.instream = self.instream[hdrlen:]
                for reqhdr in (
                    "byteorder",
                    "content-length",
                    "content-encoding",
                ):
                    if reqhdr not in self.header:
                        raise ValueError(f"Missing required header '{reqhdr}'.")
                    
        elif self.protocol_type == "custom":
            '''
            For custom, the header is a dict that contains the following fields:

            - version
            - byteorder
            - content-encoding
            '''
            hdrlen = self._header_len
            if len(self.instream) >= hdrlen:
                self.header = self._byte_decode(self.instream[:hdrlen], "utf-8")
                self.instream = self.instream[hdrlen:]
                if len(self.header) != 2:
                    raise ValueError(
                        f"Header must have 2 fields, not {len(self.header)}."
                    )
                for reqhdr in (
                    "version",
                    "content-length",
                ):
                    if reqhdr not in self.header:
                        raise ValueError(f"Missing required header '{reqhdr}'.")

                # if version is not 1, raise error
                if self.header["version"] != 1:
                    raise ValueError(f"Invalid version '{self.header['version']}'.")
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def process_response(self):
        '''
        When the header is processed, process the response by decoding the bytes.

        This looks the same for both json and custom.
        '''
        if self.protocol_type == "json" or self.protocol_type == "custom":
            content_len = self.header["content-length"]
            if not len(self.instream) >= content_len:
                return
            data = self.instream[:content_len]
            self.instream = self.instream[content_len:]
            if self.protocol_type == "json":
                encoding = self.header["content-encoding"]
            elif self.protocol_type == "custom":
                encoding = 'utf-8'
            self.response = self._byte_decode(data, encoding)
            logging.info(f"Received response {self.response!r} from {self.addr}")

            # Set selector to listen for write events, we're done reading.
            self._header_len = None
            self.header = None
            self._set_selector_events_mask("rw")
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def respond(self):
        '''
        Respond to the response by processing the action.

        Action possibilites include:
        - check_username
        - login
        - register
        - load_chat
        - send_message
        - ping
        - view_undelivered
        - delete_message
        - delete_account
        - ping_user
        '''
        action = self.response["action"]
        if action == "check_username":
            # no matter what, we destroy the user entry screen
            self.gui.destroy_user_entry()
            # username exists, send to login
            if self.response["result"]:
                self.response = None
                self.gui.setup_login()
            # username does not exist, send to register
            else:
                self.response = None
                self.gui.setup_register()
        elif action == "login":
            # logged in successfully - passhash matches
            if self.response["result"]:
                self.gui.users = self.response["users"]
                self.gui.n_undelivered = self.response["n_undelivered"]
                self.response = None
                self.gui.credentials = self.gui.login_entry.get()
                self.gui.login_frame.destroy()
                self.gui.setup_undelivered()
            # login failed, incorrect username/password
            else:
                self.response = None
                self.gui.login_frame.destroy()
                self.gui.setup_login(failed=True)

        elif action == "register":
            if self.response["result"]:
                # registered successfully
                self.gui.users = self.response["users"]
                self.response = None
                self.gui.credentials = self.gui.register_entry.get()
                self.gui.register_frame.destroy()
                self.gui.setup_main()
            else:
                # username already exists
                self.response = None
                self.gui.register_username_exists_label.pack()
        elif action == "load_chat":
            self.gui.loaded_messages = self.response["messages"]
            self.response = None
            self.gui.rerender_messages()
        elif action == "send_message":
            # locally load sent message
            self.gui.loaded_messages += [
                (
                    self.gui.credentials,
                    self.gui.connected_to,
                    self.gui.chat_entry.get(),
                    self.response["message_id"],
                )
            ]
            self.response = None
            self.gui.chat_entry.delete(0, tk.END)
            self.gui.rerender_messages()
        elif action == "view_undelivered":
            self.gui.undelivered_messages = self.response["messages"]
            self.response = None
            self.gui.rerender_undelivered()
        elif action == "ping":
            if self.gui.connected_to == self.response["sender"]:
                self.gui.loaded_messages += [
                    (
                        self.gui.connected_to,
                        self.gui.credentials,
                        self.response["sent_message"],
                        self.response["message_id"],
                    )
                ]
                self.response = None
                self.gui.rerender_messages()
            else:
                self.gui.incoming_pings += [
                    (self.response["sender"], self.response["sent_message"])
                ]
                self.response = None
                self.gui.rerender_pings()
        elif action == "delete_message":
            self.response = None
            del self.gui.loaded_messages[self.gui.chat_text.curselection()[0] - 1]
            self.gui.chat_entry.delete(0, tk.END)
            self.gui.rerender_messages()
        elif action == "delete_account":
            if self.response["result"]:
                self.response = None
                self.gui.reset_login_vars()
                self.gui.destroy_settings()
                self.gui.setup_deleted()
            else:
                self.response = None
                self.gui.destroy_settings()
                self.gui.setup_settings(failed=True)
        elif action == "ping_user":
            pinging_user = self.response["ping_user"]
            # if user is already in users, remove them; user exists but deleted account
            if pinging_user in self.gui.users:
                self.gui.users = [
                    user for user in self.gui.users if user != pinging_user
                ]
                self.gui.rerender_users()
                if self.gui.connected_to == self.response["ping_user"][0]:
                    self.gui.connected_to = None
                    self.gui.loaded_messages = []
                    self.gui.rerender_messages()
                self.gui.incoming_pings = [
                    ping for ping in self.gui.incoming_pings if ping[0] != pinging_user
                ]
                self.gui.rerender_pings()
            # user is not in users, add them; created new account
            elif pinging_user not in self.gui.users:
                self.gui.users += [pinging_user]
                self.gui.rerender_users()
            self.response = None

    def write(self):
        if self.request:
            if not self.request_created:
                self.create_request()

        self._write()

    def _write(self):
        if self.outstream:
            try:
                sent_bytes = self.sock.send(self.outstream)
            except BlockingIOError:
                pass
            else:
                self.outstream = self.outstream[sent_bytes:]
                if sent_bytes and not self.outstream:
                    self.request_created = False
                    self._set_selector_events_mask("rw")

    def create_request(self):
        '''
        When a request is created, it is created based on the action that is passed in.

        Actions include:
        - login
        - register
        - check_username
        - load_chat
        - send_message
        - ping
        - view_undelivered
        - delete_message
        - delete_account
        
        Once it is put into a dictionary, it can be encoded into bytes.
        '''
        action = self.request.get("action")
        if action in ["login", "register"]:
            username = self.request.get("username")
            passhash = self.request.get("passhash")
            content = {"username": username, "passhash": passhash, "action": action}
        elif action == "check_username":
            username = self.request.get("username")
            content = {"username": username, "action": action}
        elif action == "load_chat":
            username = self.request.get("username")
            user2 = self.request.get("user2")
            content = {"username": username, "user2": user2, "action": action}
        elif action == "send_message":
            sender = self.request.get("sender")
            recipient = self.request.get("recipient")
            message = self.request.get("message")
            content = {
                "sender": sender,
                "recipient": recipient,
                "message": message,
                "action": action,
            }
        elif action == "ping":
            content = {
                "sender": self.request.get("sender"),
                "sent_message": self.request.get("sent_message"),
                "action": action,
            }
        elif action == "view_undelivered":
            username = self.request.get("username")
            n_messages = self.request.get("n_messages")
            content = {"username": username, "n_messages": n_messages, "action": action}
        elif action == "delete_message":
            message_id = self.request.get("message_id")
            content = {"message_id": message_id, "action": action}
        elif action == "delete_account":
            username = self.request.get("username")
            passhash = self.request.get("passhash")
            content = {"username": username, "passhash": passhash, "action": action}
        else:
            content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = self.request.get("encoding")

        if self.protocol_type == "json":
            temp_request = {
                "content_bytes": self._byte_encode(content, content_encoding),
                "content_type": "text/json",
                "content_encoding": content_encoding,
            }
            message = self._create_message(**temp_request)
        elif self.protocol_type == "custom":
            content_bytes = self._byte_encode(content, content_encoding)
            customheader = {
                "version": 1,
                "content-length": len(content_bytes),
            }
            customheader_bytes = self._byte_encode(customheader, content_encoding)
            message_hdr = struct.pack(">H", len(customheader_bytes))
            message = message_hdr + customheader_bytes + content_bytes
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

        self.request_created = True
        self.request = None
        self.outstream += message

    def _create_message(self, *, content_bytes, content_type, content_encoding):
        if self.protocol_type == "json":
            jsonheader = {
                "byteorder": sys.byteorder,
                "content-type": content_type,
                "content-encoding": content_encoding,
                "content-length": len(content_bytes),
            }
            jsonheader_bytes = self._byte_encode(jsonheader, "utf-8")
            message_hdr = struct.pack(">H", len(jsonheader_bytes))
            message = message_hdr + jsonheader_bytes + content_bytes
        elif self.protocol_type == "custom":
            # it should never get here, but in case it does, it shouldn't do anything
            pass
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")
        return message

    def _byte_encode(self, obj, encoding):
        '''
        Encode the object into bytes based on the protocol type.
        '''
        if self.protocol_type == "json":
            return json.dumps(obj, ensure_ascii=False).encode(encoding)
        elif self.protocol_type == "custom":
            # convert dict to string
            obj = parse_helpers.dict_to_string(obj)
            # encode string as bytes
            return obj.encode(encoding)
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def _byte_decode(self, bytes, encoding):
        if self.protocol_type == "json":
            tiow = io.TextIOWrapper(io.BytesIO(bytes), encoding=encoding, newline="")
            obj = json.load(tiow)
            tiow.close()
        elif self.protocol_type == "custom":
            obj = parse_helpers.string_to_dict(bytes.decode(encoding))
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")
        return obj

    def _set_selector_events_mask(self, mode):
        '''
        Set the selector events mask.
        
        references online pointed to this function as specifications, but we only use rw

        Parameters
        ----------
        mode : str
            The mode to set the selector events mask to.
        '''
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode {mode!r}.")
        self.sel.modify(self.sock, events, data=self)

    def close(self):
        logging.info(f"Closing connection to {self.addr}")
        try:
            self.sel.unregister(self.sock)
        except Exception as e:
            logging.error(f"Error: selector.unregister() exception for " f"{self.addr}: {e!r}")

        try:
            self.sock.close()
        except OSError as e:
            logging.error(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

import io
import json
import selectors
import struct
import sys
import sqlite3

# import sha256 password hashing
import hashlib

import parse_helpers


class Bolt:
    """
    A class that handles data communication, protocols, and database access.

    Bidreictional
    Object
    Logging
    Transmitter
    """

    def __init__(self, sel, sock, addr, protocol_type="json"):
        """
        Initialize the Bolt object.
        We need to keep the selector, socket, and address here.

        Instream + outstream are used to store data coming in and going out.

        Parameters
        ----------
        sel : selectors.DefaultSelector
            The selector object.
        sock : socket.socket
            The socket object.
        addr : tuple
            The address of the client.
        protocol_type : str
            The protocol type to use (default is 'json').
        """
        self.sel = sel
        self.sock = sock
        self.addr = addr

        # where to store data either coming in or going out
        # necessary for storage before protocol encoding/decoding
        self.instream = b""
        self.outstream = b""

        self.protocol_type = protocol_type

        # necessary for json header (json header is variable)
        self._header_len = None

        self.header = None
        self.request = None
        self.response_created = False

    def process_events(self, mask):
        '''
        Process events for the given socket whenever the selector detects an event.
        '''
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            return self.write()

    def read(self):
        '''
        Read in info from instream and process it.

        First reads raw bytes, then reads header length, then reads header, then reads response.
        '''
        self._read()

        if self._header_len is None:
            self.process_header_len()

        if self._header_len is not None:
            if self.header is None:
                self.process_header()

        if self.header is not None:
            if self.request is None:
                self.process_request()

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
                if len(self.header) != 4:
                    raise ValueError(f"Header must have 4 fields, not {len(self.header)}.")
                for reqhdr in (
                    "version",
                    "byteorder",
                    "content-encoding",
                    "content-length",
                ):
                    if reqhdr not in self.header:
                        raise ValueError(f"Missing required header '{reqhdr}'.")

                # if version is not 1, raise error
                if self.header["version"] != 1:
                    raise ValueError(f"Invalid version '{self.header[0]}'.")
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def process_request(self):
        '''
        When the header is processed, process the request by decoding the bytes.

        This looks the same for both json and custom.
        '''
        if self.protocol_type == "json" or self.protocol_type == "custom":
            content_len = self.header["content-length"]
            if not len(self.instream) >= content_len:
                return
            data = self.instream[:content_len]
            self.instream = self.instream[content_len:]
            encoding = self.header["content-encoding"]
            self.request = self._byte_decode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")

            # Set selector to listen for write events, we're done reading.
            self._header_len = None
            self.header = None
            self._set_selector_events_mask("rw")
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def write(self):  # ND: need to relay create_response back to user
        back_to_server = None
        if self.request:
            if not self.response_created:
                back_to_server = self.create_response()

        self._write()
        return back_to_server

    def _write(self):
        if self.outstream:
            print(f"Preparing to write {self.outstream!r} to {self.addr}")
            try:
                sent_bytes = self.sock.send(self.outstream)
            except BlockingIOError:
                pass
            else:
                self.outstream = self.outstream[sent_bytes:]
                if sent_bytes and not self.outstream:
                    self.response_created = False
                    self._set_selector_events_mask("rw")

    def create_response(self):
        '''
        Create a response to the request.

        Note: sometimes, back to server is a dictionary that is sent back to the backend for logic
        regarding text sending and mapping ports to users.
        '''
        back_to_server = {}
        action = self.request.get("action")
        if action == "login":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username")
            passhash = self.request.get("passhash") 
            passhash = hashlib.sha256(passhash.encode()).hexdigest()
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (username,))

            result = sqlcur.fetchone()
            if result:
                # username exists and passhash matches
                if result[0] == passhash:
                    # get number of undelivered messages
                    sqlcur.execute(
                        "SELECT COUNT(*) FROM messages WHERE recipient=? AND delivered=0",
                        (username,),
                    )

                    n_undelivered = sqlcur.fetchone()[0]

                    content = {
                        "action": action,
                        "result": True,
                        "users": [s[0] for s in sqlcur.execute(
                            "SELECT username FROM users WHERE username != ?", (username,)
                        ).fetchall()],
                        "n_undelivered": n_undelivered,
                    }
                    back_to_server["new_user"] = username
                # username exists but passhash is wrong
                else:
                    content = {"action": action, "result": False}
            else:
                # username doesn't exist
                content = {"action": action, "result": False}

            sqlcon.close()
        elif action == "register":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username")
            passhash = self.request.get("passhash")
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (username,))

            result = sqlcur.fetchone()
            if result:
                content = {"action": action, "result": False}
            else:
                passhash = hashlib.sha256(passhash.encode()).hexdigest()
                sqlcur.execute(
                    "INSERT INTO users (username, passhash) VALUES (?, ?)",
                    (username, passhash),
                )
                sqlcon.commit()
                content = {
                    "action": action, 
                    "result": True,
                    "users": [s[0] for s in sqlcur.execute(
                        "SELECT username FROM users WHERE username != ?", (username,)
                        ).fetchall()],
                }
                back_to_server["new_user"] = username
                back_to_server["registering"] = True

            sqlcon.close()
        elif action == "check_username":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username")
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (username,))

            result = sqlcur.fetchone()
            if result:
                content = {"action": action, "result": True}
            else:
                content = {"action": action, "result": False}

            sqlcon.close()
        elif action == "load_chat":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username")
            user2 = self.request.get("user2")
            print(username)
            print(user2)
            try:
                sqlcur.execute(
                    "SELECT sender, recipient, message, message_id FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY time",
                    (username, user2, user2, username),
                )
                result = sqlcur.fetchall()
            except Exception as e:
                print("Error:", e)
                result = []
            content = {"action": action, "messages": result}

            sqlcon.close()
        elif action == "send_message":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            sender = self.request.get("sender")
            recipient = self.request.get("recipient")
            message = self.request.get("message")
            try:
                sqlcur.execute(
                    "INSERT INTO messages (sender, recipient, message) VALUES (?, ?, ?)",
                    (sender, recipient, message),
                )
                sqlcon.commit()

                # get the message_id
                sqlcur.execute(
                    "SELECT message_id FROM messages WHERE sender=? AND recipient=? AND message=? ORDER BY time DESC LIMIT 1",
                    (sender, recipient, message),
                )
                message_id = sqlcur.fetchone()[0]
                content = {"action": action, "message_id": message_id}

                back_to_server["new_message"] = {
                    "message_id": message_id,
                    "sender": sender,
                    "recipient": recipient,
                    "sent_message": message,
                }
            except:
                content = {"action": action, "result": False}

            sqlcon.close()
        elif action == "ping":
            content = {
                "action": action, 
                "sender": self.request.get("sender"),
                "sent_message": self.request.get("sent_message"),
                "message_id": self.request.get("message_id")
            }

            # update the message to delivered
            message_id = self.request.get("message_id")
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            print(f"Updating message {message_id} to delivered.")

            sqlcur.execute(
                "UPDATE messages SET delivered=1 WHERE message_id=?", (message_id,)
            )
            sqlcon.commit()

            sqlcon.close()
        elif action == "view_undelivered":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username")
            n_messages = self.request.get("n_messages")

            print(f"User: {username}")
            print(f"Number of messages: {n_messages}")
            sqlcur.execute(
                "SELECT sender, recipient, message, message_id FROM messages WHERE recipient=? AND delivered=0 ORDER BY time DESC LIMIT ?",
                (username, n_messages),
            )
            result = sqlcur.fetchall()
            content = {"action": action, "messages": result}

            sqlcur.execute(
                "UPDATE messages SET delivered=1 WHERE recipient=?", (username,)
            )
            sqlcon.commit()

            sqlcon.close()
        elif action == "delete_message":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            message_id = self.request.get("message_id")
            sqlcur.execute("DELETE FROM messages WHERE message_id=?", (message_id,))
            sqlcon.commit()

            sqlcon.close()
            content = {"action": action, "result": True}
        elif action == "delete_account":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            username = self.request.get("username") 
            passhash = self.request.get("passhash") 
            passhash = hashlib.sha256(passhash.encode()).hexdigest()
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (username,))

            result = sqlcur.fetchone()
            if result:
                # username exists and passhash matches
                if result[0] == passhash:
                    sqlcur.execute("DELETE FROM users WHERE username=?", (username,))
                    sqlcur.execute("DELETE FROM messages WHERE sender=? OR recipient=?", (username, username))
                    sqlcon.commit()

                    content = {
                        "action": action, 
                        "result": True
                    }
                    # tell server to ping users to update their chat, remove from connected users
                    back_to_server["delete_user"] = username
                # username exists but passhash is wrong
                else:
                    content = {"action": action, "result": False}
            else:
                # username doesn't exist
                content = {"action": action, "result": False}

            sqlcon.close()
        elif action == "ping_user":
            # ping that a user has been added or deleted
            content = {
                "action": action, 
                "ping_user": [self.request.get("ping_user")]
            }
        else:
            content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = "utf-8"
        if self.protocol_type == "json":
            response = {
                "content_bytes": self._byte_encode(content, content_encoding),
                "content_type": "text/json",
                "content_encoding": content_encoding,
            }

            message = self._create_message(**response)
        elif self.protocol_type == "custom":
            print("HERRRREEEEECUSTOM")
            content_bytes = self._byte_encode(content, content_encoding)
            customheader = {
                "version": 1,
                "byteorder": sys.byteorder,
                "content-encoding": content_encoding,
                "content-length": len(content_bytes)
            }
            customheader_bytes = self._byte_encode(customheader, content_encoding)
            message_hdr = struct.pack(">H", len(customheader_bytes))
            message = message_hdr + customheader_bytes + content_bytes

        self.response_created = True
        self.request = None
        self.outstream += message

        return back_to_server

    def _create_message(self, *, content_bytes, content_type, content_encoding):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._byte_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes 
        return message

    def _byte_encode(self, obj, encoding):
        '''
        Encode message into bytes.
        '''
        if self.protocol_type == "json":
            return json.dumps(obj, ensure_ascii=False).encode(encoding)
        elif self.protocol_type == "custom":
            # convert dict to string
            obj = parse_helpers.dict_to_string(obj)
            # encode string as byte
            return obj.encode(encoding)
        else:
            raise ValueError(f"Invalid protocol type '{self.protocol_type}'.")

    def _byte_decode(self, bytes, encoding):
        '''
        Decode message from bytes.
        '''
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
        print(f"Closing connection to {self.addr}")
        try:
            self.sel.unregister(self.sock)
        except Exception as e:
            print(f"Error: selector.unregister() exception for " f"{self.addr}: {e!r}")

        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None

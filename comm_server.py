import io
import json
import selectors
import struct
import sys
import sqlite3
import socket
# import sha256 password hashing
import hashlib

class Bolt:
    '''
    A class that handles data communication, protocols, and database access.
    
    Bidreictional
    Object
    Logging
    Transmitter
    '''
    def __init__(self, sel, sock, addr, protocol_type='json'):
        '''
        Initialize the Memo object.
        We need to keep the selector, socket, and address here.
        We also have an instream and outstream for holding transferred information.

        '''
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
        if mask & selectors.EVENT_READ:
            print("reading")
            self.read()
        if mask & selectors.EVENT_WRITE:
            print("writing")
            self.write()

    def read(self):
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
        try:
            data = self.sock.recv(4096) # KG: why this amount
        except BlockingIOError:
            pass
        else:
            if data:
                self.instream += data 
                print("instream", self.instream)
            else:
                raise RuntimeError("Peer closed.")

    def process_header_len(self):
        processlen = 2
        if len(self.instream):
            self._header_len = struct.unpack(
                ">H", self.instream[:processlen]
            )[0]
            self.instream = self.instream[processlen:]

    def process_header(self):
        hdrlen = self._header_len
        if len(self.instream) >= hdrlen:
            self.header = self._json_decode(
                self.instream[:hdrlen], "utf-8"
            )
            self.instream = self.instream[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-encoding",
            ):
                if reqhdr not in self.header:
                    raise ValueError(f"Missing required header '{reqhdr}'.")
                
    def process_request(self):
        content_len = self.header["content-length"]
        if not len(self.instream) >= content_len:
            return
        data = self.instream[:content_len]
        self.instream = self.instream[content_len:]
        encoding = self.header["content-encoding"]
        self.request = self._json_decode(data, encoding)
        print(f"Received request {self.request!r} from {self.addr}")
        
        # Set selector to listen for write events, we're done reading.
        self._header_len = None
        self.header = None
        self._set_selector_events_mask("w")

            
    def write(self): # ND: current issue in this block, no bytes being transferred to client
        if self.request:
            if not self.response_created:
                print('got here')
                self.create_response()
                print('past here')

        print(f"Preparing to write {self.outstream!r} to {self.addr}")
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
                    self.response_created = False
                    self._set_selector_events_mask("r")

    def create_response(self):
        action = self.request.get("action")
        if action == "login":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            user = self.request.get("username") # KG: what if doesn't match
            passhash = self.request.get("passhash") # KG: need to hash
            passhash = hashlib.sha256(passhash.encode()).hexdigest()
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (user,))

            result = sqlcur.fetchone()
            if result:
                if result[0] == passhash:
                    content = {
                        "result": True,
                        "users": sqlcur.execute("SELECT username FROM users WHERE username != ?", (user,)).fetchall()
                        }
                else:
                    content = {"result": False}
            else:
                content = {"result": False}

            sqlcon.close()
        elif action == "register":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            user = self.request.get("username") # KG: what if doesn't match
            passhash = self.request.get("passhash")
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (user,))

            result = sqlcur.fetchone()
            if result:
                content = {"result": False}
            else:
                passhash = hashlib.sha256(passhash.encode()).hexdigest()
                sqlcur.execute("INSERT INTO users (username, passhash) VALUES (?, ?)", (user, passhash))
                sqlcon.commit()
                content = {
                    "result": True,
                    "users": sqlcur.execute("SELECT username FROM users WHERE username != ?", (user,)).fetchall()
                    }
            
            sqlcon.close()
        elif action == "check_username":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            user = self.request.get("username")
            sqlcur.execute("SELECT passhash FROM users WHERE username=?", (user,))

            result = sqlcur.fetchone()
            if result:
                content = {"result": True}
            else:
                content = {"result": False}
            
            sqlcon.close()
        elif action == "load_chat": # ND: current issue here in this block, not sure where it is
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            user1 = self.request.get("user1")
            user2 = self.request.get("user2")
            print(user1)
            print(user2)
            try:
                sqlcur.execute("SELECT sender, recipient, message, message_id FROM messages WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?) ORDER BY time", (user1, user2, user2, user1))
                result = sqlcur.fetchall()
            except Exception as e:
                print('Error:', e)
                result = []
            content = {"messages": result}
            
            sqlcon.close()
        elif action == "send_message":
            sqlcon = sqlite3.connect("data/messenger.db")
            sqlcur = sqlcon.cursor()

            sender = self.request.get("sender")
            recipient = self.request.get("recipient")
            message = self.request.get("message")
            try:
                sqlcur.execute("INSERT INTO messages (sender, recipient, message) VALUES (?, ?, ?)", (sender, recipient, message))
                sqlcon.commit()
                content = {"result": True}
            except:
                content = {"result": False}
            
            sqlcon.close()
        else:
            content = {"result": f"Error: invalid action '{action}'."}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }

        message = self._create_message(**response)
        self.response_created = True
        self.request = None
        self.outstream += message

    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message

    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj
    
    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events: mode is 'r', 'w', or 'rw'."""
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
            print(
                f"Error: selector.unregister() exception for "
                f"{self.addr}: {e!r}"
            )

        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            # Delete reference to socket object for garbage collection
            self.sock = None
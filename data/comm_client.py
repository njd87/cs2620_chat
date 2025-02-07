class Memo:
    def __init__(self, sel, sock, addr):
        self.sel = sel
        self.sock = sock
        self.addr = addr

        self._inbuffer = b""
        self._outbuffer = b""

        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
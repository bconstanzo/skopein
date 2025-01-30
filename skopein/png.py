import re
import struct
import zlib

# based on spec available online at:
#   https://www.w3.org/TR/2003/REC-PNG-20031110/#5DataRep

_rx_valid_ctype = re.compile(b"[A-Za-z]")

def valid_ctype(ctype):
    return _rx_valid_ctype.sub(b"", ctype) == b""

class Chunk:
    def __init__(self, rawbytes, *, ctype="", start=0, length=0, flag_crc_check=True):
        self.rawbytes = rawbytes
        self.data = b""
        self.ctype = ctype
        self.start = start
        self.length = length
        self.crc32 = 0
        self._flag_crc_check = flag_crc_check
        self.parse()

    def __repr__(self):
        return (
            f"< {self.__class__.__qualname__}"
            f" {self.ctype}"
            f" start={self.start}"
            f" length={self.length}"
            f" >"
        )
    
    def parse(self):
        data = self.rawbytes
        self.length, = struct.unpack(">L", data[:4])
        ctype = data[4:8]
        if not valid_ctype(ctype):
            raise ValueError("Invalid chunk type in file!")
        self.ctype = ctype.decode("utf-8")
        self.data = data[8: 8 + self.length]
        self.crc32 = data[8 + self.length: 12 + self.length]
        if self._flag_crc_check:
            crc_calc = zlib.crc32(data[4: 8 + self.length])
            crc_calc = struct.pack(">L", crc_calc)
            if crc_calc != self.crc32:
                raise ValueError("Invalid CRC32 for chunk!")
        self.rawbytes = data[:self.length + 12]
    
def parse_png(data):
    chunks = []
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        # literal value from the spec, obtained doing
        #   bytes( [137, 80, 78, 71, 13, 10, 26, 10] )
        return chunks
    pos = 8
    while pos < len(data):
        try:
            chunk = Chunk(data[pos:], start=pos)
        except Exception as e:
            print(e)
            return chunks
        chunks.append(chunk)
        pos += chunk.length + 12
    return chunks

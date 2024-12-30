import re
import struct


jpg_segments = {
    # (Start|End) Of Image
    b"\xff\xd8": "SOI", b"\xff\xd9": "EOI",
    # Application markers
    b"\xff\xe0": "APP0",
    b"\xff\xe1": "APP1",  # EXIF
    # we have more but many are rare or non-existant
    b"\xff\xe2": "APP2", b"\xff\xe3": "APP3", b"\xff\xe4": "APP4",
    b"\xff\xe5": "APP5", b"\xff\xe6": "APP6", b"\xff\xe7": "APP7",
    b"\xff\xe8": "APP8", b"\xff\xe9": "APP9", b"\xff\xea": "APP10",
    b"\xff\xeb": "APP11", b"\xff\xec": "APP12", b"\xff\xed": "APP13",
    b"\xff\xee": "APP14", b"\xff\xef": "APP15",
    # SOFs -- Start of Frame
    b"\xff\xc0": "SOF0", b"\xff\xc1": "SOF1",
    # usully unsupported, according to sugovica.hu
    b"\xff\xc2": "SOF2", b"\xff\xc3": "SOF3", b"\xff\xc5": "SOF5",
    b"\xff\xc6": "SOF6", b"\xff\xc7": "SOF7", b"\xff\xc9": "SOF9",
    b"\xff\xca": "SOF10", b"\xff\xcb": "SOF11", b"\xff\xcd": "SOF13",
    b"\xff\xce": "SOF14", b"\xff\xcf": "SOF15",
    # tables
    b"\xff\xc4": "DHT",  # Huffman Table
    b"\xff\xcc": "DAC",  # Arithmetic Table, sugovica.hu says "usually unsupported"
    b"\xff\xdb": "DQT",  # Quantization Table
    b"\xff\xda": "SOS",
    b"\xff\xdd": "DRI",  # Define Restart Interval
    # undefined/reserved/skip
    b"\xff\xc8": "JPG",  # "causes decoding error"
    b"\xff\xf0": "JPG0",
    b"\xff\xfd": "JPG13",
    b"\xff\xdc": "DNL",
    b"\xff\xde": "DHP",
    b"\xff\xdf": "EXP",
    b"\xff\x01": "*TEM", # "usually causes decoding error"
    # RSTns, used for resync
    b"\xff\xd0": "RST0", b"\xff\xd1": "RST1", b"\xff\xd2": "RST2", b"\xff\xd3": "RST3",
    b"\xff\xd4": "RST4", b"\xff\xd5": "RST5", b"\xff\xd6": "RST6", b"\xff\xd7": "RST7",
    # Comment
    b"\xff\xfe": "COM",
}

valid_markers = [ marker[1:2] for marker in jpg_segments.keys()][1:]
rx_sosend_pattern = b"\xff(" + b"|".join(valid_markers) + b")"
rx_sosend = re.compile(rx_sosend_pattern)

st_seglen = struct.Struct(">H")

class Segment:
    def __init__(self, rawbytes, *, code="", start=0, length=0):
        self.rawbytes = rawbytes
        self.code = code
        self.start = start
        self.length = length
        # and now we call the auto-parser
        self.parse()

    
    def __repr__(self):
        return (
            f"< {self.__class__.__qualname__}"
            f" {self.code}"
            f" start={self.start}"
            f" length={self.length}"
            f" >"
        )
    
    def __str__(self):
        return "\n".join([
            f"< {self.__class__.__qualname__}",
            f"    code: {self.code}",
            f"    start: {self.start}",
            f"    length: {self.length}",
            # f"    attrs: {pformat(self.attrs)}",
            f" >",
        ])
    
    def parse(self):
        data = self.rawbytes
        code = data[:2]
        self.code = jpg_segments[code]
        # NOTE:     ^^^^^^^^^^^^^^^^^^
        #   maybe the mechanic here could be to do a .get() instead of []
        #   and we could default to either "Corrupted" segment and/or "Extra"
        #   (for cases like Canon and Sony that store additional data at the
        #   end of the JPEG stream)?
        if code in {b"\xff\xd8", b"\xff\xd9"}:
            self.length = 0
            self.rawbytes = data[:2]
            return 0  # we make an early return for the EOI segment
        length, = st_seglen.unpack(data[2:4])
        self.length = length
        if code != b"\xff\xda":
            self.rawbytes = data[:length + 2]
            return length
        # SOS segments are variable length until we find another marker
        # or end of data...
        end = rx_sosend.search(data, pos=2)
        if end is None:
            raise ValueError("Corrupt data!")
        length = end.start()
        self.rawbytes = data[:length]
        self.length = length - 2
        return length - 2
    
def parse_jpg(data):
    """
    Parses the raw bytes of a JPG file to extract a list of all its Segments.

    :param data: bytes
    :return: list[Segment]
    """
    segments = []
    pos = 0
    while pos < len(data):
        try:
            seg = Segment(data[pos:], start=pos)
        except KeyError as e:
            # NOTE: this is *a* way to end the process, though we could check
            #   for an EOI marker instead
            #   this works for valid JPG files, fails "gracefully" for extended
            #   JPG files (for example, Canon and Sony like storing extra
            #   information past the EOI marker)
            # TODO: test on carved files to double check how it works with them
            print(e)
            return segments
        segments.append(seg)
        pos += seg.length + 2
    return segments

def parse_dqt(data):
    """
    Parses a DHT Segment (or raw bytes from one) to extract the quantization
    tables defined in it. Can extract multiple QTs if present.

    :param data: Segment or bytes
    :return: tuple of tuples[ int, int, list[list[int]] ]
    """
    if isinstance(data, Segment):
        data = data.rawbytes
    #code, length, qtinfo = struct.unpack(">2sHB", data[:5])
    ret = []
    pos = 4
    while pos < len(data):
        qtinfo = data[pos]
        qtp = qtinfo >> 4
        qtnum = qtinfo & 0b00001111
        if qtp not in {0, 1}:
            raise ValueError("Corrupt DQT! Precision not 0 or 1")

        if qtp == 0:
            table = struct.unpack(">64B", data[pos + 1: pos + 65])
        else:
            table = struct.unpack(">64H", data[pos + 1: pos + 65])
        pos += 1 + (qtp + 1) * 64
        ret.append((
            qtnum,
            qtp,
            [ list(table[i: i + 8]) for i in range(0, 64, 8) ]
        ))
    return ret

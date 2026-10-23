import struct

class Segment:
    def __init__(self, rawbytes, *, start=0, length=0):
        self.rawbytes = rawbytes
        self.data = b""
        self.start = start
        self.length = length
        # set the attributes
        self.pattern = b""
        self.ver = 0
        self.htype = 0
        self.granule = 0
        self.bsn = 0
        self.psn = 0
        self.crc = 0
        self.psegments = 0
        self.segment_table = []
        self.segments = []
        self.parse()

    def __repr__(self):
        return (
            f"< {self.__class__.__qualname__}"
            f" {self.pattern}"
            f" {self.htype}"
            f" start={self.start}"
            f" length={self.length}"
            f" >"
        )

    def __str__(self):
            return (
                f"< {self.__class__.__qualname__}"
                f" pattern: {self.pattern}"
                f" htype: {self.htype}"
                f" bsn: {self.bsn}"
                f" psn: {self.psn}"
                f" segment_table: {self.segment_table}"
                f" start={self.start}"
                f" length={self.length}"
                f" >"
            )

    def parse(self):
        data = self.rawbytes
        pattern, ver, htype, granule, bsn, psn, crc, psegments = \
            struct.unpack(">4sBBQLLLB", data[:27])
        self.pattern = pattern
        self.ver = ver
        self.htype = htype
        self.granule = granule
        self.bsn = bsn
        self.psn = psn
        self.crc = crc
        self.psegments = psegments
        self.segment_table = []
        self.segment_table = struct.unpack_from(">" + psegments * "B", data, offset=27)
        self.length = 27 + psegments + sum(self.segment_table)



def parse(data):
    segments = []
    pos = 0
    while ( pos := data.find(b"OggS", pos) ) != -1:
        try:
            seg = Segment(data[pos:], start=pos)
        except Exception as e:
            print(e)
            return segments
        segments.append(seg)
        pos += 1
    return segments

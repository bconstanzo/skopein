import struct

class Page:
    def __init__(self, rawbytes, *, start=0, length=0, debug=False):
        """
        Structure for an OGG/Opus Page, that inside contains segments.

        :param rawbytes: the bytes read from a file. One page is parsed at a
            time. If multiple pages must be read, different Page objects have
            to be instantiated.
        :param start: (keyword only, 0) start position of the Page in the file
        :param length: (keyword only, 0) unused, it gets overwritten on the 
            self.parse() call at the end of __init__
        :param debug: (keyword only, False) turns on debug printing/complaining
        """
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
        self.opus_tags = ()
        self.parse(debug=debug)

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
            return "\n".join( e for e in [
                f"< {self.__class__.__qualname__}",
                f"     pattern: {self.pattern}, htype: {self.htype}",
                f"     bsn: {self.bsn}, psn: {self.psn}",
                f"     start={self.start}, length={self.length}",
                f"     tags={self.opus_tags}" if self.opus_tags else None,
                f" >",
            ] if e)

    def parse(self, *, debug=False):
        """
        Parses the rawbytes used to instantiate the Page. Called at the end of
        __init__ to parse the byte structure.

        :param debug: (keyword only, False) turns on debug printing/complaining
        """
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
        sbase = 27 + psegments
        for slen in self.segment_table:
            segment = data[sbase: sbase + slen]
            self.segments.append( segment )
            sbase += slen
        self.data = b"".join(self.segments)
        if self.data.startswith(b"OpusTags"):
            self.opus_tags = _opustags(self.data)



def parse(data, *, debug=False):
    """
    Parses a stream of bytes into OGG/Opus Pages.

    :param data: bytes to be parsed
    :param debug: (keyword only, False) turns on debug printing/complaining
    """
    segments = []
    pos = 0
    while ( pos := data.find(b"OggS", pos) ) != -1:
        try:
            seg = Page(data[pos:], start=pos, debug=debug)
        except Exception as e:
            print(e)
            return segments
        segments.append(seg)
        pos += 1
    return segments

def _opustags(data):
    header, enclen = struct.unpack_from("<8sL", data)
    encoder = data[12: 12 + enclen].decode("utf-8")
    tag_base = 12 + enclen
    num_tags, = struct.unpack("<L", data[tag_base : tag_base + 4])
    tag_base += 4
    tags = []
    for i in range(num_tags):
        taglen, = struct.unpack("<L", data[tag_base:tag_base+4])
        tag_base += 4
        tag = data[tag_base: tag_base + taglen].decode("utf-8")
        tag_base += taglen
        tags.append(tag)
    return encoder, tags

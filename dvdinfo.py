
from collections import namedtuple

AudioTrack = namedtuple('AudioTrack', 'num, desc, lang, sr, rate')
SubtitleTrack = namedtuple('SubtitleTrack', 'num, desc, lang, format, src_name')
Chapter = namedtuple('Chapter', 'num, cell_start, cell_end, block_count, duration')


class Title(object):
    def __init__(self):
        pass
    
    
class DvdInfo(object):
    pass


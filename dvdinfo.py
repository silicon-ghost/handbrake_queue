
from collections import namedtuple

AudioTrack = namedtuple('AudioTrack', 'num, desc, lang, sr, rate')
SubtitleTrack = namedtuple('SubtitleTrack', 'num, desc, lang, format, src_name')
Chapter = namedtuple('Chapter', 'num, cell_start, cell_end, block_count, duration')


class Title(object):
    def __init__(self):
        self.num = None
        self.duration = None
        self.fps = None
        self.audio_tracks = list()
        self.subtitle_tracks = list()
        self.chapters = list()
    
    def add_audio_track(self, track):
        self.audio_tracks.append(track)
    
    def add_subtitle_track(self, track):
        self.subtitle_tracks.append(track)
    
    def add_chapter(self, chapter):
        self.chapters.append(chapter)
        
    
    
    
class DvdInfo(object):
    def __init__(self):
        self.titles = list()

    def add_title(self, title):
        self.titles.append(title)


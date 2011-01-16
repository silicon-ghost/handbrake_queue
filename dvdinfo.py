from collections import namedtuple

AudioTrack = namedtuple('AudioTrack', 'num, desc, lang, sr, rate, enabled')
SubtitleTrack = namedtuple('SubtitleTrack', 'num, desc, lang, format, src_name, enabled')
Chapter = namedtuple('Chapter', 'num, cell_start, cell_end, block_count, duration, enabled')


class Title(object):
    def __init__(self, num=None, duration=None, fps=None, audio_tracks=None, subtitle_tracks=None, chapters=None, enabled=True):
        self.num = num
        self.duration = duration
        self.fps = fps
        self.audio_tracks = audio_tracks or list()
        self.subtitle_tracks = subtitle_tracks or list()
        self.chapters = chapters or list()
        self.enabled = enabled
    
    def add_audio_track(self, track):
        self.audio_tracks.append(track)
    
    def add_subtitle_track(self, track):
        self.subtitle_tracks.append(track)
    
    def add_chapter(self, chapter):
        self.chapters.append(chapter)
    
    def SimilarToTitle(self, title):
        """Returns True if this Title has equal contents to title, ignoring 'num' and 'enabled' fields."""
        return (self.duration == title.duration and 
            self.fps == title.fps and 
            self.audio_tracks == title.audio_tracks and
            self.subtitle_tracks == title.subtitle_tracks and
            self.chapters == title.chapters)
    
    def __repr__(self):
        return ''.join(('Title(num=', repr(self.num), ',\n\tduration=', repr(self.duration), ',\n\tfps=', repr(self.fps),
            ',\n\taudio_tracks=[', ',\n\t\t'.join(repr(x) for x in self.audio_tracks), 
            '],\n\tsubtitle_tracks=[', ',\n\t\t'.join(repr(x) for x in self.subtitle_tracks), 
            '],\n\tchapters=[', ',\n\t\t'.join(repr(x) for x in self.chapters), 
            '],\n\tenabled=', repr(self.enabled), ')\n'))
    
    
class DvdInfo(object):
    def __init__(self, titles=None):
        self.titles = titles or list()

    def add_title(self, title):
        self.titles.append(title)
        
    def __repr__(self):
        return 'DvdInfo(' + repr(self.titles) + ')\n'


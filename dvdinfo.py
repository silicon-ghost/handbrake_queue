"""dvdinfo.py - Classes for describing the content of a DVD"""
from collections import namedtuple


AudioTrack = namedtuple('AudioTrack', 
                        'num, desc, lang, sr, rate, enabled')

SubtitleTrack = namedtuple('SubtitleTrack', 
                           'num, desc, lang, format, src_name, enabled')

Chapter = namedtuple('Chapter', 
                     'num, cell_start, cell_end, block_count, duration, enabled')


class Title(object):
    """Describes a single title on a DVD"""
    def __init__(self, num=None, duration=None, fps=None, audio_tracks=None, subtitle_tracks=None, 
                 chapters=None, enabled=True):
        self.num = num
        self.duration = duration
        self.fps = fps
        self.audio_tracks = audio_tracks or list()
        self.subtitle_tracks = subtitle_tracks or list()
        self.chapters = chapters or list()
        self.enabled = enabled
    
    def AddAudioTrack(self, track):
        """Add track to list of audio tracks"""
        self.audio_tracks.append(track)
    
    def AddSubtitleTrack(self, track):
        """Add track to list of subtitle tracks"""
        self.subtitle_tracks.append(track)
    
    def AddChapter(self, chapter):
        """Add chapter to list of chapters"""
        self.chapters.append(chapter)
    
    def SimilarToTitle(self, title):
        """Returns True if this Title has equal contents to title, ignoring 'num' and 'enabled' fields."""
        return (self.duration == title.duration and 
            self.fps == title.fps and 
            self.audio_tracks == title.audio_tracks and
            self.subtitle_tracks == title.subtitle_tracks and
            self.chapters == title.chapters)
    
    def __repr__(self):
        return ''.join(('Title(num=', repr(self.num), ',\n\tduration=', repr(self.duration), 
            ',\n\tfps=', repr(self.fps),
            ',\n\taudio_tracks=[', ',\n\t\t'.join(repr(x) for x in self.audio_tracks), 
            '],\n\tsubtitle_tracks=[', ',\n\t\t'.join(repr(x) for x in self.subtitle_tracks), 
            '],\n\tchapters=[', ',\n\t\t'.join(repr(x) for x in self.chapters), 
            '],\n\tenabled=', repr(self.enabled), ')\n'))
    
    
class DvdInfo(object):
    """Describes the content of a single DVD"""
    def __init__(self, titles=None, folder=None):
        self.titles = titles or list()
        self.folder = folder or list()

    def AddTitle(self, title):
        """Add a Title to list of titles"""
        self.titles.append(title)
        
    def __repr__(self):
        return 'DvdInfo(' + repr(self.titles) + ', ' + repr(self.folder) + ')\n'


"""dvdinfo.py - Classes for describing the content of a DVD"""
from collections import namedtuple
import re
import xml.etree.ElementTree as et
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom.minidom import parseString



AudioTrack = namedtuple('AudioTrack', 
                        'num, desc, lang, sr, rate, enabled')

SubtitleTrack = namedtuple('SubtitleTrack', 
                           'num, desc, lang, format, src_name, enabled')

Chapter = namedtuple('Chapter', 
                     'num, cell_start, cell_end, block_count, duration, enabled')


class Title(object):
    """Describes a single title on a DVD"""
    def __init__(self, num=None, duration=None, fps=None, num_blocks=None, audio_tracks=None, 
                 subtitle_tracks=None, chapters=None, enabled=True, eps_type=None, 
                 eps_start_num=None, eps_end_num=None):
        self.num = num
        self.duration = duration
        self.fps = fps
        self.num_blocks = num_blocks
        self.audio_tracks = audio_tracks or list()
        self.subtitle_tracks = subtitle_tracks or list()
        self.chapters = chapters or list()
        self.enabled = enabled
        self.eps_type = eps_type
        self.eps_start_num = eps_start_num
        self.eps_end_num = eps_end_num
    
    def EmitXML(self):
        """Generates XML fragment stresenting this object"""
        title_elem = Element('title', 
                        attrib=dict(enabled=str(self.enabled), eps_type=str(self.eps_type), 
                                    eps_start_num=str(self.eps_start_num), 
                                    eps_end_num=str(self.eps_end_num)))
        SubElement(title_elem, 'num').text = str(self.num)
        SubElement(title_elem, 'duration').text = str(self.duration)
        SubElement(title_elem, 'fps').text = str(self.fps)
        SubElement(title_elem, 'num_blocks').text = str(self.num_blocks)
        audio_tracks_elem = SubElement(title_elem, 'audio_tracks')
        for track in self.audio_tracks:
            track_elem = SubElement(audio_tracks_elem, 'track', attrib=dict(enabled=str(track.enabled)))
            SubElement(track_elem, 'num').text = str(track.num)
            SubElement(track_elem, 'desc').text = str(track.desc)
            SubElement(track_elem, 'lang').text = str(track.lang)
            SubElement(track_elem, 'sr').text = str(track.sr)
            SubElement(track_elem, 'rate').text = str(track.rate)
        subtitle_tracks_elem = SubElement(title_elem, 'subtitle_tracks')
        for track in self.subtitle_tracks:
            track_elem = SubElement(subtitle_tracks_elem, 'track', attrib=dict(enabled=str(track.enabled)))
            SubElement(track_elem, 'num').text = str(track.num)
            SubElement(track_elem, 'desc').text = str(track.desc)
            SubElement(track_elem, 'lang').text = str(track.lang)
            SubElement(track_elem, 'format').text = str(track.format)
            SubElement(track_elem, 'src_name').text = str(track.src_name)
        chapters_elem = SubElement(title_elem, 'chapters')
        for chapter in self.chapters:
            chapter_elem = SubElement(chapters_elem, 'chapter', attrib=dict(enabled=str(chapter.enabled)))
            SubElement(chapter_elem, 'num').text = str(chapter.num)
            SubElement(chapter_elem, 'cell_start').text = str(chapter.cell_start)
            SubElement(chapter_elem, 'cell_end').text = str(chapter.cell_end)
            SubElement(chapter_elem, 'block_count').text = str(chapter.block_count)
            SubElement(chapter_elem, 'duration').text = str(chapter.duration)
        
        return title_elem
    
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
            ',\n\tnum_blocks=', repr(self.num_blocks),
            ',\n\taudio_tracks=[', ',\n\t\t'.join(repr(x) for x in self.audio_tracks), 
            '],\n\tsubtitle_tracks=[', ',\n\t\t'.join(repr(x) for x in self.subtitle_tracks), 
            '],\n\tchapters=[', ',\n\t\t'.join(repr(x) for x in self.chapters), 
            '],\n\tenabled=', repr(self.enabled),
            ',\n\teps_type=', repr(self.eps_type),
            ',\n\teps_start_num=', repr(self.eps_start_num),
            ',\n\teps_end_num=', repr(self.eps_end_num),
            ')\n'))
    
    
class DvdInfo(object):
    """Describes the content of a single DVD"""
    def __init__(self, titles=None, folder=None, series=None, season=None):
        self.titles = titles or list()
        self.folder = folder
        self.series = series
        self.season = season

    def EmitXML(self):
        dvd_elem = Element('dvd', 
                           attrib=dict(folder=str(self.folder), series=str(self.series), 
                                       season=str(self.season)))
        titles_elem = SubElement(dvd_elem, 'titles')
        for title in self.titles:
            titles_elem.append(title.EmitXML())
        return dvd_elem
        
    def AddTitle(self, title):
        """Add a Title to list of titles"""
        self.titles.append(title)
        
    def __repr__(self):
        return ''.join(('DvdInfo('
            'titles=', repr(self.titles),
            ',folder=', repr(self.folder),
            ',series=', repr(self.series),
            ',season=', repr(self.season),
            ')\n'))

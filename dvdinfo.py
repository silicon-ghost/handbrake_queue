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
                 eps_start_num=0, eps_end_num=0, default_audio_track=0, default_subtitle_track=0,
                 combing_detected=False):
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
        self.default_audio_track = default_audio_track
        self.default_subtitle_track = default_subtitle_track
        self.combing_detected = combing_detected
        
    def ParseXML(self, title_elem):
        assert(isinstance(title_elem, Element))
        self.default_audio_track = title_elem.attrib['default_audio_track']
        self.default_subtitle_track = title_elem.attrib['default_subtitle_track']
        self.eps_start_num = title_elem.attrib['eps_start_num']
        self.eps_end_num = title_elem.attrib['eps_end_num']
        self.eps_type = title_elem.attrib['eps_type']
        self.enabled = title_elem.attrib['enabled'] == 'True'
        self.num = int(title_elem.find('num').text)
        self.duration = int(title_elem.find('duration').text)
        self.fps = title_elem.find('fps').text
        self.num_blocks = int(title_elem.find('num_blocks').text)
        self.combing_detected = title_elem.find('combing_detected').text == 'True'
        self.audio_tracks = list()
        for track_elem in title_elem.findall('audio_tracks/track'):
            self.audio_tracks.append(AudioTrack(
                num=int(track_elem.find('num').text), 
                desc=track_elem.find('desc').text, 
                lang=track_elem.find('lang').text, 
                sr=int(track_elem.find('sr').text), 
                rate=int(track_elem.find('rate').text),
                enabled=track_elem.attrib['enabled']=='True'))
        self.subtitle_tracks = list()
        for track_elem in title_elem.findall('subtitle_tracks/track'):
            self.subtitle_tracks.append(SubtitleTrack(
                num=int(track_elem.find('num').text), 
                desc=track_elem.find('desc').text, 
                lang=track_elem.find('lang').text, 
                format=track_elem.find('format').text, 
                src_name=track_elem.find('src_name').text,
                enabled=track_elem.attrib['enabled']=='True'))
        self.chapters = list()
        for chapter_elem in title_elem.findall('chapters/chapter'):
            self.chapters.append(Chapter(
                num=int(chapter_elem.find('num').text), 
                cell_start=int(chapter_elem.find('cell_start').text), 
                cell_end=int(chapter_elem.find('cell_end').text), 
                block_count=int(chapter_elem.find('block_count').text), 
                duration=int(chapter_elem.find('duration').text), 
                enabled=chapter_elem.attrib['enabled']=='True'))
    
    def EmitXML(self):
        """Generates XML fragment stresenting this object"""
        title_elem = Element('title', 
                        attrib=dict(enabled=str(self.enabled), eps_type=str(self.eps_type), 
                                    eps_start_num=str(self.eps_start_num), 
                                    eps_end_num=str(self.eps_end_num),
                                    default_audio_track=str(self.default_audio_track),
                                    default_subtitle_track=str(self.default_subtitle_track)))
        SubElement(title_elem, 'num').text = str(self.num)
        SubElement(title_elem, 'duration').text = str(self.duration)
        SubElement(title_elem, 'fps').text = str(self.fps)
        SubElement(title_elem, 'num_blocks').text = str(self.num_blocks)
        SubElement(title_elem, 'combing_detected').text = str(self.combing_detected)
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
            ',\n\tdefault_audio_track=', repr(self.default_audio_track),
            ',\n\tdefault_subtitle_track=', repr(self.default_subtitle_track),
            ',\n\tcombing_detected=', repr(self.combing_detected),
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
        
    def ParseXML(self, dvd_elem):
        assert(isinstance(dvd_elem, Element))
        self.folder = dvd_elem.attrib['folder']
        self.series = dvd_elem.attrib['series']
        self.season = int(dvd_elem.attrib['season'])
        self.titles = list()
        for title_elem in dvd_elem.findall('titles/title'):
            title = Title()
            title.ParseXML(title_elem)
            self.titles.append(title)
    
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

def WriteDvdListToXML(dvds, filename):
    dvds_elem = et.Element('dvds') 
    for dvd in dvds:
        dvds_elem.append(dvd.EmitXML())
        
    txt = et.tostring(dvds_elem)
    text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    ugly_xml = parseString(txt).toprettyxml(indent="  ")
    
    pretty_xml = text_re.sub('>\g<1></', ugly_xml)

    f = open(filename, 'w')
    try:
        f.write(pretty_xml)
    finally:
        f.close()

def ReadDvdListFromXML(filename):
    dvds = list()
    
    tree = et.parse(filename)
    root_elem = tree.getroot()

    for dvd_elem in root_elem.findall('dvd'):
        dvd = DvdInfo()
        dvd.ParseXML(dvd_elem)
        dvds.append(dvd)
    return dvds
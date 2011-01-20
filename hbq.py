"""hbq - Command line tool for building a HandBrake Queue"""

import xml.etree.ElementTree as et
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom.minidom import parseString
from collections import namedtuple
from itertools import combinations
import argparse
import logging
import os.path
import re
from pprint import pprint, pformat
from oreillycookbook.files import all_folders
from hbscan import ParseHBOutput, ScanDvd
from dvdinfo import DvdInfo, Title

logger = logging.getLogger('hbq')

EpisodeDetails = namedtuple('EpisodeDetails', 
                            'folder, title_idx, title_num, season, eps_or_extra, eps_start_num, eps_end_num')


class TimeArgumentError(Exception):
    pass

def GetDurationInSeconds(hms_duration):
    """Returns an integer tuple of seconds from a string in MM:SS+MM:SS format"""
    try:
        (duration, variance) = hms_duration.split('+')
        duration = GetInSeconds(duration)
        variance = GetInSeconds(variance)
    except Exception:
        raise TimeArgumentError('Unable to convert the time+variance value "{}" into seconds (expect MM:SS+MM:SS)'.format(hms_duration))
    return duration, variance

def GetInSeconds(hms):
    """Returns an integer seconds value from a string in HH:MM:SS or MM:SS format"""
    factor = 1
    seconds = 0
    try:
        for x in reversed(hms.split(':')):
            seconds += int(x) * factor
            factor *= 60
    except Exception:
        raise TimeArgumentError('Unable to convert the time value "{}" into seconds'.format(hms))
    return seconds

def GetInHMS(seconds):
    """Returns a string in HH:MM:SS format from an integer seconds value"""
    hours = seconds / 3600
    seconds -= 3600 * hours
    minutes = seconds / 60
    seconds -= 60 * minutes
    if hours == 0:
        return "%02d:%02d" % (minutes, seconds)
    return "%02d:%02d:%02d" % (hours, minutes, seconds)


def ParseArguments(default_src_root_folder):
    parser = argparse.ArgumentParser(
        description='Process a series of folders, reading the DVD information, display it to stdout',
        fromfile_prefix_chars='@')
    
    subparsers = parser.add_subparsers(dest='subparser_name', help='sub-command help')
    
    parser_scan = subparsers.add_parser('scan', help='scan help', 
                                        usage='hbq.py scan root_folder [options]')
    parser_scan.add_argument(
        'root_folder', 
        nargs=1)
    parser_scan.add_argument(
        '-d', '--eps-duration', 
        dest='eps_duration', 
        nargs='+',
        default='25:00+1:00',
        metavar='MM:SS+MM:SS',
        help='A list of times (+/- variance) to be considered an episode (default: 25:00+1:00)')
    parser_scan.add_argument(
        '-t', '--title-min-duration', 
        dest='title_min_duration', 
        default='1:00',
        metavar='MM:SS',
        help='Minimum time for a title to be considered an episode or extra (default: 1:00)')
    parser_scan.add_argument(
        '--eps-start-num', 
        dest='eps_start_num',
        type=int,
        default=1,
        metavar='N',
        help='The first episode number be be used for the first season detected (default: 1)')
    parser_scan.add_argument(
        '--extras-start-num', 
        dest='extras_start_num',
        type=int,
        default=1,
        metavar='N',
        help='The first extra number be be used for the first season detected (default: 1)')
    parser_scan.add_argument(
        '-k', '--keep-dup-titles', 
        dest='remove_dup_titles', 
        action='store_const', 
        const=False,
        default=True,
        help='Keep all duplicate titles (default: False)')
    parser_scan.add_argument(
        '-v', '--keep-virtual-titles', 
        dest='remove_virtual_titles', 
        action='store_const', 
        const=False,
        default=True,
        help='Keep all virtual titles (default: False)')
    parser_scan.add_argument(
        '-2', '--no-2x-duration', 
        dest='expect_2x_duration', 
        action='store_const', 
        const=False,
        default=True,
        help='Do not double --eps-duration values to find double-length episodes (default: False)')
    parser_scan.set_defaults(command=ScanFolders)

    parser_build = subparsers.add_parser('build', help='build help')
    parser_build.add_argument('control_file', 
                              nargs='?',
                              default=r'w:\some_folder')
    parser_build.set_defaults(command=BuildQueue)
    
    
    #parser.add_argument('command', choices=('scan', 'build'))
    args = parser.parse_args()
    #pprint(args)
    #args.command()
    if args.subparser_name == 'scan':
        # convert the MM:SS and MM:SS+MM:SS argument values to seconds
        args.title_min_duration = GetInSeconds(args.title_min_duration)
        # MEZ this is a bit of a hack.  Is there a more Pythonistic way to ensure I have an iterable from a string
        if not isinstance(args.eps_duration, list):
            args.eps_duration = (args.eps_duration,)
        args.eps_duration = [GetDurationInSeconds(duration) for duration in args.eps_duration]
    #pprint(args)
    return args

def ScanFolders(args):
    """
    Implements command line 'scan' arg
    
    Scans the folder provided and builds an XML output file
    """
    # Create 2x episode duration tuple
    eps_durations = args.eps_duration
    if args.expect_2x_duration:
        eps_2x_durations = tuple((duration * 2, variance * 2) 
                                 for duration, variance in eps_durations)
    else:
        eps_2x_durations = None
        
    episodes = list()
    eps_start_num = args.eps_start_num
    extras_start_num = args.extras_start_num
    previous_season = None

    episodes = EpisodeDetector(eps_start_num, extras_start_num, args.remove_dup_titles, 
                               args.remove_virtual_titles, args.title_min_duration,
                               eps_durations, eps_2x_durations)
    
    episodes.ProcessFolder(args.root_folder[0])

def BuildQueue(args):
    print('BuildQueue() not implemented')

class DvdNameError(Exception):
    pass

class EpisodeDetector(object):
    def __init__(self, eps_start_num, extras_start_num, remove_dup_titles, remove_virtual_titles, 
                 title_min_duration, eps_durations, eps_2x_durations):
        self.eps_start_num = eps_start_num
        self.extras_start_num = extras_start_num
        self.remove_dup_titles = remove_dup_titles
        self.remove_virtual_titles = remove_virtual_titles
        self.title_min_duration = title_min_duration
        self.eps_durations = eps_durations
        self.eps_2x_durations = eps_2x_durations
        self.previous_season = None
        self.previous_series = None
        self.curr_dvd = None
        self.dvds = list()
        
    def ProcessFolder(self, folder):
        """
        Process the given folder for DVD content.
        If the folder does not contain DVD content, recurse into subfolders.
        """
        logger.info('Searching folder: %s', folder)
        if (os.path.exists(os.path.join(folder, 'VIDEO_TS')) or 
            os.path.exists(os.path.join(folder, 'VIDEO_TS.IFO'))):
            # Process this folder
            basename = os.path.basename(folder)
            match = re.search('(.+?)_?[sS](\d+)_?[dD](\d+)', basename)
            if match:
                series = match.group(1)
                season = int(match.group(2))
                disc = int(match.group(3))
                logger.info('series = "%s", season = %d, disc = %d', series, season, disc)
                
                if (self.previous_season and season != self.previous_season or
                    self.previous_series and series != self.previous_series):
                    # Restart the episode numbering
                    self.eps_start_num = 1
                    self.extras_start_num = 1
                
                raw = ScanDvd(folder)
                self.curr_dvd = ParseHBOutput(raw)
                self.curr_dvd.folder = folder
                self.curr_dvd.series = series
                self.curr_dvd.season = season
                
                if self.remove_dup_titles:
                    self.RemoveDuplicateTitles()
                self.RemoveShortTitles()
                if self.remove_virtual_titles:
                    self.RemoveVirtualTitles()
                    
                # Report summary of durations kept/rejected
                active_durations = [x.duration for x in self.curr_dvd.titles if x.enabled]
                active_duration_total = sum(active_durations)
                inactive_durations = [x.duration for x in self.curr_dvd.titles if not x.enabled]
                inactive_duration_total = sum(inactive_durations)
                logger.info('*** %d active titles with total playtime of %s '
                            '(%d inactive titles with playtime of %s) ***',
                            len(active_durations), GetInHMS(active_duration_total),
                            len(inactive_durations), GetInHMS(inactive_duration_total))
                
                self.FindEpisodesAndExtras()
                self.EnableAudioAndSubtitleTracks()
                self.dvds.append(self.curr_dvd)
                logger.debug(pformat(self.curr_dvd))
                
                self.previous_season = season
                self.previous_series = series
                    
            else:
                raise DvdNameError("Unable to parse folder name '{}'".format(folder))
        else:
            for sub_folder in sorted(all_folders(folder, single_level=True)):
                self.ProcessFolder(sub_folder)

    def RemoveDuplicateTitles(self):
        """Clears the enabled flag for any Titles that appear to be duplicates of earlier Titles on this DVD"""
        for j, src_title in enumerate(self.curr_dvd.titles):
            if src_title.enabled:
                for title in self.curr_dvd.titles[j+1:]:
                    if title.enabled and src_title.SimilarToTitle(title):
                        title.enabled = False
                        title.eps_type = 'duplicate'
                        logger.debug('Title #%d appears to be a duplicate of Title #%d', 
                                    title.num, src_title.num)

    def RemoveShortTitles(self):
        """Clears the enabled flag for any Titles shorter than title_min_duration"""
        assert(isinstance(self.curr_dvd, DvdInfo))
        for title in self.curr_dvd.titles:
            if title.enabled and title.duration < self.title_min_duration:
                title.enabled = False
                title.eps_type = 'too short'
                logger.debug('Removed Title #%d for duration shorter than %d seconds', 
                             title.num, self.title_min_duration)
                
    def RemoveVirtualTitles(self):
        """
        Remove Titles that appear to be combinations of other active Titles.
        These Titles are often all of the episodes combined into a single Title.
        """
        for title in self.curr_dvd.titles:
            assert(isinstance(title, Title))
            if not title.enabled:
                pass
            # Get num_blocks for all other active titles
            match = None
            other_titles = [(x.num, x.num_blocks) for x in self.curr_dvd.titles 
                            if x.enabled and x.num != title.num]
            # Process all combinations of other titles, taken r at a time, up to all titles
            for r in range(2, len(other_titles) + 1):
                for c in combinations(other_titles, r):
                    num_blocks = sum(x[1] for x in c)
                    if num_blocks == title.num_blocks:
                        match = c
                        break
                if match:
                    break
            
            if match:
                title.enabled = False
                title.eps_type = 'virtual'
                logger.debug('Removed Title #%d for being a virtual match by block count to titles %s', 
                             title.num, pformat([x[0] for x in c]))

    def EnableAudioAndSubtitleTracks(self, langs=('eng', 'unk')):
        """Enable audio and subtitle tracks with a language in langs"""
        assert(isinstance(self.curr_dvd, DvdInfo))
        for title in self.curr_dvd.titles:
            assert(isinstance(title, Title))
            for i, track in enumerate(title.audio_tracks):
                if track.lang in langs:
                    title.audio_tracks[i] = track._replace(enabled=True)
            for i, track in enumerate(title.subtitle_tracks):
                if track.lang in langs:
                    title.subtitle_tracks[i] = track._replace(enabled=True)

    def FindEpisodesAndExtras(self):
        """Finds and assigns episode/extras numbers to active Titles on this DVD"""
        assert(isinstance(self.curr_dvd, DvdInfo))
        for title in self.curr_dvd.titles:
            assert(isinstance(title, Title))
            if not title.enabled:
                continue
            is_episode = any((duration - variance) < title.duration < (duration + variance) 
                             for duration, variance in self.eps_durations)
            is_2x_episode = any((duration - variance) < title.duration < (duration + variance) 
                                for duration, variance in self.eps_2x_durations)
            if is_episode:
                logger.info('Title #%2d is episode "S%02dE%02d", duration %s', 
                            title.num, self.curr_dvd.season, self.eps_start_num, GetInHMS(title.duration))
                title.eps_type = 'episode'
                title.eps_start_num = self.eps_start_num
                title.eps_end_num = self.eps_start_num
                self.eps_start_num += 1
            elif is_2x_episode:
                logger.info('Title #%2d is episode "S%02dE%02dE%02d", duration %s', 
                            title.num, self.curr_dvd.season, self.eps_start_num, self.eps_start_num + 1, 
                            GetInHMS(title.duration))
                title.eps_type = 'episode'
                title.eps_start_num = self.eps_start_num
                title.eps_end_num = self.eps_start_num + 1
                self.eps_start_num += 2
            else:
                logger.info('Title #%2d is extras  "S%02dExtras%02d", duration %s', 
                            title.num, self.curr_dvd.season, self.extras_start_num, GetInHMS(title.duration))
                title.eps_type = 'extra'
                title.eps_start_num = self.extras_start_num
                title.eps_end_num = self.extras_start_num
                self.extras_start_num += 1
        
def main():
    default_src_root_folder = r'\\Archer\archer_s\_video_raw'
    dst_root_folder = 'W:\\video_handbrake\\'

    args = ParseArguments(default_src_root_folder)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)5s - %(module)s:%(lineno)03d[%(funcName)s()] - %(message)s')
    # create info file handler
    fh = logging.FileHandler(filename='hbq_info.log')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # create debug file handler
    fh = logging.FileHandler(filename='hbq_debug.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # set overall logging detail here
    logger.setLevel(logging.DEBUG)

    args.command(args)    
    
    return

    
            
def hbq_ex1():
    src_root_folder = 'W:\\_video_raw\\'
    dst_root_folder = 'W:\\video_handbrake\\'
    
    cq = 20.0
    basename = 'MASH'
    season = 1
    num_eps = 24
    num_eps_per_disc = 8
    job_start = 220
    audio_tracks_val = (2, 1)
    audio_tracks = ",".join([str(x) for x in audio_tracks_val])
    audio_encoders = ",".join(["ac3" for x in audio_tracks_val])
    subtitles_val = (1, 4)
    subtitles = ",".join([str(x) for x in subtitles_val])
    default_subtitle = 4
    
    root = Element('ArrayOfJob')
    for eps in range(num_eps):
        cfg = {}
        cfg['cq'] = cq
        cfg['title_num'] = (eps % num_eps_per_disc) + 1
        cfg['disc_num'] = (eps / num_eps_per_disc) + 1
        cfg['src_folder'] = '{0}{1}S{2}D{3}'.format(src_root_folder, basename, season, cfg['disc_num'])
        cfg['destination'] = '{0}MASH S{1:02d}E{2:02d}.mkv'.format(dst_root_folder, season, eps + 1)
        cfg['audio_tracks'] = audio_tracks
        cfg['audio_encoders'] = audio_encoders
        cfg['subtitles'] = subtitles
        cfg['default_subtitle'] = default_subtitle
        job = Element('Job')
        SubElement(job, 'Id').text = '{:d}'.format(job_start + eps)
        SubElement(job, 'Title').text = '{:d}'.format(cfg['title_num'])
        SubElement(job, 'Query').text = (
            ' -i "{src_folder}"'
            ' -t {title_num}'
            ' --angle 1'
            ' -o "{destination}"'
            ' -f mkv'
            ' --detelecine --decomb --denoise="weak"'
            ' -w 720 --loose-anamorphic'
            ' -e x264 -q {cq}'
            ' -a {audio_tracks} -E {audio_encoders}'
            ' --subtitle {subtitles} --subtitle-default={default_subtitle}'
            ' -m'
            ' -x ref=5:bframes=5:subq=9:mixed-refs=0:8x8dct=1:trellis=2:b-pyramid=1:me=umh:merange=32:analyse=all'
            ' -v 2'.format(**cfg))
        SubElement(job, 'CustomQuery').text = 'false'
        SubElement(job, 'Source').text = cfg['src_folder']
        SubElement(job, 'Destination').text = cfg['destination']
        root.append(job)
    
    
    txt = et.tostring(root)
    ugly_xml = parseString(txt).toprettyxml(indent="  ")
    text_re = re.compile('>\n\s+([^<>\s].*?)\n\s+</', re.DOTALL)
    pretty_xml = text_re.sub('>\g<1></', ugly_xml)
    
    fid = open(r'W:\mash_test1.queue', 'w')
    try:
        fid.write(pretty_xml)
    finally:
        fid.close()


        
        
if __name__ == '__main__':
    main()
    
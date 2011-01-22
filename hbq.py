"""hbq - Command line tool for building a HandBrake Queue"""
# Python modules
import argparse
import logging
import logging.config
import os.path
from pprint import pprint, pformat
import re
import xml.etree.ElementTree as et
from xml.dom.minidom import parseString
import yaml
# Personal library modules
from oreillycookbook.files import all_folders
# Project modules
from eps_detector import EpisodeDetector
from time_util import GetInSeconds, GetDurationInSeconds
from dvdinfo import WriteDvdListToXML, ReadDvdListFromXML

logger = logging.getLogger('hbq')


def ParseArguments():
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
        '-f', '--xml-output-filename', 
        dest='xml_filename', 
        nargs=1,
        default='',
        metavar='FILE',
        help='Filename to write scan results to (default: basename(<root_folder>).xml)')
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
        '--no-default-close-captions', 
        dest='default_close_captions', 
        action='store_const', 
        const=False,
        default=True,
        help='Do not default subtitles to Closed Captions (default: False)')
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
                              nargs='+')
    parser_build.set_defaults(command=BuildQueue)
    
    args = parser.parse_args()
    
    return args


def ScanFolders(args):
    """
    Implements command line 'scan' arg
    
    Scans the folder provided and builds an XML output file
    """
    # convert the MM:SS and MM:SS+MM:SS argument values to seconds
    args.title_min_duration = GetInSeconds(args.title_min_duration)
    # MEZ this is a bit of a hack.  Is there a more Pythonistic way to ensure I have an iterable from a string
    if not isinstance(args.eps_duration, list):
        args.eps_duration = (args.eps_duration,)
    args.eps_duration = [GetDurationInSeconds(duration) for duration in args.eps_duration]

    root_folder = os.path.abspath(args.root_folder[0])
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
                               eps_durations, eps_2x_durations, args.default_close_captions)
    
    episodes.ProcessFolder(root_folder)
    if not args.xml_filename:
        xml_filename = os.path.basename(root_folder)
        xml_filename = xml_filename or 'hbq'
        xml_filename = xml_filename + '.xml'
    else:
        xml_filename = args.xml_filename[0]
        
    WriteDvdListToXML(episodes.dvds, xml_filename)

    
def BuildQueue(args):
    xml_filename = args.control_file[0]
    dvds = ReadDvdListFromXML(xml_filename)
    #pprint(dvds)
    WriteDvdListToXML(dvds, 'test.xml')

logging_conf = """
version: 1
formatters:
    simple:
        format: "%(asctime)s - %(levelname)5s - %(message)s"
    precise:
        format: "%(asctime)s - %(levelname)5s - %(module)s:%(lineno)03d[%(funcName)s()] - %(message)s"
handlers:
    console:
        class: logging.StreamHandler
        level: INFO
        formatter: simple
        stream: ext://sys.stdout
    info_file:
        class: logging.FileHandler
        level: INFO
        filename: hbq_info.log
        formatter: simple
    debug_file:
        class: logging.FileHandler
        level: DEBUG
        filename: hbq_debug.log
        formatter: precise
loggers:
    hbq:
        level: DEBUG
        handlers: [console, info_file, debug_file]
    eps_detector:
        level: DEBUG
        handlers: [console, info_file, debug_file]
"""
"""
root:
    level: DEBUG
    handlers: [console, info_file, debug_file]
"""

def main():
    args = ParseArguments()
    
    logging_dict = yaml.load(logging_conf)
    logging.config.dictConfig(logging_dict)
    
    args.command(args)    

    
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
    
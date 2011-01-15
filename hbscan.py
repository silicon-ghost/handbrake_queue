import re
import subprocess
import time
import logging
from cStringIO import StringIO
from oreillycookbook.files import all_folders
import argparse
from pprint import pprint

from dvdinfo import DvdInfo, Title, SubtitleTrack, AudioTrack, Chapter

logger = logging.getLogger('hbscan')    

TRANSCODER = 'C:\\Program Files (x86)\\Handbrake\\HandBrakeCLI.exe'

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

class ParseException(Exception):
    pass

class HandbrakeTitleParser(object):
    pass

STATES = enum('ReadLine', 'Scanning', 
              'TitleStart', 'InTitle', 'TitleEnd', 
              'ChaptersStart', 'InChapters', 'ChaptersEnd', 
              'AudioTracksStart', 'InAudioTracks', 'AudioTracksEnd',
              'SubtitleTracksStart', 'InSubtitleTracks', 'SubtitleTracksEnd',
              'Done')
    

def parseOutput(src):
    assert isinstance(src, str)
    s = StringIO(src)
    line_num = 0
    states = list()
    states.append(STATES.Scanning)
    states.append(STATES.ReadLine)
    
    dvd = DvdInfo()    
    while 1:
        state = states.pop()
        if state == STATES.ReadLine:
            line = s.readline()
            line_num += 1
            assert isinstance(line, str)
            if line != '':
                line = line.rstrip()
            else:
                states.append(STATES.Done)
                
        elif state == STATES.Scanning:
            #print('{:03d}: Scanning'.format(line_num))
            if line.startswith('+ title'):
                states.append(STATES.TitleStart)
            else:
                states.append(STATES.Scanning)
                states.append(STATES.ReadLine)
        
        elif state == STATES.TitleStart:
            logger.debug('%03d: Title Start', line_num)
            # Initialize a new title here
            title = Title()
            match = re.search('(?<=\+ title )\d+(?=:)', line)
            if match:
                title_num = int(match.group())
                logger.info('%03d: Found title #%d', line_num, title_num)
                title.num = title_num
                states.append(STATES.InTitle)
                states.append(STATES.ReadLine)
               
            else:
                raise ParseException('Unable to parse title number')
                
        elif state == STATES.InTitle:
            #print('{:03d}: In Title'.format(line_num))
            if line.startswith('+'):
                states.append(STATES.TitleEnd)
            elif line.startswith('  + chapters:'):
                states.append(STATES.InTitle)
                states.append(STATES.ChaptersStart)
            elif line.startswith('  + audio tracks:'):
                states.append(STATES.InTitle)
                states.append(STATES.AudioTracksStart)
            elif line.startswith('  + subtitle tracks:'):
                states.append(STATES.InTitle)
                states.append(STATES.SubtitleTracksStart)
            else:
                match = re.search('(?<=\+ duration: )(\d\d):(\d\d):(\d\d)', line)
                if match:
                    duration_str = match.group()
                    title.duration = int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
                    logger.info('%03d: Found duration %s (%d s)', line_num, duration_str, title.duration)
                    states.append(STATES.InTitle)
                    states.append(STATES.ReadLine)
                    continue
                match = re.search('\+ size: ([^,]+), pixel aspect: ([^,]+), display aspect: ([^,]+), ([0-9]*\.?[0-9]+) fps', line)
                if match:
                    title.fps = match.group(4)
                    logger.info('%03d: Found fps %s', line_num, title.fps)
                    states.append(STATES.InTitle)
                    states.append(STATES.ReadLine)
                    continue
                states.append(STATES.InTitle)
                states.append(STATES.ReadLine)
        
        elif state == STATES.TitleEnd:
            logger.debug('%03d: Title End', line_num)
            # Finalize title here
            dvd.add_title(title)
            states.append(STATES.Scanning)
            
        elif state == STATES.ChaptersStart:
            logger.debug('%03d: Chapters Start', line_num)
            
            states.append(STATES.InChapters)
            states.append(STATES.ReadLine)
            
        elif state == STATES.InChapters:
            logger.debug('%03d: In Chapters', line_num)
            if line.startswith('    +'):
                match = re.search('\+ (\d+): cells (\d+)->(\d+), (\d+) blocks, duration (\d\d):(\d\d):(\d\d)', line)
                if match:
                    chapter = Chapter(
                        num=int(match.group(1)), 
                        cell_start=int(match.group(2)), 
                        cell_end=int(match.group(3)), 
                        block_count=int(match.group(4)), 
                        duration=int(match.group(5)) * 3600 + int(match.group(6)) * 60 + int(match.group(7)))
                    
                    # Add chapter
                    logger.info('%03d: Found chapter #%d, cells %d->%d, %d blocks, %d seconds', line_num, chapter.num, chapter.cell_start, chapter.cell_end, chapter.block_count, chapter.duration)
                    title.add_chapter(chapter)
                else:
                    logger.error('%03d: Error Parsing Chapter Info: "%s"', line_num, line)
                    
                states.append(STATES.InChapters)
                states.append(STATES.ReadLine)
            else:
                states.append(STATES.ChaptersEnd)
            
        elif state == STATES.ChaptersEnd:
            logger.debug('%03d: Chapters End', line_num)


        elif state == STATES.AudioTracksStart:
            logger.debug('%03d: Audio Tracks Start', line_num)
            
            states.append(STATES.InAudioTracks)
            states.append(STATES.ReadLine)
            
        elif state == STATES.InAudioTracks:
            logger.debug('%03d: In Audio Tracks', line_num)
            if line.startswith('    +'):
                # There are 2 possible HB audio track formats
                match1 = re.search('\+ (\d+), (.+?) \(iso639-2: ([^)]+)\), (\d+)Hz, (\d+)bps', line)
                match2 = re.search('\+ (\d+), (.+?) \(iso639-2: ([^)]+)\)', line)
                if match1:
                    track_num = int(match1.group(1))
                    track_desc = match1.group(2)
                    track_lang = match1.group(3)
                    track_sr = int(match1.group(4))
                    track_rate = int(match1.group(5))
                    # Add audio track
                    logger.info('%03d: Found audio track #%d, desc="%s", language="%s", sr=%dHz, bps=%dbps', line_num, track_num, track_desc, track_lang, track_sr, track_rate)
                elif match2:
                    # Try alternate HB format
                    track_num = int(match1.group(1))
                    track_desc = match1.group(2)
                    track_lang = match1.group(3)
                    track_sr = 0
                    track_rate = 0
                    # Add audio track
                    logger.info('%03d: Found audio track #%d, desc="%s", language="%s" (no rate information)', line_num, track_num, track_desc, track_lang)
                    
                else:
                    logger.error('%03d: Error Parsing Audio Track Info: "%s"', line_num, line)
                    
                                    
                states.append(STATES.InAudioTracks)
                states.append(STATES.ReadLine)
            else:
                states.append(STATES.AudioTracksEnd)
                

            
        elif state == STATES.AudioTracksEnd:
            logger.debug('%03d: Audio Tracks End', line_num)

        elif state == STATES.SubtitleTracksStart:
            logger.debug('%03d: Subtitle Tracks Start', line_num)
            
            states.append(STATES.InSubtitleTracks)
            states.append(STATES.ReadLine)
            
        elif state == STATES.InSubtitleTracks:
            logger.debug('%03d: In Subtitle Tracks', line_num)
            if line.startswith('    +'):
                match = re.search('\+ (\d+), (.+) \(iso639-2: ([^)]+)\) \((Bitmap|Text)\)\(([^)]+)\)', line)
                if match:
                    track_num = int(match.group(1))
                    track_desc = match.group(2)
                    track_lang = match.group(3)
                    track_format = match.group(4)
                    track_src_name = match.group(5)
                    # Add subtitle track
                    logger.info('%03d: Found subtitle #%d, desc="%s", language="%s", format="%s", src_name="%s"', line_num, track_num, track_desc, track_lang, track_format, track_src_name)
                else:
                    logger.error('%03d: Error Parsing Subtitle Track Info: "%s"', line_num, line)
                    
                states.append(STATES.InSubtitleTracks)
                states.append(STATES.ReadLine)
            else:
                states.append(STATES.SubtitleTracksEnd)
            
        elif state == STATES.SubtitleTracksEnd:
            logger.debug('%03d: Subtitle Tracks End', line_num)
            
        elif state == STATES.Done:
            logger.info('%03d: Done', line_num)
            break
        
        else:
            raise ParseException('Unknown State')
            
            


def main():
    movie_dir = 'W:\\_video_raw\\MASHS1D1'
    movie_dir = r'\\tpol\Raw Video\VOYAGER_S1D1'
    movie_dir = r'\\Archer\archer_s\_video_raw\COMBAT_SEASON_2_MISSION_1_DISC_1'
    default_root_dir = r'\\Archer\archer_s\_video_raw'
    default_root_dir = r'\\tpol\Raw Video\VOYAGER_S1D1'

    parser = argparse.ArgumentParser(description='Process a series of folders, reading the DVD information, display it to stdout')
    parser.add_argument('root_dir', default=default_root_dir, nargs='?')
    args = parser.parse_args()
    
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)5s - %(module)s:%(lineno)03d[%(funcName)s()] - %(message)s')
    fh = logging.FileHandler(filename='hbscan.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    logger.setLevel(logging.DEBUG)

    
    folders = all_folders(args.root_dir, single_level=True)
    for movie_dir in folders:
        logger.info('****** Scanning folder ****** %s', movie_dir)
        cmd = ['{}'.format(TRANSCODER), '-i', '{}'.format(movie_dir), '-t', '0']
        scan_start = time.time()
        scanning = subprocess.Popen(cmd, executable=TRANSCODER, shell=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (stdout, stderr) = scanning.communicate()
        logger.info('Scan took %.3f seconds', time.time() - scan_start)
        assert isinstance(stdout, str)
        #lines = stdout.splitlines()
        #parser = HandbrakeTitleParser()
        dvd = parseOutput(stdout)
        #print(stdout)
        
    

if __name__ == '__main__':
    main()
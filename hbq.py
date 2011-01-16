import xml.etree.ElementTree as et
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom.minidom import parseString
from oreillycookbook.files import all_folders
import os.path
import re
from pprint import pprint
from hbscan import ParseOutput, ScanDvd
from dvdinfo import DvdInfo

options = {'eps_len': ((48.8*60, 2*60), (30*60, 2*60)), 
            'expect_2x_len': True,
            'remove_dup_titles': True}

def GetInHMS(seconds):
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    if hours == 0:
        return "%02d:%02d" % (minutes, seconds)
    return "%02d:%02d:%02d" % (hours, minutes, seconds)


def RemoveDuplicateTitles(dvd):
    assert(isinstance(dvd, DvdInfo))
    for j, src_title in enumerate(dvd.titles):
        if src_title.enabled:
            for curr_title in dvd.titles[j+1:]:
                if curr_title.enabled and src_title.SimilarToTitle(curr_title):
                    curr_title.enabled = False
    
def main():
    src_root_folder = r'\\Archer\archer_s\_video_raw'
    dst_root_folder = 'W:\\video_handbrake\\'

    
    for folder in all_folders(src_root_folder, single_level=True):
        #print('{0}'.format(folder))
        basename = os.path.basename(folder)
        print('{0}'.format(basename))
        match = re.search('(.+?)_?[sS](\d+)_?[dD](\d+)', basename)
        if match:
            series = match.group(1)
            season = int(match.group(2))
            disc = int(match.group(3))
            print('    series = "{0}", season = {1}, disc = {2}'.format(series, season, disc))
            hb_out = ScanDvd(folder)
            dvd = ParseOutput(hb_out)
            if options['remove_dup_titles']:
                RemoveDuplicateTitles(dvd)
            active_durations = [x.duration for x in dvd.titles if x.enabled]
            active_duration_total = sum(active_durations)
            inactive_durations = [x.duration for x in dvd.titles if not x.enabled]
            inactive_duration_total = sum(inactive_durations)
            print('*** {0} active titles with total playtime of {1} ({2} inactive titles with playtime of {3}) ***'.format(
                len(active_durations), GetInHMS(active_duration_total),
                len(inactive_durations), GetInHMS(inactive_duration_total)))
            pprint(dvd)
        else:
            print('    *** Unable to parse folder name ***')
            
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
        SubElement(job, 'Query').text = ' -i "{src_folder}" -t {title_num} --angle 1 -o "{destination}" -f mkv --detelecine --decomb --denoise="weak" -w 720 --loose-anamorphic -e x264 -q {cq} -a {audio_tracks} -E {audio_encoders} --subtitle {subtitles} --subtitle-default={default_subtitle} -m -x ref=5:bframes=5:subq=9:mixed-refs=0:8x8dct=1:trellis=2:b-pyramid=1:me=umh:merange=32:analyse=all -v 2'.format(**cfg)
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
    
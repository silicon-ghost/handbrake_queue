import logging
import os.path
from pprint import pformat
import re
from hbscan import ParseHBOutput, ScanDvd
from dvdinfo import DvdInfo, Title
from itertools import combinations
# Personal library modules
from oreillycookbook.files import all_folders
from time_util import GetInHMS


logger = logging.getLogger('eps_detector')

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
        folder = os.path.abspath(folder)
        logger.info('Searching folder: %s', folder)
        if (os.path.exists(os.path.join(folder, 'VIDEO_TS')) or 
            os.path.exists(os.path.join(folder, 'VIDEO_TS.IFO'))):
            # Process this folder
            basename = os.path.basename(folder)
            match = re.search('(.+?)_?[sS](\d+)_?[dD](\d+)', basename)
            if match:
                series = match.group(1)
                series = series.replace('_', ' ')
                series = series.strip()
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

    def EnableAudioAndSubtitleTracks(self, langs=('eng', 'und')):
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
            is_episode = any((duration - variance) <= title.duration <= (duration + variance) 
                             for duration, variance in self.eps_durations)
            is_2x_episode = any((duration - variance) <= title.duration <= (duration + variance) 
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

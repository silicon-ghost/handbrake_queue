
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


def format_time(time):
    """
    Formats time as string: <hours>:<minutes>:<fseconds>.

    fseconds -- seconds as float

    Arguments:
    time -- time in fseconds
    """
    hours = int(time / 3600)
    r = time % 3600
    minutes = int(r / 60)
    seconds = r % 60
    return "{0:02d}:{1:02d}:{2:05.2f}".format(hours, minutes, seconds)

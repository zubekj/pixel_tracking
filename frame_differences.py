import numpy as np
import pandas as pd
import time

from ffpyplayer.player import MediaPlayer


def get_frame(player, t0=0):
    """
    Reads next frame from the stream, ensuring timestamp after t0.
    """
    while True:
        frame, val = player.get_frame()
        if val == 'eof':
            return None
        elif frame is None:
            time.sleep(0.01)
        else:
            img, t = frame
            if t < t0:
                continue
            return img, t


def update_range(crange, range_selected):
    """
    Finds next range which is selected for processing.
    """
    while True:
        crange += 1
        if crange == len(range_selected) or range_selected[crange]:
            break
    return crange


def calculate_frame_diffs_wcall(video_file, masks, cut_ranges,
                                pixel_diff_threshold=10, callback=None,
                                sec_callback=5):
    """
    Calculates frame differences for a video file.
    """
    distances = []
    column_names = (["Range", "Time", "Overall"]
                    + ["ROI{0}".format(j) for j, _ in enumerate(masks)])
    masks = [m.flatten() for m in masks]
    distances.append([-1, -1, 1] + [np.mean(m) for m in masks])

    player = MediaPlayer(video_file, thread_lib="SDL",
                         ff_opts={"out_fmt": "gray8", "an": True, "sn": True})

    frame = get_frame(player)
    if frame is None:
        return pd.DataFrame(distances, columns=column_names)
    img, t = frame

    metadata = player.get_metadata()
    duration, vid_size = metadata["duration"], metadata["src_vid_size"]
    vid_size = (vid_size[1], vid_size[0])

    img, t = frame
    oframe = np.asarray(img.to_memoryview(keep_align=True)[0], dtype=np.uint8)

    range_end = [r*duration for r in cut_ranges[0]]
    range_selected = [True] + cut_ranges[1]

    t0 = 0
    last_callback = 0
    crange = 0

    while True:
        # Get next frame
        frame = get_frame(player, t0)
        if frame is None:
            break
        img, t = frame

        # Update current range
        if t >= range_end[crange]:
            nrange = update_range(crange, range_selected)
            if nrange == len(range_selected):
                break
            if nrange > crange:
                if t < range_end[nrange-1]:
                    player.seek(range_end[nrange-1], relative=False)
                    oframe = None
                    t0 = range_end[nrange-1]
                    continue
                crange = nrange

        # Calculate frame difference
        cframe = np.asarray(img.to_memoryview(keep_align=True)[0])
        if oframe is not None:
            frame_diff = ((cframe - oframe > pixel_diff_threshold) &
                          (oframe - cframe > pixel_diff_threshold))
            distances.append([crange, t, np.mean(frame_diff)]
                             + [np.mean(frame_diff & mask)
                                for mask in masks])
            # Callback
            if callback is not None and (t - last_callback) >= sec_callback:
                last_callback = t
                callback(t/duration, frame_diff.reshape(vid_size))
        oframe = cframe
        t0 = t

    player.close_player()

    return pd.DataFrame(distances, columns=column_names)


if __name__ == "__main__":
    res = calculate_frame_diffs_wcall("LABIRYNT_03_78_044.avi", [],
                                      ([0, 0.5, 0.6, 0.66, 0.7, 0.8, 1], [False, True, True, False, True, False]),
                                      callback=lambda p, _: print(p))
    res.to_csv("out.csv", index=False)

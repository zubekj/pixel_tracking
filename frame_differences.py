import numpy as np
import pandas as pd
import skvideo.io
from skvideo.io import FFmpegReader
import collections

def calculate_frame_diffs(video_file, masks, pixel_diff_threshold=10):
    oframe = None
    videogen = FFmpegReader(video_file, outputdict={"-pix_fmt": "gray16le"})

    nframes = videogen.getShape()[0]
    distances = np.zeros(shape=(nframes, len(masks)), dtype="float64")

    try:
        oframe = next(videogen.nextFrame())[:, :, 0]
    except StopIteration:
        return distances

    for i, frame in enumerate(videogen.nextFrame()):
        cframe = frame[:, :, 0]
        frame_diff = np.abs(cframe - oframe)
        frame_diff[frame_diff <= pixel_diff_threshold] = 0
        for j, mask in enumerate(masks):
            distances[i, j] = np.sum(frame_diff[mask])
        oframe = cframe

    return distances


if __name__ == "__main__":

    videofile = "cut12.avi"

    frame = skvideo.io.vread(videofile, num_frames=1, outputdict={"-pix_fmt": "gray"})[0, :, :, 0]

    maskA = np.zeros(frame.shape, dtype=np.bool)
    maskB = np.zeros(frame.shape, dtype=np.bool)

    maskA[:, list(range(int(maskA.shape[1]/2)))] = 1
    maskB[:, list(range(int(maskA.shape[1]/2), maskA.shape[1]))] = 1

    ROI = collections.namedtuple("ROI", "name mask")

    import cProfile

    #cProfile.run('distances = calculate_frame_diffs(videofile, [ROI(name="A", mask=maskA), ROI(name="B", mask=maskB)])')
    distances = calculate_frame_diffs_p(videofile, [maskA, maskB])
    #distances = calculate_frame_diffs(videofile, np.array([maskA, maskB]))
    #distances.to_csv("raw_out.csv", index=False)

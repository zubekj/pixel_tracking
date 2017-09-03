import numpy as np
from skvideo.io import FFmpegReader


def calculate_frame_diffs(video_file, masks, pixel_diff_threshold=10):
    oframe = None
    videogen = FFmpegReader(video_file, outputdict={"-pix_fmt": "gray"})

    nframes = videogen.getShape()[0]
    distances = np.zeros(shape=(nframes, len(masks)+1), dtype="float64")

    try:
        oframe = next(videogen.nextFrame())[:, :, 0]
    except StopIteration:
        return distances

    for i in range(nframes-1):
        try:
            frame = next(videogen.nextFrame())
            cframe = frame[:, :, 0]
            frame_diff = ((cframe - oframe > pixel_diff_threshold) &
                          (oframe - cframe > pixel_diff_threshold))
            for j, mask in enumerate(masks):
                distances[i, j] = np.mean(frame_diff & mask)
            distances[i, len(masks)] = np.mean(frame_diff)
            oframe = cframe
        except RuntimeError:
            print("Error reading frame {0}".format(i))

    return distances


def calculate_frame_diffs_wcall(video_file, masks, pixel_diff_threshold=10,
        callback=None, nframes_callback=100):
    oframe = None
    videogen = FFmpegReader(video_file, outputdict={"-pix_fmt": "gray"})

    nframes = videogen.getShape()[0]
    distances = np.zeros(shape=(nframes, len(masks)+1), dtype="float64")

    try:
        oframe = next(videogen.nextFrame())[:, :, 0]
    except StopIteration:
        return distances

    for i in range(nframes-1):
        try:
            frame = next(videogen.nextFrame())
            cframe = frame[:, :, 0]
            frame_diff = ((cframe - oframe > pixel_diff_threshold) &
                          (oframe - cframe > pixel_diff_threshold))
            for j, mask in enumerate(masks):
                distances[i, j] = np.mean(frame_diff & mask)
            distances[i, len(masks)] = np.mean(frame_diff)
            oframe = cframe
            if callback is not None and (i % nframes_callback) == 0:
                callback(float(i)/nframes, frame_diff)
        except RuntimeError:
            print("Error reading frame {0}".format(i))

    return distances


if __name__ == "__main__":

    videofile = "cut12.avi"
    
    from skvideo.io import vread
    frame = vread(videofile, num_frames=1, outputdict={"-pix_fmt": "gray"})[0, :, :, 0]

    maskA = np.zeros(frame.shape, dtype=np.uint8)
    maskB = np.zeros(frame.shape, dtype=np.uint8)

    maskA[:, list(range(int(maskA.shape[1]/2)))] = 1
    maskB[:, list(range(int(maskA.shape[1]/2), maskA.shape[1]))] = 1

    distances = calculate_frame_diffs(videofile, [maskA, maskB])
    print(distances)

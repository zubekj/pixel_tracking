import numpy as np
import pandas as pd
import cv2
import scipy.signal

ds = 6  # downsample
cuttoff_freq = 0.75  # for butterworth filtering


def butterworth_filter(data):
    # source http://azitech.wordpress.com/2011/03/15/designing-a-butterworth-low-pass-filter-with-scipy/
    norm_pass = cuttoff_freq/(ds/2)
    norm_stop = 1.5*norm_pass
    (N, Wn) = scipy.signal.buttord(wp=norm_pass, ws=norm_stop, gpass=2,
                                   gstop=30, analog=0)
    (b, a) = scipy.signal.butter(N, Wn, btype='low', analog=0, output='ba')
    data = [scipy.signal.lfilter(b, a, data[d].values) for d in data]
    data = pd.DataFrame(data).T
    return data


def calculate_frame_diffs(cap, masks, pixel_diff_threshold=20,
                          video_output=None):
    ret, frame = cap.read()
    oframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    video_writer = cv2.VideoWriter()
    if video_output is not None:
        video_writer.open(video_output,
                          cv2.VideoWriter_fourcc(*'XVID'),
                          20.0, oframe.T.shape, False)

    distances = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        frame_diff = np.abs(cframe.astype(np.int8) -
                            oframe.astype(np.int8))
        frame_diff[frame_diff <= pixel_diff_threshold] = 0

        if video_output is not None:
            video_writer.write(frame_diff.astype(np.uint8))

        distances.append([(frame_diff & m).mean() for m in masks])
        oframe = cframe

    if video_output is not None:
        video_writer.release()

    return pd.DataFrame(distances)


if __name__ == "__main__":

    cap = cv2.VideoCapture('cut.avi')
    #cap = cv2.VideoCapture('flame.avi')

    if not cap.isOpened():
        print("Cannot open video file")
        exit(1)

    ret, frame = cap.read()

    maskA = np.zeros(frame.shape[:2], dtype=np.int8)
    maskB = np.zeros(frame.shape[:2], dtype=np.int8)

    maskA[:, list(range(int(maskA.shape[1]/2)))] = 1
    maskB[:, list(range(int(maskA.shape[1]/2), maskA.shape[1]))] = 1

    distances = calculate_frame_diffs(cap, [maskA, maskB],
                                      video_output="fd_out.avi")
    distances.to_csv("raw_out.csv", index=False)
    cap.release()

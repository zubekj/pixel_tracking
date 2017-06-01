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
    data = [scipy.signal.lfilter(b, a, d) for d in data]
    data = pd.DataFrame(data).T
    return data


def calculate_frame_diffs(cap, masks):
    ret, frame = cap.read()
    oframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    distances = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        distances.append([(np.abs(cframe.astype(np.int8) -
                                  oframe.astype(np.int8)) & m).mean()
                          for m in masks])
        oframe = cframe

    return pd.DataFrame(distances)


drawing = False  # true if mouse is pressed
ix, iy = -1, -1
img = None


# mouse callback function
def mouse_event(event, x, y, flags, param):
    global ix, iy, drawing, mode

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            cv2.circle(img, (x, y), 5, (0, 0, 255), -1)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.circle(img, (x, y), 5, (0, 0, 255), -1)


def draw_mask(cap):
    ret, frame = cap.read()
    img = frame

    cv2.namedWindow('image')
    cv2.setMouseCallback('image', mouse_event)

    while(True):
        cv2.imshow('image', img)
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break

    cv2.destroyAllWindows()


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

    distances = calculate_frame_diffs(cap, [maskA, maskB])
    distances.to_csv("raw_out.csv", index=False)
    distances = butterworth_filter(distances)
    distances.to_csv("out.csv", index=False)
    cap.release()

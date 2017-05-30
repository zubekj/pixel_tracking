import numpy as np
import pandas as pd
import cv2


def dist(cframe, oframe):
    return ((cframe.astype(np.int8) - oframe.astype(np.int8)) != 0).sum() / 3


def calculate_pixel_change(cap, maskA, maskB):

    ret, frame = cap.read()
    #oframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    oframe = frame

    distances = []

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        #cframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cframe = frame
        distances.append(dist(cframe, oframe))
        oframe = cframe

    return pd.Series(distances)


drawing = False # true if mouse is pressed
ix,iy = -1,-1
img = None

# mouse callback function
def draw_mask(event,x,y,flags,param):
    global ix,iy,drawing,mode

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix,iy = x,y

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing == True:
            cv2.circle(img,(x,y),5,(0,0,255),-1)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        cv2.circle(img,(x,y),5,(0,0,255),-1)


if __name__ == "__main__":

    cap = cv2.VideoCapture('flame.avi')

    if not cap.isOpened():
        print("Cannot open video file")
        exit(1)

    ret, frame = cap.read()
    #img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img = frame

    cv2.namedWindow('image')
    cv2.setMouseCallback('image', draw_mask)

    while(True):
        cv2.imshow('image', img)
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break

    cv2.destroyAllWindows()

    distances = calculate_pixel_change(cap, None, None)
    distances.to_csv("out.txt", index=False)
    cap.release()

# README #

Pixel Tracking app for quantifying movement on video recordings. Written in Python with Kivy GUI.

## Requirements

- numpy
- pandas
- scipy
- kivy
- ffpyplayer 

All required libraries may be installed with pip.

    > pip install numpy pandas scipy kivy ffpyplayer

Kivy dependencies (sdl2, glew, gstreamer) must be installed separately. For Linux and macOS
it is best to use system-wide package manager. For Windows binary packages are provided:

    [Windows only] > pip install docutils pygments pypiwin32 kivy.deps.sdl2 kivy.deps.glew kivy.deps.gstreamer
    
Detailed instructions regarding Kivy installation may be found here:

https://kivy.org/docs/installation/installation.html

## Running

To run the application write:

    > python pixel_tracking.py

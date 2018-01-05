from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.video import Video
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Ellipse, Line, Rectangle, Fbo
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.event import EventDispatcher
from kivy.clock import mainthread, Clock

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

from filebrowser import FileBrowser

import threading
import numpy as np
import pandas as pd

import os

import cutpoint_line

from frame_differences import calculate_frame_diffs_wcall

roi_colors = [[ 0.10588235,  0.61960784,  0.46666667, 1],
              [ 0.85098039,  0.37254902,  0.00784314, 1],
              [ 0.45882353,  0.43921569,  0.70196078, 1],
              [ 0.90588235,  0.16078431,  0.54117647, 1],
              [ 0.4       ,  0.65098039,  0.11764706, 1],
              [ 0.90196078,  0.67058824,  0.00784314, 1]]

class LoadDialog(Popup):
    load = ObjectProperty(None)


class SaveDialog(Popup):
    save = ObjectProperty(None)


class ConfirmDialog(Popup):
    yes = ObjectProperty(None)
    text = StringProperty("")


class VideoProgress(Popup):

    def __init__(self, **kwargs):
        super(VideoProgress, self).__init__(**kwargs)
        self.ids.image_id.color = (1, 1, 1, 0)

    @mainthread
    def update_progress(self, progress_fraction, image_matrix):
        self.ids.progressbar_id.value = progress_fraction
        m = np.zeros(shape=image_matrix.shape, dtype=np.uint8)
        m[image_matrix == 1] = 255
        texture = Texture.create(size=(m.shape[1], m.shape[0]))
        texture.blit_buffer(m.tostring(), colorfmt="luminance",
                            bufferfmt="ubyte")
        self.ids.image_id.texture = texture
        self.ids.image_id.texture.flip_vertical()
        self.ids.image_id.color = (1, 1, 1, 1)
        self.ids.image_id.canvas.ask_update()


class ROIList(EventDispatcher):

    def __init__(self, **kwargs):
        self.register_event_type('on_roi_added')
        self.register_event_type('on_roi_selected')
        self.register_event_type('on_roi_removed')
        super(ROIList, self).__init__(**kwargs)

        self.values = []
        self.selected = None

    def add(self):
        new_value = self.values[-1] + 1 if len(self.values) > 0 else 0
        self.values.append(new_value)
        self.dispatch('on_roi_added', new_value)

    def select(self, index):
        if index is None:
            return
        self.selected = index
        self.dispatch('on_roi_selected', index)

    def remove(self, index):
        if index is None:
            return
        del self.values[index]
        self.selected = None
        self.dispatch('on_roi_removed', index)

    def clear(self):
        while len(self.values) > 0:
            self.remove(0)

    def on_roi_added(self, a):
        pass

    def on_roi_selected(self, a):
        pass

    def on_roi_removed(self, a):
        pass


class VideoWidget(Video):

    cutpoint_panel = ObjectProperty(None)
    video_loaded = BooleanProperty(False)

    stop = threading.Event()

    def __init__(self, **kwargs):
        super(VideoWidget, self).__init__(**kwargs)

        self.roi_list = App.get_running_app().roi_list
        self.roi_list.bind(on_roi_added=self.add_roi_fbo)
        self.roi_list.bind(on_roi_selected=self.select_roi_fbo)
        self.roi_list.bind(on_roi_removed=self.remove_roi_fbo)

        self.fbo_list = []

    def add_roi_fbo(self, obj, new_value):
        with self.canvas:
            fbo = Fbo(size=self.texture.size)
            color = Color(*roi_colors[new_value % len(roi_colors)])
            rect = Rectangle(size=self.vid_size, pos=self.vid_pos,
                             texture=fbo.texture)
            self.bind(vid_size=lambda s, *args: setattr(rect, 'size', self.vid_size),
                      vid_pos=lambda s, *args: setattr(rect, 'pos', self.vid_pos))
            self.fbo_list.append((fbo, color, rect))

    def select_roi_fbo(self, obj, index):
        for fbo_t in self.fbo_list:
            fbo_t[1].a = 0.5
        self.fbo_list[index][1].a = 0.75

    def remove_roi_fbo(self, obj, index):
        self.canvas.remove(self.fbo_list[index][0])
        self.canvas.remove(self.fbo_list[index][1])
        self.canvas.remove(self.fbo_list[index][2])
        del self.fbo_list[index]

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos)\
           or self.roi_list.selected is None:
            return

        color = (1, 1, 1)
        fbo = self.fbo_list[self.roi_list.selected][0]
        x = (touch.x - self.vid_pos[0])/self.vid_size[0]*fbo.size[0]
        y = (touch.y - self.vid_pos[1])/self.vid_size[1]*fbo.size[1]

        d = 40.0/self.vid_size[0]*fbo.size[0]

        with fbo:
            Color(*color, mode='rgb')
            Ellipse(pos=(x - d / 2, y - d / 2), size=(d, d))
            touch.ud['line'] = Line(points=(x, y), width=d/2, joint='round')

    def on_touch_move(self, touch):
        if self.roi_list.selected is None or "line" not in touch.ud:
            return

        fbo = self.fbo_list[self.roi_list.selected][0]
        x = (touch.x - self.vid_pos[0])/self.vid_size[0]*fbo.size[0]
        y = (touch.y - self.vid_pos[1])/self.vid_size[1]*fbo.size[1]
        touch.ud['line'].points += [x, y]

    def on_texture(self, obj, texture):
        if self.state == "play":
            self.state = "stop"
            self.resize_video()
            self.video_loaded = True

    def on_size(self, obj, size):
        self.resize_video()

    def resize_video(self):
        ratio = self.image_ratio
        if self.height*ratio <= self.width:
            self.vid_size = (self.height*ratio, self.height)
        else:
            self.vid_size = (self.width, self.width/ratio)
        self.vid_pos = (
                (self.width - self.vid_size[0])/2 - self.width + self.right,
                (self.height - self.vid_size[1])/2 - self.height + self.top)

    def verify_load_location(self, path, filename):
        filename = os.path.join(path, filename)
        if os.path.isdir(filename):
            return
        if not os.path.isfile(filename):
            return
        self.load_video(filename)
        self._popup.dismiss()

    def load_video(self, filename):
        self.source = ""
        self.roi_list.clear()
        self.video_loaded = False
        self.cutpoint_panel.reset()
        self.volume = 0
        self.state = "play"
        self.source = filename

    def seek_video(self, pos):
        if self.texture is not None:
            self.seek(pos)

    def show_load(self, load_action):
        self._popup = LoadDialog(load=load_action)
        self._popup.open()

    def show_save(self, save_action):
        self._popup = SaveDialog(save=save_action)
        self._popup.open()

    def verify_save_location(self, path, filename):
        self._confirm = None

        def finalize_save():
            if self._confirm is not None:
                self._confirm.dismiss()
            self._popup.dismiss()
            self.save_fd_rois(filename)

        filename = os.path.join(path, filename)
        if os.path.isdir(filename):
            return
        if os.path.isfile(filename):
            text = "File exists. Do you want to overwrite?"
            self._confirm = ConfirmDialog(text=text, yes=finalize_save)
            self._confirm.open()
            return

        finalize_save()

    def save_fd_rois(self, filename):
        width, height = self.texture.size
        masks = [np.frombuffer(fbo[0].pixels, dtype="ubyte").reshape(height, width, 4)[:, :, 0] > 0
                 for fbo in self.fbo_list]
        roi_names = [roi for roi in self.roi_list.values] + ["Overall"]

        self._progress = VideoProgress()
        self._progress.open()

        threading.Thread(target=self.calc_save_fd, args=(self.source, masks, roi_names, filename, self._progress.update_progress)).start()

    def calc_save_fd(self, source, masks, roi_names, filename, callback):
        diffs = pd.DataFrame(calculate_frame_diffs_wcall(source, masks,
            callback=callback))
        self.close_progressbar()
        diffs.columns = roi_names
        diffs.to_csv(filename, index=False)

    @mainthread
    def close_progressbar(self):
        self._progress.dismiss()


class ROISelector(BoxLayout):

    def __init__(self, **kwargs):
        super(ROISelector, self).__init__(**kwargs)

        self.dropdown = DropDown()
        self.dropdown.bind(on_select=lambda obj, x:
                setattr(self.ids.mainbutton_id, 'text', "ROI {0}".format(x)))

        self.roi_list = App.get_running_app().roi_list
        self.roi_list.bind(on_roi_added=self.add_roi_button)
        self.roi_list.bind(on_roi_selected=lambda obj, index:
                self.dropdown.select(obj.values[index]))
        self.roi_list.bind(on_roi_removed=self.remove_roi_button)

        add_roi_btn = Button(text="Add new ROI…", size_hint_y=None, height=44)
        add_roi_btn.bind(on_release=lambda obj: self.roi_list.add() or
                self.roi_list.select(len(self.roi_list.values)-1))
        self.dropdown.add_widget(add_roi_btn)

        self.roi_buttons = []

    def add_roi_button(self, obj, new_value):
        color = roi_colors[new_value % len(roi_colors)]
        btn = Button(text="ROI {0}".format(new_value), size_hint_y=None,
                     height=44, background_color=color)
        btn.bind(on_release=lambda instance: self.roi_list.select(
            self.roi_buttons.index(btn)))
        self.dropdown.add_widget(btn)
        self.roi_buttons.append(btn)

    def remove_roi_button(self, obj, index):
        self.dropdown.remove_widget(self.roi_buttons[index])
        del self.roi_buttons[index]
        self.ids.mainbutton_id.text = "Select ROI…"


class RootWindow(BoxLayout):
    pass


class PixelTrackingApp(App):

    def __init__(self, **kwargs):
        super(PixelTrackingApp, self).__init__(**kwargs)
        self.roi_list = ROIList()

    def on_stop(self):
        video = self.root.ids.video_id
        video.stop.set()
        os._exit(0)


if __name__ == '__main__':
    PixelTrackingApp().run()

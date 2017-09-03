from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.video import Video
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.popup import Popup
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Ellipse, Line, Fbo
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.event import EventDispatcher
from kivy.clock import mainthread

import threading
import numpy as np
import pandas as pd

import os

from frame_differences import calculate_frame_diffs_wcall

class LoadDialog(FloatLayout):
    load = ObjectProperty(None)
    cancel = ObjectProperty(None)


class SaveDialog(FloatLayout):
    save = ObjectProperty(None)
    text_input = ObjectProperty(None)
    cancel = ObjectProperty(None)


class VideoProgress(FloatLayout):

    def __init__(self, **kwargs):
        super(VideoProgress, self).__init__(**kwargs)
        self.job_finished = False
        self.ids.image_id.color = (1, 1, 1, 0)

    def on_parent_dismiss(self, instance):
        if not self.job_finished:
            return True

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

    disabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        self.register_event_type('on_roi_added')
        self.register_event_type('on_roi_selected')
        self.register_event_type('on_roi_removed')
        super(ROIList, self).__init__(**kwargs)

        self.values = []
        self.selected = None

    def add(self):
        if self.disabled:
            return
        roi_name = "ROI {0}".format(len(self.values))
        self.values.append(roi_name)
        new_index = len(self.values)-1
        self.dispatch('on_roi_added', new_index)

    def select(self, index):
        if self.disabled or index is None:
            return
        self.selected = index
        self.dispatch('on_roi_selected', index)

    def remove(self, index):
        if self.disabled or index is None:
            return
        del self.values[index]
        self.selected = None
        self.dispatch('on_roi_removed', index)

    def clear(self):
        if self.disabled:
            return
        while len(self.values) > 0:
            self.remove(0)

    def on_roi_added(self, a):
        pass

    def on_roi_selected(self, a):
        pass

    def on_roi_removed(self, a):
        pass


class VideoWidget(Video):

    stop = threading.Event()

    def __init__(self, **kwargs):
        super(VideoWidget, self).__init__(**kwargs)

        self.roi_list = App.get_running_app().roi_list
        self.roi_list.bind(on_roi_added=self.add_roi_fbo)
        self.roi_list.bind(on_roi_selected=self.select_roi_fbo)
        self.roi_list.bind(on_roi_removed=self.remove_roi_fbo)

        self.fbo_list = []

    def add_roi_fbo(self, obj, index):
        with self.canvas:
            self.fbo_list.append(Fbo(size=self.texture.size))

    def select_roi_fbo(self, obj, index):
        self.fbo_texture = self.fbo_list[index].texture

    def remove_roi_fbo(self, obj, index):
        self.canvas.remove(self.fbo_list[index])
        del self.fbo_list[index]
        self.fbo_texture = Texture.create()

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or self.roi_list.selected is None:
            return

        color = (1, 0.6, 0.6)
        fbo = self.fbo_list[self.roi_list.selected]
        x = (touch.x - self.vid_pos[0])/self.vid_size[0]*fbo.size[0]
        y = (touch.y - self.vid_pos[1])/self.vid_size[1]*fbo.size[1]

        d = 40.0/self.vid_size[0]*fbo.size[0]

        with fbo:
            Color(*color, mode='rgb')
            Ellipse(pos=(x-d/2, y-d/2), size=(d, d))
            touch.ud['line'] = Line(points=(x, y), width=d/2, joint='round')

    def on_touch_move(self, touch):
        if self.roi_list.selected is None or not "line" in touch.ud:
            return

        fbo = self.fbo_list[self.roi_list.selected]
        x = (touch.x - self.vid_pos[0])/self.vid_size[0]*fbo.size[0]
        y = (touch.y - self.vid_pos[1])/self.vid_size[1]*fbo.size[1]
        touch.ud['line'].points += [x, y]

    def on_texture(self, obj, texture):
        if self.state == "play":
            self.state = "stop"
            self.resize_video()
            self.roi_list.disabled = False
            self.parent.ids.slider_id.disabled = False
            self.fbo_texture = Texture.create()

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

    def load_video(self, path, filename):
        self.source = ""
        self.roi_list.clear()
        self.roi_list.disabled = True
        self.parent.ids.slider_id.disabled = True
        self.parent.ids.slider_id.value = 0
        self.volume = 0
        self.state = "play"
        self.source = os.path.join(path, filename[0])
        self.dismiss_popup()

    def load_video_init(self):
        self.show_load(self.load_video)

    def seek_video(self, pos):
        if self.texture is not None:
            self.seek(pos)

    def dismiss_popup(self):
        self._popup.dismiss()

    def show_load(self, load_action):
        content = LoadDialog(load=load_action, cancel=self.dismiss_popup)
        self._popup = Popup(title="Load file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def show_save(self, save_action):
        content = SaveDialog(save=save_action, cancel=self.dismiss_popup)
        self._popup = Popup(title="Save file", content=content,
                            size_hint=(0.9, 0.9))
        self._popup.open()

    def save_fd_rois(self, path, filename):
        self.dismiss_popup()

        width, height = self.texture.size
        masks = [np.frombuffer(fbo.pixels, dtype="ubyte").reshape(height, width, 4)[:, :, 0] > 0
                 for fbo in self.fbo_list] 
        roi_names = [roi for roi in self.roi_list.values] + ["Overall"]

        video_progress = VideoProgress()
        self._progress = Popup(title="Processing video…", content=video_progress, size_hint=(0.9, 0.9))
        self._progress.bind(on_dismiss=video_progress.on_parent_dismiss)
        self._progress.open()

        threading.Thread(target=self.calc_save_fd, args=(self.source, masks, roi_names, path, filename, video_progress.update_progress)).start()

    def calc_save_fd(self, source, masks, roi_names, path, filename, callback):
        diffs = pd.DataFrame(calculate_frame_diffs_wcall(source, masks,
            callback=callback))
        self.close_progressbar()
        diffs.columns = roi_names
        diffs.to_csv(os.path.join(path, filename), index=False)

    @mainthread
    def close_progressbar(self):
        self._progress.content.job_finished = True
        self._progress.dismiss()


class ROISelector(BoxLayout):

    def __init__(self, **kwargs):
        super(ROISelector, self).__init__(**kwargs)

        self.disabled = True

        self.dropdown = DropDown()
        self.dropdown.bind(on_select=lambda obj, x:
                setattr(self.ids.mainbutton_id, 'text', x))

        self.roi_list = App.get_running_app().roi_list
        self.roi_list.bind(on_roi_added=self.add_roi_button)
        self.roi_list.bind(on_roi_selected=lambda obj, index:
                self.dropdown.select(obj.values[index]))
        self.roi_list.bind(on_roi_removed=self.remove_roi_button)

        def set_disabled(i, b):
            self.disabled = b
        self.roi_list.bind(disabled=set_disabled) 
        
        add_roi_btn = Button(text="Add new ROI…", size_hint_y=None, height=44)
        add_roi_btn.bind(on_release=lambda obj: self.roi_list.add() or
                self.roi_list.select(len(self.roi_list.values)-1))
        self.dropdown.add_widget(add_roi_btn)

        self.roi_buttons = []

    def add_roi_button(self, obj, new_index):
        btn = Button(text=obj.values[new_index], size_hint_y=None, height=44)
        btn.bind(on_release=lambda instance: self.roi_list.select(
            self.roi_buttons.index(btn)))
        self.dropdown.add_widget(btn)
        self.roi_buttons.append(btn)

    def remove_roi_button(self, obj, index):
        self.dropdown.remove_widget(self.roi_buttons[index])
        del self.roi_buttons[index]
        self.ids.mainbutton_id.text = "Select ROI…"


class PixelTrackingApp(App):

    def __init__(self, **kwargs):
        super(PixelTrackingApp, self).__init__(**kwargs)
        self.roi_list = ROIList()

    def on_stop(self):
        video = self.root.ids.video_id
        video.stop.set()
        os._exit(0)

    def export_rois(self):
        video = self.root.ids.video_id
        video.show_save(video.save_fd_rois)


if __name__ == '__main__':
    PixelTrackingApp().run()

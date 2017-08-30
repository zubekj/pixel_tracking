from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.video import Video
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.dropdown import DropDown
from kivy.graphics import Color, Ellipse, Line, Fbo, Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, ListProperty, NumericProperty
from kivy.event import EventDispatcher

import numpy as np


class ROIList(EventDispatcher):

    def __init__(self, **kwargs):
        self.register_event_type('on_roi_added')
        self.register_event_type('on_roi_selected')
        self.register_event_type('on_roi_removed')
        super(ROIList, self).__init__(**kwargs)

        self.values = []
        self.selected = None
        self.enabled = False

    def add(self):
        if not self.enabled:
            return
        roi_name = "ROI {0}".format(len(self.values))
        self.values.append(roi_name)
        new_index = len(self.values)-1
        self.dispatch('on_roi_added', new_index)
    
    def select(self, index):
        if not self.enabled or index is None:
            return
        self.selected = index
        self.dispatch('on_roi_selected', index)

    def remove(self, index):
        if not self.enabled or index is None:
            return
        del self.values[index]
        self.selected = None
        self.dispatch('on_roi_removed', index)

    def clear(self):
        if not self.enabled:
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
        
        with fbo:
            Color(*color, mode='rgb')
            d = 20.
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
            #self.fbo.clear()
            #self.fbo.size = texture.size
            self.state = "stop"
            self.resize_video()
            self.roi_list.enabled = True
            self.fbo_texture = Texture.create()

    def on_size(self, obj, size):
        self.resize_video()

    def resize_video(self):
        ratio = self.image_ratio
        if self.height/ratio <= self.width:
            self.vid_size = (self.height/ratio, self.height)
        else:
            self.vid_size = (self.width, self.width*ratio)
        self.vid_pos = (
                (self.width - self.vid_size[0])/2 - self.width + self.right,
                (self.height - self.vid_size[1])/2 - self.height + self.top)

    def load_video(self):
        self.source = ""
        self.roi_list.clear()
        self.roi_list.enabled = False
        self.parent.ids.slider_id.value = 0
        self.state = "play"
        self.source = "flame.avi"

    def seek_video(self, pos):
        if self.texture is not None:
            self.seek(pos)


class ROISelector(BoxLayout):

    def __init__(self, **kwargs):
        super(ROISelector, self).__init__(**kwargs)

        self.dropdown = DropDown()
        self.dropdown.bind(on_select=lambda obj, x:
                setattr(self.ids.mainbutton_id, 'text', x))
        
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

    def export_rois(self):
        video = self.root.ids.video_id
        #for i in range(len(video.fbo_list)):


if __name__ == '__main__':
    PixelTrackingApp().run()

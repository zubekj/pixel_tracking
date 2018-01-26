from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Rectangle, Color, Line
from kivy.properties import ListProperty, NumericProperty, StringProperty, ObjectProperty

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,disable_multitouch')

class CutpointLine(Widget):
    """
    Class for creating a CutpointLine widget.
    """
    padding = NumericProperty(25)
    line_width = NumericProperty(2)
    cutpoints = ListProperty([0, 1])
    selected_ranges = ListProperty([True])
    state = StringProperty("seek")
    value = NumericProperty(0)

    def __init__(self, **kwargs):
        super(CutpointLine, self).__init__(**kwargs)

        self.display_ranges = []
        self.display_ticks = []

        self.selected_color = [0.4, 0.6, 0.8, 0.5]
        self.unselected_color = [0, 0, 0, 0]
        self.tick_color = [0.6, 0.6, 0.6]

        with self.canvas:
            # By default full video is selected
            c = Color(*self.selected_color)
            l = Line(points=[], width=10, cap='none')
            self.display_ranges.append((c, l))

        with self.canvas.after:
            # Tick at the beginning
            c = Color(*self.tick_color)
            l = Line(points=[], width=2)
            self.display_ticks.append((c, l))

            # Tick at the end
            c = Color(*self.tick_color)
            l = Line(points=[], width=2)
            self.display_ticks.append((c, l))

        self.bind(size=self.repaint_ranges, pos=self.repaint_ranges)

    def on_value(self, *args):
        pass

    def repaint_ranges(self, *args):
        x_1 = self.frac_to_pos(self.cutpoints[0])
        for i in range(len(self.cutpoints)-1):
            x = x_1
            x_1 = self.frac_to_pos(self.cutpoints[i+1])
            c = self.selected_color if self.selected_ranges[i] else self.unselected_color
            self.display_ranges[i][0].rgba = c
            self.display_ranges[i][1].points = [x, self.center_y, x_1, self.center_y]
            self.display_ticks[i][1].points = [x, self.center_y-10, x, self.center_y+10]
        self.display_ticks[-1][1].points = [x_1, self.center_y-10, x_1, self.center_y+10]
        v = self.value
        self.value = 0
        self.value = v


    def pos_to_frac(self, x):
        """
        Converts from screen position to relative line position.
        Values outside range are trimmed.
        """
        x -= self.x + self.padding
        rwidth = self.width - 2*self.padding
        return float(min(max(0, x), rwidth)) / rwidth

    def frac_to_pos(self, x):
        """
        Converts from relative line position to screen position.
        """
        rwidth = self.width - 2*self.padding
        return self.x + self.padding + x*rwidth

    def add_cutpoint(self, i, frac):
        """
        Adds cutpoint at the selected (relative) position.
        """
        self.cutpoints.insert(i, frac)
        self.selected_ranges.insert(i, True)

        with self.canvas:
            self.display_ranges.append((Color(), Line(width=10, cap='none')))

        c = Color(*self.tick_color)
        l = Line(points=[], width=2)
        self.canvas.after.insert(0, l)
        self.canvas.after.insert(0, c)
        self.display_ticks.append((c, l))
        self.repaint_ranges()

    def remove_cutpoint(self, i):
        """
        Removes cutpoint to the right of the selected position.
        """
        if i == 0 or i == len(self.cutpoints)-1:
            return

        del self.cutpoints[i]
        del self.selected_ranges[i]
        self.canvas.after.remove(self.display_ticks[0][0])
        self.canvas.after.remove(self.display_ticks[0][1])
        del self.display_ticks[0]
        self.canvas.remove(self.display_ranges[0][0])
        self.canvas.remove(self.display_ranges[0][1])
        del self.display_ranges[0]
        self.repaint_ranges()

    def on_touch_down(self, touch):
        if self.disabled or not self.collide_point(*touch.pos):
            return

        # i -- next index, nn_i -- nearest index
        frac = self.pos_to_frac(touch.x)
        i = 0
        while self.cutpoints[i] < frac:
            i += 1
        nn_i = i
        if i > 0 and (self.cutpoints[i] - frac) > (frac - self.cutpoints[i-1]):
            nn_i = i - 1

        if self.state == "add":
            self.add_cutpoint(i, frac)
        elif self.state == "delete":
            self.remove_cutpoint(nn_i)
        elif self.state == "move":
            # Select nearest cutpoint to grab
            if nn_i == 0 or nn_i == len(self.cutpoints)-1:
                return
            self.grab_cutpoint = nn_i
            self.cutpoints[nn_i] = frac
            touch.grab(self)
            self.repaint_ranges()
        elif self.state == "seek":
            self.value = self.pos_to_frac(touch.x)
            touch.grab(self)
        elif self.state == "toggle":
            if i == 0:
                return
            self.selected_ranges[i-1] = not self.selected_ranges[i-1]
            self.repaint_ranges()
        return True

    def on_touch_move(self, touch):
        if touch.grab_current == self:
            if self.state == "move":
                frac = self.pos_to_frac(touch.x)
                frac = min(max(self.cutpoints[self.grab_cutpoint-1], frac),
                           self.cutpoints[self.grab_cutpoint+1])
                self.cutpoints[self.grab_cutpoint] = frac
                self.repaint_ranges()
            elif self.state == "seek":
                self.value = self.pos_to_frac(touch.x)
            return True

    def on_touch_up(self, touch):
        if touch.grab_current == self:
            if self.state == "move":
                frac = self.pos_to_frac(touch.x)
                frac = min(max(self.cutpoints[self.grab_cutpoint-1], frac),
                           self.cutpoints[self.grab_cutpoint+1])
                self.cutpoints[self.grab_cutpoint] = frac
                self.repaint_ranges()
                touch.ungrab(self)
                self.grab_cutpoint = None
            elif self.state == "seek":
                self.value = self.pos_to_frac(touch.x)
                touch.ungrab(self)
            return True

    def reset(self):
        while len(self.cutpoints) > 2:
            self.remove_cutpoint(1)
        self.value = 0
        self.selected_ranges[0] = True


class CutpointPanel(BoxLayout):
    cutpoint_line = ObjectProperty(None)
    value = NumericProperty(0)
    length = NumericProperty(0)
    cutpoints = ListProperty([0, 1])
    selected_ranges = ListProperty([True])

    def reset(self):
        self.cutpoint_line.reset()


if __name__ == '__main__':
    from kivy.app import App

    class CutpointLineApp(App):
        def build(self):
            r = CutpointPanel()
            return r

    CutpointLineApp().run()

"""Gráfico leve com leituras reais: não desenha curva na ausência de valores."""
from collections import deque
from gi.repository import Gtk

class History(Gtk.DrawingArea):
    def __init__(self, ceiling=100.0, color=(.55,.4,1.0)):
        super().__init__()
        self.set_size_request(160,32)
        self.readings=deque(maxlen=45)
        self.ceiling=ceiling
        self.color=color
        self.connect('draw',self.draw_graph)

    def push(self,value):
        self.readings.append(float(value) if isinstance(value,(float,int)) and value>=0 else None)
        self.queue_draw()

    def draw_graph(self,_,cr):
        w,h=self.get_allocated_width(),self.get_allocated_height()
        cr.set_source_rgba(.18,.22,.36,.7);cr.set_line_width(1)
        cr.move_to(0,h-2);cr.line_to(w,h-2);cr.stroke()
        if len(self.readings)<2:return False
        cr.set_line_width(2.0)
        cr.set_source_rgb(*self.color)
        drawing=False
        for i,value in enumerate(self.readings):
            if value is None:drawing=False;continue
            x=float(i)/max(1,len(self.readings)-1)*w
            y=(h-3)-min(1.,value/max(1.,self.ceiling))*(h-7)
            if drawing:cr.line_to(x,y)
            else:cr.move_to(x,y);drawing=True
        cr.stroke()
        return False

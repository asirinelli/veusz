#    Copyright (C) 2011 Jeremy S. Sanders
#    Email: Jeremy Sanders <jeremy@jeremysanders.net>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
##############################################################################

"""Helper for doing the plotting of the document.
"""

import veusz.qtall as qt4
import veusz.setting as setting
import veusz.utils as utils

try:
    from veusz.helpers.qtloops import RecordPaintDevice
except ImportError:
    # fallback to this if we don't get the native recorded
    def RecordPaintDevice(width, height, dpix, dpiy):
        return qt4.QPicture()

class DrawState(object):
    """Each widget plotted has a recorded state in this object."""

    def __init__(self, widget, bounds, clip, helper):
        """Initialise state for widget.
        bounds: tuple of (x1, y1, x2, y2)
        clip: if clipping should be done, another tuple."""

        self.widget = widget
        self.record = RecordPaintDevice(
            helper.pagesize[0], helper.pagesize[1],
            helper.dpi[0], helper.dpi[1])
        self.bounds = bounds
        self.clip = clip

        # controlgraphs belonging to widget
        self.cgis = []

        # list of child widgets states
        self.children = []

class PaintHelper(object):
    """Helper used when painting widgets.

    Provides a QPainter to each widget for plotting.
    Records the controlgraphs for each widget.
    Holds the scaling, dpi and size of the page.
    """

    def __init__(self, pagesize, scaling=1., dpi=(100, 100),
                 directpaint=None):
        """Initialise using page size (tuple of pixelw, pixelh).

        If directpaint is set to a painter, use this directly rather
        than creating separate layers for rendering later. The user
        will need to call restore() on the painter before ending, if
        using this mode, however.
        """

        self.dpi = dpi
        self.scaling = scaling
        self.pixperpt = self.dpi[1] / 72.
        self.pagesize = pagesize

        # keep track of states of all widgets
        self.states = {}

        # axis to plotter mappings
        self.axisplottermap = {}

        # whether to directly render to a painter or make new layers
        self.directpaint = directpaint
        self.directpainting = False

        # state for root widget
        self.rootstate = None

    @property
    def maxsize(self):
        """Return maximum page dimension (using PaintHelper's DPI)."""
        return max(*self.pagesize)

    def sizeAtDpi(self, dpi):
        """Return a tuple size for the page given an output device dpi."""
        return ( int(self.pagesize[0]/self.dpi[0] * dpi),
                 int(self.pagesize[1]/self.dpi[1] * dpi) )

    def updatePageSize(self, pagew, pageh):
        """Update page size to value given (in user text units."""
        self.pagesize = ( setting.Distance.convertDistance(self, pagew),
                          setting.Distance.convertDistance(self, pageh) )

    def painter(self, widget, bounds, clip=None):
        """Return a painter for use when drawing the widget.
        widget: widget object
        bounds: tuple (x1, y1, x2, y2) of widget bounds
        clip: another tuple, if set clips drawing to this rectangle
        """
        s = self.states[widget] = DrawState(widget, bounds, clip, self)
        if widget.parent is None:
            self.rootstate = s
        else:
            self.states[widget.parent].children.append(s)

        if self.directpaint:
            # only paint to one output painter
            p = self.directpaint
            if self.directpainting:
                p.restore()
            self.directpainting = True
            p.save()
        else:
            # save to multiple recorded layers
            p = qt4.QPainter(s.record)

        p.scaling = self.scaling
        p.pixperpt = self.pixperpt
        p.pagesize = self.pagesize
        p.dpi = self.dpi[1]

        if clip:
            p.setClipRect(clip)

        return p

    def setControlGraph(self, widget, cgis):
        """Records the control graph list for the widget given."""
        self.states[widget].cgis = cgis

    def renderToPainter(self, painter):
        """Render saved output to painter.
        """
        self._renderState(self.rootstate, painter)

    def _renderState(self, state, painter):
        """Render state to painter."""

        painter.save()
        state.record.play(painter)
        painter.restore()

        for child in state.children:
            self._renderState(child, painter)

    def identifyWidgetAtPoint(self, x, y, antialias=True):
        """What widget has drawn at the point x,y?

        Returns the widget drawn last on the point, or None if it is
        an empty part of the page.
        root is the root widget to recurse from
        if antialias is true, do test for antialiased drawing
        """
        
        # make a small image filled with a specific color
        box = 3
        specialcolor = qt4.QColor(254, 255, 254)
        origpix = qt4.QPixmap(2*box+1, 2*box+1)
        origpix.fill(specialcolor)
        origimg = origpix.toImage()
        # store most recent widget here
        lastwidget = [None]
        
        def rendernextstate(state):
            """Recursively draw painter.

            Checks whether drawing a widgetchanges the small image
            around the point given.
            """

            pixmap = qt4.QPixmap(origpix)
            painter = qt4.QPainter(pixmap)
            painter.setRenderHint(qt4.QPainter.Antialiasing, antialias)
            painter.setRenderHint(qt4.QPainter.TextAntialiasing, antialias)
            # this makes the small image draw from x-box->x+box, y-box->y+box
            # translate would get overriden by coordinate system playback
            painter.setWindow(x-box,y-box,box*2+1,box*2+1)
            state.record.play(painter)
            painter.end()
            newimg = pixmap.toImage()

            if newimg != origimg:
                lastwidget[0] = state.widget

            for child in state.children:
                rendernextstate(child)

        rendernextstate(self.rootstate)
        return lastwidget[0]

    def pointInWidgetBounds(self, x, y, widgettype):
        """Which graph widget plots at point x,y?

        Recurse from widget root
        widgettype is the class of widget to get
        """

        widget = [None]

        def recursestate(state):
            if isinstance(state.widget, widgettype):
                b = state.bounds
                if x >= b[0] and y >= b[1] and x <= b[2] and y <= b[3]:
                    # most recent widget drawing on point
                    widget[0] = state.widget

            for child in state.children:
                recursestate(child)

        recursestate(self.rootstate)
        return widget[0]

    def widgetBounds(self, widget):
        """Return bounds of widget."""
        return self.states[widget].bounds

    def widgetBoundsIterator(self, widgettype=None):
        """Returns bounds for each widget.
        Set widgettype to be a widget type to filter returns
        Yields (widget, bounds)
        """

        # this is a recursive algorithm turned into an iterative one
        # which makes creation of a generator easier
        stack = [self.rootstate]
        while stack:
            state = stack[0]
            if widgettype is None or isinstance(state.widget, widgettype):
                yield state.widget, state.bounds
            # remove the widget itself from the stack and insert children
            stack = state.children + stack[1:]

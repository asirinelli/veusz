# root.py
# Represents the root widget for plotting the document

#    Copyright (C) 2004 Jeremy S. Sanders
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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
##############################################################################

# $Id$

import qt

import widget
import widgetfactory
import setting

class Root(widget.Widget):
    """Root widget class for plotting the document."""

    typename='document'
    allowusercreation = False
    allowedparenttypes = [None]

    def __init__(self, parent, name=None):
        """Initialise object."""

        widget.Widget.__init__(self, parent, name=name)
        s = self.settings
        s.add( setting.Distance('width', '20cm',
                                descr='Width of the pages') )
        s.add( setting.Distance('height', '20cm',
                                descr='Height of the pages') )
        s.readDefaults()

    def draw(self, parentposn, painter):
        """Draw the plotter. Clip graph inside bounds."""

        x1, y1, x2, y2 = parentposn

        painter.save()
        painter.setClipRect( qt.QRect(x1, y1, x2-x1, y2-y1) )
        bounds = widget.Widget.draw(self, parentposn, painter)
        painter.restore()

        return bounds

# allow the factory to instantiate this
widgetfactory.thefactory.register( Root )
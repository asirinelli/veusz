#    Copyright (C) 2010 Jeremy S. Sanders
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
###############################################################################

"""For making box plots."""

import math
from itertools import izip
import numpy as N

import veusz.qtall as qt4
import veusz.setting as setting
import veusz.document as document
import veusz.utils as utils

from plotters import GenericPlotter

def percentile(sortedds, perc):
    """Given a sorted dataset, get the percentile perc.

    Interpolates between data points."""

    index = perc * 0.01 * (sortedds.shape[0]-1)

    # interpolate between indices
    frac, index = math.modf(index)
    index = int(index)
    indexplus1 = min(index+1, sortedds.shape[0]-1)
    interpol = (1-frac)*sortedds[index] + frac*sortedds[indexplus1]
    return interpol

def swapline(painter, x1, y1, x2, y2, swap):
    """Draw line, swapping x and y coordinates if swap is True."""
    if swap:
        painter.drawLine( qt4.QPointF(y1, x1), qt4.QPointF(y2, x2) )
    else:
        painter.drawLine( qt4.QPointF(x1, y1), qt4.QPointF(x2, y2) )

def swapbox(painter, x1, y1, x2, y2, swap):
    """Draw box, swapping x and y coordinates if swap is True."""
    if swap:
        painter.drawRect( qt4.QRectF(qt4.QPointF(y1, x1),
                                     qt4.QPointF(y2, x2)) )
    else:
        painter.drawRect( qt4.QRectF(qt4.QPointF(x1, y1),
                                     qt4.QPointF(x2, y2)) )

class _Stats(object):
    """Store statistics about box."""

    def calculate(self, data, whiskermode):
        """Calculate statistics for data."""
        cleaned = data[ N.isfinite(data) ]
        cleaned.sort()

        self.median = percentile(cleaned, 50)
        self.botquart = percentile(cleaned, 25)
        self.topquart = percentile(cleaned, 75)
        self.mean = N.mean(cleaned)
        
        if whiskermode == 'min/max':
            self.botwhisker = cleaned.min()
            self.topwhisker = cleaned.max()
        elif whiskermode == '1.5IQR':
            iqr = self.topquart - self.botquart
            eltop = N.searchsorted(cleaned, self.topquart+1.5*iqr)-1
            self.topwhisker = cleaned[eltop]
            elbot = max(N.searchsorted(cleaned, self.botquart-1.5*iqr)-1, 0)
            self.botwhisker = cleaned[elbot]
        elif whiskermode == '1 stddev':
            stddev = N.std(cleaned)
            self.topwhisker = self.mean+stddev
            self.botwhisker = self.mean-stddev
        elif whiskermode == '9/91 percentile':
            self.topwhisker = percentile(cleaned, 91)
            self.botwhisker = percentile(cleaned, 9)
        elif whiskermode == '2/98 percentile':
            self.topwhisker = percentile(cleaned, 98)
            self.botwhisker = percentile(cleaned, 2)
        else:
            raise RuntimeError, "Invalid whisker mode"

        self.outliers = cleaned[ (cleaned < self.botwhisker) |
                                 (cleaned > self.topwhisker) ]

class BoxPlot(GenericPlotter):
    """Plot bar charts."""

    typename='boxplot'
    allowusercreation=True
    description='Plot box plots'

    def __init__(self, parent, name=None):
        """Initialise box plot."""
        GenericPlotter.__init__(self, parent, name=name)
        if type(self) == BoxPlot:
            self.readDefaults()

    @classmethod
    def addSettings(klass, s):
        """Construct list of settings."""
        GenericPlotter.addSettings(s)

        s.remove('key')
        s.add( setting.Choice('whiskermode', 
                              ('min/max',
                               '1.5IQR',
                               '1 stddev',
                               '9/91 percentile',
                               '2/98 percentile'),
                              '1.5IQR', 
                              descr = 'Whisker mode', 
                              usertext='Whisker mode'), 0 )

        s.add( setting.Choice('direction', 
                              ('horizontal', 'vertical'), 'vertical', 
                              descr = 'Horizontal or vertical boxes', 
                              usertext='Direction'), 0 )
        s.add( setting.DatasetOrStr('labels', '',
                                    descr='Dataset or string to label bars',
                                    usertext='Labels', datatype='text'), 0 )
        s.add( setting.DatasetOrFloatList(
                'posn', '',
                descr = 'Dataset or list of values giving '
                'positions of boxes (optional)', usertext='Positions'), 0 )

        # calculate statistics from these datasets
        s.add( setting.Datasets('values', ('data',),
                                descr = 'Datasets containing values to '
                                'calculate statistics for',
                                usertext='Datasets'), 0 )

        # alternate mode where data are provided for boxes
        s.add( setting.DatasetOrFloatList(
                'whiskermax', '',
                descr='Dataset with whisker maxima or list of values',
                usertext='Whisker max'), 0 )
        s.add( setting.DatasetOrFloatList(
                'whiskermin', '',
                descr='Dataset with whisker minima or list of values',
                usertext='Whisker min'), 0 )
        s.add( setting.DatasetOrFloatList(
                'boxmax', '',
                descr='Dataset with box maxima or list of values',
                usertext='Box max'), 0 )
        s.add( setting.DatasetOrFloatList(
                'boxmin', '',
                descr='Dataset with box minima or list of values',
                usertext='Box min'), 0 )
        s.add( setting.DatasetOrFloatList(
                'median', '',
                descr='Dataset with medians or list of values',
                usertext='Median'), 0 )
        s.add( setting.DatasetOrFloatList(
                'mean', '',
                descr='Dataset with means or list of values',
                usertext='Mean'), 0 )

        # switch between different modes
        s.add( setting.BoolSwitch('calculate', True,
                                  descr = 'Calculate statistics from datasets'
                                  ' rather than given manually',
                                  usertext = 'Calculate',
                                  settingstrue=('whiskermode', 'values'),
                                  settingsfalse=('boxmin', 'whiskermin',
                                                 'boxmax', 'whiskermax',
                                                 'mean', 'median')), 0 )

        # formatting options
        s.add( setting.Float('fillfraction', 0.75,
                             descr = 'Fill fraction of boxes',
                             usertext='Fill fraction', formatting=True) )
        s.add( setting.Marker('outliersmarker',
                              'circle',
                              descr = 'Marker for outliers',
                              usertext='Outliers', formatting=True) )
        s.add( setting.Marker('meanmarker',
                              'linecross',
                              descr = 'Marker for mean',
                              usertext='Mean', formatting=True) )
        s.add( setting.DistancePt('markerSize',
                                  '3pt',
                                  descr = 'Size of markers to plot',
                                  usertext='Markers size', formatting=True) )

        s.add( setting.GraphBrush( 'Fill',
                                   descr = 'Box fill',
                                   usertext='Box fill'),
               pixmap='settings_bgfill' )
        s.add( setting.Line('Border', descr = 'Box border line',
                            usertext='Box border'),
               pixmap='settings_border')
        s.add( setting.Line('Whisker', descr = 'Whisker line',
                            usertext='Whisker line'),
               pixmap='settings_whisker')
        s.add( setting.Line('MarkersLine',
                            descr = 'Line around markers',
                            usertext = 'Markers border'),
               pixmap = 'settings_plotmarkerline' )
        s.add( setting.GraphBrush('MarkersFill',
                                  descr = 'Markers fill',
                                  usertext = 'Markers fill'),
               pixmap = 'settings_plotmarkerfill' )

    @property
    def userdescription(self):
        """Friendly description for user."""
        s = self.settings
        return "values='%s', position='%s'" % (
            ', '.join(s.values),  s.posn)

    def providesAxesDependency(self):
        """This widget provides range information about these axes."""
        s = self.settings
        return ( (s.xAxis, 'sx'), (s.yAxis, 'sy') )

    def rangeManual(self):
        """For updating range in manual mode."""
        s = self.settings
        ds = []
        for name in ('whiskermin', 'whiskermax', 'boxmin', 'boxmax',
                     'mean', 'median'):
            ds.append( s.get(name).getData(self.document) )
        r = [N.inf, -N.inf]
        if None not in ds:
            concat = N.concatenate([d.data for d in ds])
            r[0] = N.nanmin(concat)
            r[1] = N.nanmax(concat)
        return r

    def getPosns(self):
        """Get values of positions of bars."""

        s = self.settings
        doc = self.document

        posns = s.get('posn').getData(doc)
        if posns is not None:
            # manual positions
            return posns.data
        else:
            if s.calculate:
                # number of datasets
                vals = s.get('values').getData(doc)
            else:
                # length of mean array
                vals = s.get('mean').getData(doc)
                if vals:
                    vals = vals.data

            if vals is None:
                return N.array([])
            else:
                return N.arange(1, len(vals)+1, dtype=N.float64)

    def updateAxisRange(self, axis, depname, axrange):
        """Update axis range from data."""

        s = self.settings
        doc = self.document

        if ( (depname == 'sx' and s.direction == 'horizontal') or
             (depname == 'sy' and s.direction == 'vertical') ):
            # update axis in direction of data
            if s.calculate:
                # update from values
                values = s.get('values').getData(doc)
                if values:
                    for v in values:
                        axrange[0] = min(axrange[0], N.nanmin(v.data))
                        axrange[1] = max(axrange[1], N.nanmax(v.data))
            else:
                # update from manual entries
                drange = self.rangeManual()
                axrange[0] = min(axrange[0], drange[0])
                axrange[1] = max(axrange[1], drange[1])
        else:
            # update axis in direction of datasets
            posns = self.getPosns()
            if len(posns) > 0:
                axrange[0] = min(axrange[0], N.nanmin(posns)-0.5)
                axrange[1] = max(axrange[1], N.nanmax(posns)+0.5)

    def getAxisLabels(self, direction):
        """Get labels for axis if using a label axis."""

        s = self.settings
        doc = self.document
        text = s.get('labels').getData(doc, checknull=True)
        values = s.get('values').getData(doc)
        if text is None or values is None:
            return (None, None)
        positions = self.getPosns()
        return (text, positions)

    def calcStats(self, data):
        """Calculate statistics for data."""

        stats = _Stats()

    def plotBox(self, painter, axes, boxposn, posn, width, clip, stats):
        """Draw box for dataset."""

        s = self.settings
        horz = (s.direction == 'horizontal')

        # convert quartiles, top and bottom whiskers to plotter
        medplt, botplt, topplt, botwhisplt, topwhisplt = tuple(
            axes[not horz].dataToPlotterCoords(
                posn,
                N.array([ stats.median, stats.botquart, stats.topquart,
                          stats.botwhisker, stats.topwhisker ]))
            )

        # draw whisker top to bottom
        p = s.Whisker.makeQPenWHide(painter)
        p.setCapStyle(qt4.Qt.FlatCap)
        painter.setPen(p)
        swapline(painter, boxposn, topwhisplt, boxposn, botwhisplt, horz)
        # draw ends of whiskers
        endsize = width/2
        swapline(painter, boxposn-endsize/2, topwhisplt,
                 boxposn+endsize/2, topwhisplt, horz)
        swapline(painter, boxposn-endsize/2, botwhisplt,
                 boxposn+endsize/2, botwhisplt, horz)

        # draw box fill
        painter.setPen( qt4.QPen(qt4.Qt.NoPen) )
        painter.setBrush( s.Fill.makeQBrushWHide() )
        swapbox(painter, boxposn-width/2, botplt,
                boxposn+width/2, topplt, horz)

        # draw line across box
        p = s.Whisker.makeQPenWHide(painter)
        p.setCapStyle(qt4.Qt.FlatCap)
        painter.setPen(p)
        swapline(painter, boxposn-width/2, medplt,
                 boxposn+width/2, medplt, horz)

        # draw box
        painter.setPen( s.Border.makeQPenWHide(painter) )
        painter.setBrush( qt4.QBrush() )
        swapbox(painter, boxposn-width/2, botplt,
                boxposn+width/2, topplt, horz)

        # draw outliers
        painter.setPen( s.MarkersLine.makeQPenWHide(painter) )
        painter.setBrush( s.MarkersFill.makeQBrushWHide() )
        markersize = s.get('markerSize').convert(painter)
        if stats.outliers.shape[0] != 0:
            pltvals = axes[not horz].dataToPlotterCoords(posn, stats.outliers)
            otherpos = N.zeros(pltvals.shape) + boxposn
            if horz:
                x, y = pltvals, otherpos
            else:
                x, y = otherpos, pltvals

            utils.plotMarkers( painter, x, y, s.outliersmarker,
                               markersize, clip=clip )

        # draw mean
        meanplt = axes[not horz].dataToPlotterCoords(
            posn, N.array([stats.mean]))[0]
        if horz:
            x, y = meanplt, boxposn
        else:
            x, y = boxposn, meanplt
        utils.plotMarker( painter, x, y, s.meanmarker, markersize )

    def draw(self, parentposn, phelper, outerbounds=None):
        """Plot the data on a plotter."""

        widgetposn = GenericPlotter.draw(self, parentposn, phelper,
                                         outerbounds=outerbounds)
        s = self.settings

        # exit if hidden
        if s.hide:
            return

        # get data
        doc = self.document
        positions = self.getPosns()
        if s.calculate:
            # calculate from data
            values = s.get('values').getData(doc)
            if values is None:
                return
        else:
            # use manual datasets
            datasets = [ s.get(x).getData(doc) for x in
                         ('whiskermin', 'whiskermax', 'boxmin',
                          'boxmax', 'mean', 'median') ]
            if None in datasets:
                return

        # get axes widgets
        axes = self.parent.getAxes( (s.xAxis, s.yAxis) )

        # return if there are no proper axes
        if ( None in axes or
             axes[0].settings.direction != 'horizontal' or
             axes[1].settings.direction != 'vertical' ):
            return

        clip = self.clipAxesBounds(axes, widgetposn)
        painter = phelper.painter(self, widgetposn, clip=clip)

        # get boxes visible along direction of boxes to work out width
        horz = (s.direction == 'horizontal')
        plotposns = axes[horz].dataToPlotterCoords(widgetposn, positions)

        if horz:
            inplot = (plotposns > widgetposn[1]) & (plotposns < widgetposn[3])
        else:
            inplot = (plotposns > widgetposn[0]) & (plotposns < widgetposn[2])
        inplotposn = plotposns[inplot]
        if inplotposn.shape[0] < 2:
            if horz:
                width = (widgetposn[3]-widgetposn[1])*0.5
            else:
                width = (widgetposn[2]-widgetposn[0])*0.5
        else:
            # use minimum different between points to get width
            inplotposn.sort()
            width = N.nanmin(inplotposn[1:] - inplotposn[:-1])

        # adjust width
        width = width * s.fillfraction

        if s.calculate:
            # calculated boxes
            for vals, plotpos in izip(values, plotposns):
                stats = _Stats()
                stats.calculate(vals.data, s.whiskermode)
                self.plotBox(painter, axes, plotpos, widgetposn, width,
                             clip, stats)
        else:
            # manually given boxes
            vals = [d.data for d in datasets] + [plotposns]
            lens = [len(d) for d in vals]
            for i in xrange(min(lens)):
                stats = _Stats()
                stats.topwhisker = vals[0][i]
                stats.botwhisker = vals[1][i]
                stats.botquart = vals[2][i]
                stats.topquart = vals[3][i]
                stats.mean = vals[4][i]
                stats.median = vals[5][i]
                stats.outliers = N.array([])
                self.plotBox(painter, axes, vals[6][i], widgetposn,
                             width, clip, stats)

# allow the factory to instantiate a boxplot
document.thefactory.register( BoxPlot )

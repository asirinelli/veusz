# -*- coding: utf-8 -*-
#    Copyright (C) 2005 Jeremy S. Sanders
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

"""Module for creating QWidgets for the settings, to enable their values
   to be changed.

    These widgets emit settingChanged(control, setting, val) when the setting is
    changed. The creator should use this to change the setting.
"""

from itertools import izip
import re

import veusz.qtall as qt4

import setting

import veusz.utils as utils

def styleClear(widget):
    """Return widget to default"""
    widget.setStyleSheet("")

def styleError(widget):
    """Show error state on widget."""
    widget.setStyleSheet("background-color: " +
                         setting.settingdb.color('error').name() )

class DotDotButton(qt4.QPushButton):
    """A button for opening up more complex editor."""
    def __init__(self, tooltip=None, checkable=True):
        qt4.QPushButton.__init__(self, "..")
        if tooltip:
            self.setToolTip(tooltip)
        self.setFlat(True)
        self.setSizePolicy(qt4.QSizePolicy.Maximum, qt4.QSizePolicy.Maximum)
        self.setMaximumWidth(16)
        self.setCheckable(checkable)

class Edit(qt4.QLineEdit):
    """Main control for editing settings which are text."""

    def __init__(self, setting, parent):
        """Initialise the setting widget."""

        qt4.QLineEdit.__init__(self, parent)
        self.setting = setting

        # set the text of the widget to the 
        self.setText( setting.toText() )

        self.connect(self, qt4.SIGNAL('editingFinished()'),
                     self.validateAndSet)

        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.setReadOnly(True)

    def validateAndSet(self):
        """Check the text is a valid setting and update it."""

        text = unicode(self.text())
        try:
            val = self.setting.fromText(text)
            styleClear(self)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

        except setting.InvalidType:
            styleError(self)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.setText( self.setting.toText() )

class _EditBox(qt4.QTextEdit):
    """A popup edit box to support editing long text sections.

    Emits closing(text) when the box closes
    """

    def __init__(self, origtext, readonly, parent):
        """Make a popup, framed widget containing a text editor."""

        qt4.QTextEdit.__init__(self, parent)
        self.setWindowFlags(qt4.Qt.Popup)
        self.setAttribute(qt4.Qt.WA_DeleteOnClose)

        self.spacing = self.fontMetrics().height()

        self.origtext = origtext
        self.setPlainText(origtext)

        cursor = self.textCursor()
        cursor.movePosition(qt4.QTextCursor.End)
        self.setTextCursor(cursor)

        if readonly:
            self.setReadOnly(True)

        utils.positionFloatingPopup(self, parent)

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        """Grab clicks outside this window to close it."""
        if ( isinstance(event, qt4.QMouseEvent) and
             event.buttons() != qt4.Qt.NoButton ):
            frame = qt4.QRect(0, 0, self.width(), self.height())
            if not frame.contains(event.pos()):
                self.close()
                return True
        return qt4.QTextEdit.eventFilter(self, obj, event)

    def keyPressEvent(self, event):
        """Close if escape or return is pressed."""
        qt4.QTextEdit.keyPressEvent(self, event)

        key = event.key()
        if key == qt4.Qt.Key_Escape:
            # restore original content
            self.setPlainText(self.origtext)
            self.close()
        elif key == qt4.Qt.Key_Return:
            # keep changes
            self.close()

    def sizeHint(self):
        """A reasonable size for the text editor."""
        return qt4.QSize(self.spacing*40, self.spacing*3)

    def closeEvent(self, event):
        """Tell the calling widget that we are closing, and provide
        the new text."""

        text = unicode(self.toPlainText())
        text = text.replace('\n', '')
        self.emit(qt4.SIGNAL('closing'), text)
        event.accept()

class String(qt4.QWidget):
    """A line editor which allows editting in a larger popup window."""

    def __init__(self, setting, parent):
        qt4.QWidget.__init__(self, parent)
        self.setting = setting

        layout = qt4.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        self.setLayout(layout)

        self.edit = qt4.QLineEdit()
        layout.addWidget(self.edit)

        b = self.button = DotDotButton(tooltip="Edit text")
        layout.addWidget(b)

        # set the text of the widget to the 
        self.edit.setText( setting.toText() )

        self.connect(self.edit, qt4.SIGNAL('editingFinished()'),
                     self.validateAndSet)
        self.connect(b, qt4.SIGNAL('toggled(bool)'),
                     self.buttonToggled)

        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.edit.setReadOnly(True)

    def buttonToggled(self, on):
        """Button is pressed to bring popup up / down."""

        # if button is down and there's no existing popup, bring up a new one
        if on:
            e = _EditBox( unicode(self.edit.text()),
                          self.setting.readonly, self.button)

            # we get notified with text when the popup closes
            self.connect(e, qt4.SIGNAL('closing'), self.boxClosing)
            e.show()

    def boxClosing(self, text):
        """Called when the popup edit box closes."""

        # update the text if we can
        if not self.setting.readonly:
            self.edit.setText(text)
            self.edit.setFocus()
            self.parentWidget().setFocus()
            self.edit.setFocus()

        self.button.setChecked(False)

    def validateAndSet(self):
        """Check the text is a valid setting and update it."""

        text = unicode(self.edit.text())
        try:
            val = self.setting.fromText(text)
            styleClear(self.edit)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

        except setting.InvalidType:
            styleError(self.edit)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.edit.setText( self.setting.toText() )

class Int(qt4.QSpinBox):
    """A control for changing an integer."""

    def __init__(self, setting, parent):
        qt4.QSpinBox.__init__(self, parent)

        self.ignorechange = False
        self.setting = setting
        self.setMinimum(setting.minval)
        self.setMaximum(setting.maxval)
        self.setValue(setting.val)

        self.connect(self, qt4.SIGNAL('valueChanged(int)'), self.slotChanged)
        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.setEnabled(False)            

    def slotChanged(self, value):
        """If check box changes."""
        # this is emitted by setValue, so ignore onModified doing this
        if not self.ignorechange:
            self.emit(qt4.SIGNAL('settingChanged'), self, self.setting, value)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.ignorechange = True
        self.setValue( self.setting.val )
        self.ignorechange = False

class Bool(qt4.QCheckBox):
    """A check box for changing a bool setting."""
    
    def __init__(self, setting, parent):
        qt4.QCheckBox.__init__(self, parent)

        self.ignorechange = False
        self.setting = setting
        self.setChecked(setting.val)

        # we get a signal when the button is toggled
        self.connect( self, qt4.SIGNAL('toggled(bool)'),
                      self.slotToggled )

        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.setEnabled(False)

    def slotToggled(self, state):
        """Emitted when checkbox toggled."""
        # this is emitted by setChecked, so ignore onModified doing this
        if not self.ignorechange:
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, state )
        
    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.ignorechange = True
        self.setChecked( self.setting.val )
        self.ignorechange = False

class BoolSwitch(Bool):
    """Bool for switching off/on other settings."""

    def showEvent(self, event):
        Bool.showEvent(self, event)
        self.updateState()

    def slotToggled(self, state):
        Bool.slotToggled(self, state)
        self.updateState()

    def updateState(self):
        """Set hidden state of settings."""
        s1, s2 = self.setting.strue, self.setting.sfalse
        if self.setting.val:
            show, hide = s1, s2
        else:
            show, hide = s2, s1

        if hasattr(self.parent(), 'showHideSettings'):
            self.parent().showHideSettings(show, hide)

class Choice(qt4.QComboBox):
    """For choosing between a set of values."""

    def __init__(self, setting, iseditable, vallist, parent, icons=None,
                 descriptions=None):
        qt4.QComboBox.__init__(self, parent)

        self.setting = setting

        self.setEditable(iseditable)

        # stops combobox readjusting in size to fit contents
        self.setSizeAdjustPolicy(
            qt4.QComboBox.AdjustToMinimumContentsLengthWithIcon)

        if icons is None:
            # add items to list (text only)
            self.addItems( list(vallist) )
        else:
            # add pixmaps and text to list
            for icon, text in izip(icons, vallist):
                self.addItem(icon, text)

        # use tooltip descriptions if requested
        if descriptions is not None:
            for i, descr in enumerate(descriptions):
                self.setItemData(i, qt4.QVariant(descr), qt4.Qt.ToolTipRole)

        # choose the correct setting
        try:
            index = list(vallist).index(setting.toText())
            self.setCurrentIndex(index)
        except ValueError:
            # for cases when this is editable
            # set the text of the widget to the setting
            assert iseditable
            self.setEditText( setting.toText() )

        # if a different item is selected
        self.connect( self, qt4.SIGNAL('activated(const QString&)'),
                      self.slotActivated )

        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.setEnabled(False)

        # make completion case sensitive (to help fix case typos)
        if self.completer():
            self.completer().setCaseSensitivity(qt4.Qt.CaseSensitive)

    def focusOutEvent(self, *args):
        """Allows us to check the contents of the widget."""
        qt4.QComboBox.focusOutEvent(self, *args)
        self.slotActivated('')

    def slotActivated(self, val):
        """If a different item is chosen."""

        text = unicode(self.currentText())
        try:
            val = self.setting.fromText(text)
            styleClear(self)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

        except setting.InvalidType:
            styleError(self)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        text = self.setting.toText()
        index = self.findText(text)
        if index >= 0:
            self.setCurrentIndex(index)
        if self.isEditable():
            self.setEditText(text)

class MultiLine(qt4.QTextEdit):
    """For editting multi-line settings."""

    def __init__(self, setting, parent):
        """Initialise the widget."""

        qt4.QTextEdit.__init__(self, parent)
        self.setting = setting

        self.setWordWrapMode(qt4.QTextOption.NoWrap)
        self.setTabChangesFocus(True)
        
        # set the text of the widget to the 
        self.setPlainText( setting.toText() )

        self.setting.setOnModified(self.onModified)

        if setting.readonly:
            self.setReadOnly(True)

    def focusOutEvent(self, *args):
        """Allows us to check the contents of the widget."""
        qt4.QTextEdit.focusOutEvent(self, *args)

        text = unicode(self.toPlainText())
        try:
            val = self.setting.fromText(text)
            styleClear(self)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

        except setting.InvalidType:
            styleError(self)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.setPlainText( self.setting.toText() )

class Distance(Choice):
    """For editing distance settings."""

    # used to remove non-numerics from the string
    # we also remove X/ from X/num
    stripnumre = re.compile(r"[0-9]*/|[^0-9.,]")

    # remove spaces
    stripspcre = re.compile(r"\s")

    def __init__(self, setting, parent, allowauto=False):
        '''Initialise with blank list, then populate with sensible units.'''
        Choice.__init__(self, setting, True, [], parent)
        self.allowauto = allowauto
        self.updateComboList()
        
    def updateComboList(self):
        '''Populates combo list with sensible list of other possible units.'''

        # turn off signals, so our modifications don't create more signals
        self.blockSignals(True)

        # get current text
        text = unicode(self.currentText())

        # get rid of non-numeric things from the string
        num = self.stripnumre.sub('', text)

        # here are a list of possible different units the user can choose
        # between. should this be in utils?
        newitems = [ num+'pt', num+'cm', num+'mm',
                     num+'in', num+'%', '1/'+num ]

        if self.allowauto:
            newitems.insert(0, 'Auto')

        # if we're already in this list, we position the current selection
        # to the correct item (up and down keys work properly then)
        # spaces are removed to make sure we get sensible matches
        spcfree = self.stripspcre.sub('', text)
        try:
            index = newitems.index(spcfree)
        except ValueError:
            index = 0
            newitems.insert(0, text)

        # get rid of existing items in list (clear doesn't work here)
        for i in range(self.count()):
            self.removeItem(0)

        # put new items in and select the correct option
        self.addItems(newitems)
        self.setCurrentIndex(index)

        # must remember to do this!
        self.blockSignals(False)

    def slotActivated(self, val):
        '''Populate the drop down list before activation.'''
        self.updateComboList()
        Choice.slotActivated(self, val)

class DistancePt(Choice):
    """For editing distances with defaults in points."""

    points = (
        '0pt', '0.25pt', '0.5pt', '1pt', '1.5pt', '2pt', '3pt',
        '4pt', '5pt', '6pt', '8pt', '10pt', '12pt', '14pt', '16pt',
        '18pt', '20pt', '22pt', '24pt', '26pt', '28pt', '30pt',
        '34pt', '40pt', '44pt', '50pt', '60pt', '70pt'
        )
    
    def __init__(self, setting, parent, allowauto=False):
        '''Initialise with blank list, then populate with sensible units.'''
        Choice.__init__(self, setting, True, DistancePt.points, parent)
        
class Dataset(qt4.QWidget):
    """Allow the user to choose between the possible datasets."""

    def __init__(self, setting, document, dimensions, datatype, parent):
        """Initialise the combobox. The list is populated with datasets.

        dimensions specifies the dimension of the dataset to list

        Changes on the document refresh the list of datasets."""
        
        qt4.QWidget.__init__(self, parent)

        self.choice = Choice(setting, True, [], None)
        self.connect( self.choice, qt4.SIGNAL("settingChanged"),
                      self.slotSettingChanged )

        b = self.button = DotDotButton(tooltip="Select using dataset browser")
        self.connect(b, qt4.SIGNAL("toggled(bool)"),
                     self.slotButtonToggled)

        self.document = document
        self.dimensions = dimensions
        self.datatype = datatype
        self.lastdatasets = None
        self._populateEntries()
        self.connect(document, qt4.SIGNAL("sigModified"), self.slotModified)

        layout = qt4.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(self.choice)
        layout.addWidget(b)
        self.setLayout(layout)

    def slotSettingChanged(self, *args):
        """Reemit setting changed signal if combo box changes."""
        self.emit( qt4.SIGNAL("settingChanged"), *args )

    def _populateEntries(self):
        """Put the list of datasets into the combobox."""

        # get datasets of the correct dimension
        datasets = []
        for name, ds in self.document.data.iteritems():
            if ds.dimensions == self.dimensions and ds.datatype == self.datatype:
                datasets.append(name)
        datasets.sort()

        if datasets != self.lastdatasets:
            utils.populateCombo(self.choice, datasets)
            self.lastdatasets = datasets

    def slotModified(self, modified):
        """Update the list of datasets if the document is modified."""
        self._populateEntries()

    def slotButtonToggled(self, on):
        """Bring up list of datasets."""
        if on:
            from veusz.qtwidgets.datasetbrowser import DatasetBrowserPopup
            d = DatasetBrowserPopup(self.document,
                                    unicode(self.choice.currentText()),
                                    self.button,
                                    filterdims=set((self.dimensions,)),
                                    filterdtype=set((self.datatype,)) )
            self.connect(d, qt4.SIGNAL("closing"), self.boxClosing)
            self.connect(d, qt4.SIGNAL("newdataset"), self.newDataset)
            d.show()

    def boxClosing(self):
        """Called when the popup edit box closes."""
        self.button.setChecked(False)

    def newDataset(self, dsname):
        """New dataset selected."""
        self.emit( qt4.SIGNAL("settingChanged"), self,
                   self.choice.setting, dsname )

class DatasetOrString(Dataset):
    """Allow use to choose a dataset or enter some text."""

    def __init__(self, setting, document, dimensions, datatype, parent):
        Dataset.__init__(self, setting, document, dimensions, datatype, parent)

        b = self.textbutton = DotDotButton()
        b.setCheckable(True)
        self.layout().addWidget(b)
        self.connect(b, qt4.SIGNAL('toggled(bool)'), self.textButtonToggled)

    def textButtonToggled(self, on):
        """Button is pressed to bring popup up / down."""

        # if button is down and there's no existing popup, bring up a new one
        if on:
            e = _EditBox( unicode(self.choice.currentText()),
                          self.choice.setting.readonly, self.textbutton)

            # we get notified with text when the popup closes
            self.connect(e, qt4.SIGNAL("closing"), self.textBoxClosing)
            e.show()

    def textBoxClosing(self, text):
        """Called when the popup edit box closes."""

        self.textbutton.setChecked(False)

        # update the text if we can
        if not self.choice.setting.readonly:
            self.choice.setEditText(text)
            self.choice.setFocus()
            self.parentWidget().setFocus()
            self.choice.setFocus()

class FillStyle(Choice):
    """For choosing between fill styles."""

    _icons = None
    _fills = None
    _fillcnvt = None

    def __init__(self, setting, parent):
        if self._icons is None:
            self._generateIcons()

        Choice.__init__(self, setting, False,
                        self._fills, parent,
                        icons=self._icons)

    @classmethod
    def _generateIcons(cls):
        """Generate a list of pixmaps for drop down menu."""

        size = 12
        icons = []
        c = qt4.QColor('grey')
        for f in cls._fills:
            pix = qt4.QPixmap(size, size)
            pix.fill()
            painter = qt4.QPainter(pix)
            painter.setRenderHint(qt4.QPainter.Antialiasing)
            brush = qt4.QBrush(c, cls._fillcnvt[f])
            painter.fillRect(0, 0, size, size, brush)
            painter.end()
            icons.append( qt4.QIcon(pix) )

        cls._icons = icons

class Marker(Choice):
    """A control to let the user choose a marker."""

    _icons = None

    def __init__(self, setting, parent):
        if self._icons is None:
            self._generateIcons()

        Choice.__init__(self, setting, False,
                        utils.MarkerCodes, parent,
                        icons=self._icons)

    @classmethod
    def _generateIcons(cls):
        size = 16
        icons = []
        brush = qt4.QBrush( qt4.QColor('darkgrey') )
        pen = qt4.QPen( qt4.QBrush(qt4.Qt.black), 1. )
        for marker in utils.MarkerCodes:
            pix = qt4.QPixmap(size, size)
            pix.fill()
            painter = qt4.QPainter(pix)
            painter.setRenderHint(qt4.QPainter.Antialiasing)
            painter.setBrush(brush)
            painter.setPen(pen)
            utils.plotMarker(painter, size*0.5, size*0.5, marker, size*0.33)
            painter.end()
            icons.append( qt4.QIcon(pix) )

        cls._icons = icons

class Arrow(Choice):
    """A control to let the user choose an arrowhead."""

    _icons = None

    def __init__(self, setting, parent):
        if self._icons is None:
            self._generateIcons()

        Choice.__init__(self, setting, False,
                        utils.ArrowCodes, parent,
                        icons=self._icons)

    @classmethod
    def _generateIcons(cls):
        size = 16
        icons = []
        brush = qt4.QBrush(qt4.Qt.black)
        pen = qt4.QPen( qt4.QBrush(qt4.Qt.black), 1. )
        for arrow in utils.ArrowCodes:
            pix = qt4.QPixmap(size, size)
            pix.fill()
            painter = qt4.QPainter(pix)
            painter.setRenderHint(qt4.QPainter.Antialiasing)
            painter.setBrush(brush)
            painter.setPen(pen)
            utils.plotLineArrow(painter, size*0.4, size*0.5,
                                size*2, 0.,
                                arrowsize=size*0.2,
                                arrowleft=arrow, arrowright=arrow)
            painter.end()
            icons.append( qt4.QIcon(pix) )

        cls._icons = icons

class LineStyle(Choice):
    """For choosing between line styles."""

    _icons = None
    _lines = None
    _linecnvt = None

    size = (24, 8)

    def __init__(self, setting, parent):
        if self._icons is None:
            self._generateIcons()

        Choice.__init__(self, setting, False,
                        self._lines, parent,
                        icons=self._icons)
        self.setIconSize( qt4.QSize(*self.size) )

    @classmethod
    def _generateIcons(cls):
        """Generate a list of icons for drop down menu."""

        # import later for dependency issues
        import veusz.setting.collections
        import veusz.document

        icons = []
        size = cls.size
        setn = veusz.setting.collections.Line('temp')
        setn.get('color').set('black')
        setn.get('width').set('1pt')
        
        for lstyle in cls._lines:
            pix = qt4.QPixmap(*size)
            pix.fill()

            ph = veusz.document.PaintHelper( (1, 1) )

            painter = qt4.QPainter(pix)
            painter.setRenderHint(qt4.QPainter.Antialiasing)

            setn.get('style').set(lstyle)
            
            painter.setPen( setn.makeQPen(ph) )
            painter.drawLine( int(size[0]*0.1), size[1]/2,
                              int(size[0]*0.9), size[1]/2 )
            painter.end()
            icons.append( qt4.QIcon(pix) )

        cls._icons = icons

class Color(qt4.QWidget):
    """A control which lets the user choose a color.

    A drop down list and a button to bring up a dialog are used
    """

    _icons = None
    _colors = None
    _qobj = None

    def __init__(self, setting,  parent):
        qt4.QWidget.__init__(self, parent)

        if self._icons is None:
            self._generateIcons()

        self.setting = setting
 
        # combo box
        c = self.combo = qt4.QComboBox()
        c.setEditable(True)
        for color in self._colors:
            c.addItem(self._icons[color], color)
        self.connect(c, qt4.SIGNAL('activated(const QString&)'),
                     self.slotActivated )

        # add color if a color is added by a different combo box
        self.connect(Color._qobj, qt4.SIGNAL('addcolor'), self.addcolorSlot)

        # button for selecting colors
        b = self.button = qt4.QPushButton()
        b.setFlat(True)
        b.setSizePolicy(qt4.QSizePolicy.Maximum, qt4.QSizePolicy.Maximum)
        b.setMaximumHeight(24)
        b.setMaximumWidth(24)
        self.connect(b, qt4.SIGNAL('clicked()'), self.slotButtonClicked)

        if setting.readonly:
            c.setEnabled(False)
            b.setEnabled(False)
                     
        layout = qt4.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        layout.addWidget(c)
        layout.addWidget(b)

        self.setColor( setting.toText() )
        self.setLayout(layout)
        self.setting.setOnModified(self.onModified)

    def addcolorSlot(self, color):
        """When another Color combo adds a color, add one to this one"""
        self.combo.addItem(self._icons[color], color)

    @classmethod
    def _generateIcons(cls):
        """Generate a list of icons for drop down menu.
        Does not generate existing icons
        """

        size = 12
        if cls._icons is None:
            cls._icons = {}
        
        icons = cls._icons
        for c in cls._colors:
            if c not in icons:
                pix = qt4.QPixmap(size, size)
                pix.fill( qt4.QColor(c) )
                icons[c] = qt4.QIcon(pix)
                if cls._qobj is not None:
                    # tell other combo boxes a color has been added
                    cls._qobj.emit(qt4.SIGNAL('addcolor'), c)

        if cls._qobj is None:
            cls._qobj = qt4.QObject()
    
    def slotButtonClicked(self):
        """Open dialog to edit color."""

        col = qt4.QColorDialog.getColor(self.setting.color(), self)
        if col.isValid():
            # change setting
            val = unicode( col.name() )
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

    def slotActivated(self, val):
        """A different value is selected."""
        
        text = unicode(self.combo.currentText())
        val = self.setting.fromText(text)
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

    def setColor(self, color):
        """Update control with color given."""

        # construct color icon if not there
        if color not in Color._icons:
            Color._colors.append(color)
            Color._generateIcons()
        
        # add text to combo if not there
        index = self.combo.findText(color)

        # set correct index in combobox
        self.combo.setCurrentIndex(index)
        self.button.setIcon( self.combo.itemIcon(index) )

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.setColor( self.setting.toText() )

class WidgetSelector(Choice):
    """For choosing from a list of widgets."""

    def __init__(self, setting, document, parent):
        """Initialise and populate combobox."""

        Choice.__init__(self, setting, True, [], parent)
        self.document = document
        self.connect(document, qt4.SIGNAL('sigModified'),
                     self.slotModified)

    def _populateEntries(self):
        pass
    
    def slotModified(self, modified):
        """Update list of axes."""
        self._populateEntries()

class Image(WidgetSelector):
    """Choose an image."""

    def __init__(self, setting, document, parent):
        """Initialise and populate combobox."""

        WidgetSelector.__init__(self, setting, document, parent)
        self._populateEntries()

    def _populateEntries(self):
        """Build up a list of images for combobox."""

        images = self.setting.getImageList()

        # we only need the list of names
        names = images.keys()
        names.sort()

        utils.populateCombo(self, names)

class Axis(WidgetSelector):
    """Choose an axis to plot against."""

    def __init__(self, setting, document, direction, parent):
        """Initialise and populate combobox."""

        WidgetSelector.__init__(self, setting, document, parent)
        self.direction = direction
        self._populateEntries()

    def _populateEntries(self):
        """Build up a list of possible axes."""

        # get parent widget
        widget = self.setting.parent
        while not widget.isWidget() and widget is not None:
            widget = widget.parent

        # get list of axis widgets up the tree
        axes = {}
        while widget is not None:
            for w in widget.children:
                try:
                    # succeeds if axis
                    if w.settings.direction == self.direction:
                        axes[w.name] = True
                except AttributeError:
                    pass
            widget = widget.parent

        names = axes.keys()
        names.sort()

        utils.populateCombo(self, names)

class ListSet(qt4.QFrame):
    """A widget for constructing settings which are lists of other
    properties.

    This code is pretty nasty and horrible, so we abstract it in this
    base widget
    """

    pixsize = 12

    def __init__(self, defaultval, setting, parent):
        """Initialise this base widget.

        defaultval is the default entry to add if add is clicked with
        no current entries

        setting is the setting this widget corresponds to

        parent is the parent widget.
        """
        
        qt4.QFrame.__init__(self, parent)
        self.setFrameStyle(qt4.QFrame.Box)
        self.defaultval = defaultval
        self.setting = setting
        self.controls = []
        self.layout = qt4.QGridLayout(self)
        self.layout.setMargin( self.layout.margin()/2 )
        self.layout.setSpacing( self.layout.spacing()/4 )

        # ignore changes if this set
        self.ignorechange = False

        self.populate()
        self.setting.setOnModified(self.onModified)
    
    def populateRow(self, row, val):
        """Populate the row in the control.

        Returns a list of the widgets created.
        """
        return None
    
    def populate(self):
        """Construct the list of controls."""

        # delete all children in case of refresh
        self.controls = []
        for c in self.children():
            if isinstance(c, qt4.QWidget):
                self.layout.removeWidget(c)
                c.deleteLater()
        c = None

        # iterate over each row
        row = -1
        for row, val in enumerate(self.setting.val):
            cntrls = self.populateRow(row, val)
            for i in cntrls:
                i.show()
            self.controls.append(cntrls)

        # buttons at end
        bbox = qt4.QWidget()
        h = qt4.QHBoxLayout(bbox)
        h.setMargin(0)
        bbox.setLayout(h)
        self.layout.addWidget(bbox, row+1, 0, 1, -1)
        
        # a button to add a new entry
        b = qt4.QPushButton('Add')
        h.addWidget(b)
        self.connect(b, qt4.SIGNAL('clicked()'), self.onAddClicked)
        b.show()

        # a button to delete the last entry
        b = qt4.QPushButton('Delete')
        h.addWidget(b)
        self.connect(b, qt4.SIGNAL('clicked()'), self.onDeleteClicked)
        b.setEnabled( len(self.setting.val) > 0 )
        b.show()

    def polish(self):
        """Remove tooltip from widget - avoid Qt bugs."""
        qt4.QVBox.polish(self)
        qt4.QToolTip.remove(self)

    def onAddClicked(self):
        """Add a line style to the list given."""

        rows = list(self.setting.val)
        if len(rows) != 0:
            rows.append(rows[-1])
        else:
            rows.append(self.defaultval)
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, rows )

    def onDeleteClicked(self):
        """Remove final entry in settings list."""

        rows = list(self.setting.val)[:-1]
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, rows )

    def onModified(self, mod):
        """called when the setting is changed remotely"""

        if not self.ignorechange:
            self.populate()
        else:
            self.ignorechange = False

    def identifyPosn(self, widget):
        """Identify the position this widget is in.

        Returns (row, col) or (None, None) if not found.
        """

        for row, cntrls in enumerate(self.controls):
            for col, cntrl in enumerate(cntrls):
                if cntrl == widget:
                    return (row, col)
        return (None, None)

    def addColorButton(self, row, col, tooltip):
        """Add a color button to the list at the position specified."""

        color = self.setting.val[row][col]
        wcolor = qt4.QPushButton()
        self.layout.addWidget(wcolor, row, col)
        wcolor.setMaximumWidth(wcolor.height())
        pix = qt4.QPixmap(self.pixsize, self.pixsize)
        pix.fill( utils.extendedColorToQColor(color) )
        wcolor.setIcon( qt4.QIcon(pix) )
        wcolor.setToolTip(tooltip)
        wcolor.setSizePolicy(qt4.QSizePolicy.Maximum, qt4.QSizePolicy.Maximum)

        self.connect(wcolor, qt4.SIGNAL('clicked()'), self.onColorClicked)
        return wcolor

    def addToggleButton(self, row, col, tooltip):
        """Make a toggle button."""

        toggle = self.setting.val[row][col]
        wtoggle = qt4.QCheckBox()
        self.layout.addWidget(wtoggle, row, col)
        wtoggle.setChecked(toggle)
        wtoggle.setToolTip(tooltip)
        self.connect(wtoggle, qt4.SIGNAL('toggled(bool)'), self.onToggled)
        return wtoggle

    def addCombo(self, row, col, tooltip, values, icons, texts):
        """Make an enumeration combo - choose from a set of icons."""
        
        val = self.setting.val[row][col]

        wcombo = qt4.QComboBox()
        self.layout.addWidget(wcombo, row, col)

        if texts is None:
            for icon in icons:
                wcombo.addItem(icon, "")
        else:
            for text, icon in izip(texts, icons):
                wcombo.addItem(icon, text)

        wcombo.setCurrentIndex(values.index(val))
        wcombo.setToolTip(tooltip)
        self.connect(wcombo, qt4.SIGNAL('activated(int)'),
                     self.onComboChanged)
        wcombo._vz_values = values
        return wcombo

    def _updateRowCol(self, row, col, val):
        """Update value on row and column."""
        rows = list(self.setting.val)
        items = list(rows[row])
        items[col] = val
        rows[row] = tuple(items)
        self.ignorechange = True
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, rows )
        
    def onToggled(self, on):
        """Checkbox toggled."""
        row, col = self.identifyPosn(self.sender())
        self._updateRowCol(row, col, on)

    def onComboChanged(self, val):
        """Update the setting if the combo changes."""
        sender = self.sender()
        row, col = self.identifyPosn(sender)
        self._updateRowCol(row, col, sender._vz_values[val])

    def onColorClicked(self):
        """Color button clicked for line."""
        sender = self.sender()
        row, col = self.identifyPosn(sender)

        rows = self.setting.val
        color = qt4.QColorDialog.getColor(
            utils.extendedColorToQColor(rows[row][col]),
            self,
            "Choose color",
            qt4.QColorDialog.ShowAlphaChannel )
        if color.isValid():
            # change setting
            # this is a bit irritating, as have to do lots of
            # tedious conversions
            color = utils.extendedColorFromQColor(color)
            self._updateRowCol(row, col, color)

            # change the color
            pix = qt4.QPixmap(self.pixsize, self.pixsize)
            pix.fill( utils.extendedColorToQColor(color) )
            sender.setIcon( qt4.QIcon(pix) )
            
class LineSet(ListSet):
    """A list of line styles.
    """

    def __init__(self, setting, parent):
        ListSet.__init__(self, ('solid', '1pt', 'black', False),
                         setting, parent)

    def populateRow(self, row, val):
        """Add the widgets for the row given."""

        # create line icons if not already created
        if LineStyle._icons is None:
            LineStyle._generateIcons()

        # make line style selector
        wlinestyle = self.addCombo(row, 0, 'Line style',
                                   LineStyle._lines,
                                   LineStyle._icons, None)
        
        # make line width edit box
        wwidth = qt4.QLineEdit()
        self.layout.addWidget(wwidth, row, 1)
        wwidth.setText(self.setting.val[row][1])
        wwidth.setToolTip('Line width')
        self.connect(wwidth, qt4.SIGNAL('editingFinished()'),
                     self.onWidthChanged)

        # make color selector button
        wcolor = self.addColorButton(row, 2, 'Line color')

        # make hide checkbox
        whide = self.addToggleButton(row, 3, 'Hide line')

        # return created controls
        return [wlinestyle, wwidth, wcolor, whide]

    def onWidthChanged(self):
        """Width has changed - validate."""

        sender = self.sender()
        row, col = self.identifyPosn(sender)

        text = unicode(sender.text())
        if setting.Distance.isDist(text):
            # valid distance
            styleClear(sender)
            self._updateRowCol(row, col, text)
        else:
            # invalid distance
            styleError(sender)

class FillSet(ListSet):
    """A list of fill settings."""

    def __init__(self, setting, parent):
        ListSet.__init__(self, ('solid', 'black', False),
                         setting, parent)

    def populateRow(self, row, val):
        """Add the widgets for the row given."""

        # construct fill icons if not already done
        if FillStyle._icons is None:
            FillStyle._generateIcons()
    
        # make fill style selector
        wfillstyle = self.addCombo(row, 0, 'Fill style',
                                   FillStyle._fills,
                                   FillStyle._icons,
                                   FillStyle._fills)
        wfillstyle.setMinimumWidth(self.pixsize)

        # make color selector button
        wcolor = self.addColorButton(row, 1, 'Fill color')

        # make hide checkbox
        whide = self.addToggleButton(row, 2, 'Hide fill')

        # return widgets
        return [wfillstyle, wcolor, whide]

class MultiSettingWidget(qt4.QWidget):
    """A widget for storing multiple values in a tuple,
    with + and - signs by each entry."""

    def __init__(self, setting, doc, parent):
        """Construct widget as combination of LineEdit and PushButton
        for browsing."""

        qt4.QWidget.__init__(self, parent)
        self.setting = setting
        self.document = doc

        self.grid = layout = qt4.QGridLayout()
        layout.setHorizontalSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.last = ()
        self.controls = []
        self.setting.setOnModified(self.onModified)
        
    def makeRow(self):
        """Make new row at end"""
        row = len(self.controls)
        cntrl = self.makeControl(row)
        cntrl.installEventFilter(self)
        addbutton = qt4.QPushButton('+')
        addbutton.setFixedWidth(24)
        addbutton.setFlat(True)
        addbutton.setToolTip('Add another item')
        subbutton = qt4.QPushButton('-')
        subbutton.setToolTip('Remove item')
        subbutton.setFixedWidth(24)
        subbutton.setFlat(True)

        self.controls.append((cntrl, addbutton, subbutton))

        self.grid.addWidget(cntrl, row, 0)
        self.grid.addWidget(addbutton, row, 1)
        self.grid.addWidget(subbutton, row, 2)

        self.connect(addbutton, qt4.SIGNAL('clicked()'),
                     lambda: self.addPressed(row))
        self.connect(subbutton, qt4.SIGNAL('clicked()'),
                     lambda: self.subPressed(row))

        if len(self.controls) == 2:
            # enable first subtraction button
            self.controls[0][2].setEnabled(True)
        elif len(self.controls) == 1:
            # or disable
            self.controls[0][2].setEnabled(False)

    def eventFilter(self, obj, event):
        """Capture loss of focus by controls."""
        if event.type() == qt4.QEvent.FocusOut:
            for row, c in enumerate(self.controls):
                if c[0] is obj:
                    self.dataChanged(row)
                    break
        return qt4.QWidget.eventFilter(self, obj, event)

    def deleteRow(self):
        """Remove last row"""
        for w in self.controls[-1]:
            self.grid.removeWidget(w)
            w.deleteLater()
        self.controls.pop(-1)

        # disable first subtraction button
        if len(self.controls) == 1:
            self.controls[0][2].setEnabled(False)

    def addPressed(self, row):
        """User adds a new row."""
        val = list(self.setting.val)
        val.insert(row+1, '')
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting,
                   tuple(val) )

    def subPressed(self, row):
        """User deletes a row."""
        val = list(self.setting.val)
        val.pop(row)
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting,
                   tuple(val) )

    def onModified(self, mod):
        """Called when the setting is changed remotely,
        or when control is opened"""

        s = self.setting

        if self.last == s.val:
            return
        self.last = s.val

        # update number of rows
        while len(self.setting.val) > len(self.controls):
            self.makeRow()
        while len(self.setting.val) < len(self.controls):
            self.deleteRow()

        # update values
        self.updateControls()

    def makeControl(self, row):
        """Override this to make an editing widget."""
        return None

    def updateControls():
        """Override this to update values in controls."""
        pass

    def readControl(self, cntrl):
        """Read value from control."""
        return None

    def dataChanged(self, row):
        """Update row of setitng with new data"""
        val = list(self.setting.val)
        val[row] = self.readControl( self.controls[row][0] )
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting,
                   tuple(val) )

class Datasets(MultiSettingWidget):
    """A control for editing a list of datasets."""

    def __init__(self, setting, doc, dimensions, datatype, parent):
        """Contruct set of comboboxes"""

        MultiSettingWidget.__init__(self, setting, doc, parent)
        self.dimensions = dimensions
        self.datatype = datatype

        self.lastdatasets = []
        # force updating to initialise
        self.onModified(True)

    def makeControl(self, row):
        """Make QComboBox edit widget."""
        combo = qt4.QComboBox()
        combo.setEditable(True)
        self.connect(combo.lineEdit(), qt4.SIGNAL('editingFinished()'), 
                     lambda: self.dataChanged(row))
        # if a different item is selected
        self.connect(combo, qt4.SIGNAL('activated(const QString&)'),
                     lambda x: self.dataChanged(row))
        utils.populateCombo(combo, self.getDatasets())
        return combo

    def readControl(self, control):
        """Get text for control."""
        return unicode( control.lineEdit().text() )

    def getDatasets(self):
        """Get applicable datasets (sorted)."""
        datasets = []
        for name, ds in self.document.data.iteritems():
            if (ds.dimensions == self.dimensions and
                ds.datatype == self.datatype):
                datasets.append(name)
        datasets.sort()
        return datasets

    def updateControls(self):
        """Set values of controls."""
        for cntrls, val in izip(self.controls, self.setting.val):
            cntrls[0].lineEdit().setText(val)

    def onModified(self, mod):
        """Called when the setting is changed remotely,
        or when control is opened"""

        MultiSettingWidget.onModified(self, mod)

        s = self.setting
        datasets = self.getDatasets()

        if self.lastdatasets == datasets:
            return
        self.lastdatasets = datasets

        # update list of datasets
        for cntrls in self.controls:
            utils.populateCombo(cntrls[0], datasets)

class Strings(MultiSettingWidget):
    """A list of strings."""

    def __init__(self, setting, doc, parent):
        """Construct widget as combination of LineEdit and PushButton
        for browsing."""

        MultiSettingWidget.__init__(self, setting, doc, parent)
        self.onModified(True)

    def makeControl(self, row):
        """Make edit widget."""
        lineedit = qt4.QLineEdit()
        self.connect(lineedit, qt4.SIGNAL('editingFinished()'), 
                     lambda: self.dataChanged(row))
        return lineedit

    def readControl(self, control):
        """Get text for control."""
        return unicode( control.text() )

    def updateControls(self):
        """Set values of controls."""
        for cntrls, val in izip(self.controls, self.setting.val):
            cntrls[0].setText(val)        

class Filename(qt4.QWidget):
    """A widget for selecting a filename with a browse button."""

    def __init__(self, setting, mode, parent):
        """Construct widget as combination of LineEdit and PushButton
        for browsing.

        mode is 'image' or 'file'
        """

        qt4.QWidget.__init__(self, parent)
        self.mode = mode
        self.setting = setting

        layout = qt4.QHBoxLayout()
        layout.setSpacing(0)
        layout.setMargin(0)
        self.setLayout(layout)

        # the actual edit control
        self.edit = qt4.QLineEdit()
        self.edit.setText( setting.toText() )
        layout.addWidget(self.edit)
        
        b = self.button = DotDotButton(checkable=False,
                                       tooltip="Browse for file")
        layout.addWidget(b)

        # connect up signals
        self.connect(self.edit, qt4.SIGNAL('editingFinished()'),
                     self.validateAndSet)
        self.connect(b, qt4.SIGNAL('clicked()'),
                     self.buttonClicked)

        # add completion if we have support (qt >= 4.3)
        if hasattr(qt4, 'QDirModel'):
            c = self.filenamecompleter = qt4.QCompleter(self)
            model = qt4.QDirModel(c)
            c.setModel(model)
            self.edit.setCompleter(c)

        # for read only filenames
        if setting.readonly:
            self.edit.setReadOnly(True)

        self.setting.setOnModified(self.onModified)

    def buttonClicked(self):
        """Button clicked - show file open dialog."""

        title = 'Choose file'
        filefilter = "All files (*)"
        if self.mode == 'image':
            title = 'Choose image'
            filefilter = ("Images (*.png *.jpg *.jpeg *.bmp *.svg *.tiff *.tif "
                          "*.gif *.xbm *.xpm);;" + filefilter)

        filename = qt4.QFileDialog.getOpenFileName(
            self, title, self.edit.text(), filefilter)

        if filename:
            val = unicode(filename)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

    def validateAndSet(self):
        """Check the text is a valid setting and update it."""

        text = unicode(self.edit.text())
        try:
            val = self.setting.fromText(text)
            styleClear(self.edit)
            self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, val )

        except setting.InvalidType:
            styleError(self.edit)

    def onModified(self, mod):
        """called when the setting is changed remotely"""
        self.edit.setText( self.setting.toText() )

class FontFamily(qt4.QFontComboBox):
    """List the font families, showing each font."""

    def __init__(self, setting, parent):
        """Create the combobox."""

        qt4.QFontComboBox.__init__(self, parent)
        self.setting = setting
        self.setFontFilters( qt4.QFontComboBox.ScalableFonts )
        
        # set initial value
        self.onModified(True)

        # stops combobox readjusting in size to fit contents
        self.setSizeAdjustPolicy(
            qt4.QComboBox.AdjustToMinimumContentsLengthWithIcon)

        self.setting.setOnModified(self.onModified)

        # if a different item is selected
        self.connect( self, qt4.SIGNAL('activated(const QString&)'),
                      self.slotActivated )

    def focusOutEvent(self, *args):
        """Allows us to check the contents of the widget."""
        qt4.QFontComboBox.focusOutEvent(self, *args)
        self.slotActivated('')

    def slotActivated(self, val):
        """Update setting if a different item is chosen."""
        newval = unicode(self.currentText())
        self.emit( qt4.SIGNAL('settingChanged'), self, self.setting, newval )

    def onModified(self, mod):
        """Make control reflect chosen setting."""
        self.setCurrentFont( qt4.QFont(self.setting.toText()) )

class ErrorStyle(Choice):
    """Choose different error bar styles."""
    
    _icons = None         # generated icons
    _errorstyles = None   # copied in by setting.py
    
    def __init__(self, setting, parent):
        if self._icons is None:
            self._generateIcons()

        Choice.__init__(self, setting, False,
                        self._errorstyles, parent,
                        icons=self._icons)

    def _generateIcons(cls):
        """Generate a list of pixmaps for drop down menu."""
        cls._icons = []
        for errstyle in cls._errorstyles:
            cls._icons.append( utils.getIcon('error_%s' % errstyle) )

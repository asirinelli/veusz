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
##############################################################################

"""Define a base dialog class cleans up self after being hidden."""

import os.path

import veusz.qtall as qt4
import veusz.utils as utils

class VeuszDialog(qt4.QDialog):
    """Base dialog class.
    - Loads self from ui file.
    - Deletes self on closing.
    - Emits dialogFinished when dialog is done
    """

    def __init__(self, mainwindow, uifile):
        """Initialise dialog given Veusz mainwindow and uifile for dialog."""

        qt4.QDialog.__init__(self, mainwindow)
        self.setAttribute(qt4.Qt.WA_DeleteOnClose)

        qt4.loadUi(os.path.join(utils.veuszDirectory, 'dialogs', uifile),
                   self)

        self.mainwindow = mainwindow

    def hideEvent(self, event):
        """Emits dialogFinished if hidden."""
        if not event.spontaneous():
            self.emit( qt4.SIGNAL('dialogFinished'), self )
        return qt4.QDialog.hideEvent(self, event)

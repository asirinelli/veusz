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
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###############################################################################

# $Id$

"""Module for holding collections of settings."""

import qt

class Settings(qt.QObject):
    """A class for holding collections of settings."""

    def __init__(self, name, descr = ''):
        """A new Settings with a name."""

        self.__dict__['setdict'] = {}
        self.name = name
        self.descr = descr
        self.setnames = []  # a list of names
        self.modified = False
        self.onmodified = [] # fns to call on modification

    def getName(self):
        """Get the name of the settings."""
        return self.name

    def getSettingsNames(self):
        """Get a list of names of settings."""
        return self.setnames

    def getList(self):
        """Get a list of setting or settings types."""
        return [self.setdict[n] for n in self.setnames]

    def getSettingList(self):
        """Get a list of setting types."""
        return [self.setdict[n] for n in self.setnames
                if not isinstance(self.setdict[n], Settings)]

    def getSettingsList(self):
        """Get a list of settings types."""
        return [self.setdict[n] for n in self.setnames
                if isinstance(self.setdict[n], Settings)]

    def isSetting(self, name):
        """Is the name a supported setting?"""
        return name in self.setdict

    def add(self, setting, posn = -1):
        """Add a new setting with the name, or a set of subsettings."""
        name = setting.getName()
        assert name not in self.setdict
        self.setdict[name] = setting
        if posn < 0:
            self.setnames.append(name)
        else:
            self.setnames.insert(posn, name)
        setting.setOnModified( self.setModified )

    def setModified(self, modified = True):
        """Set the modification flag."""
        self.modified = modified
        for i in self.onmodified:
            i(modified)
        
    def isModified(self):
        """Get the modification flag."""
        return self.modified

    def setOnModified(self, fn):
        """Set the function to be called on modification (passing True)."""
        self.onmodified.append(fn)
        
    def remove(self, name):
        """Remove name from the list of settings."""

        del self.setnames[ self.setnames.index( name ) ]
        del self.setdict[ name ]
        
    def __setattr__(self, name, val):
        """Allow us to do

        foo.setname = 42
        """

        d = self.__dict__['setdict']
        if name in d:
            d[name].set(val)
            self.setModified()
        else:
            self.__dict__[name] = val

    def __getattr__(self, name):
        """Allow us to do

        print foo.setname
        """

        d = self.__dict__['setdict']
        try:
            if name in d:
                return d[name].get()
            else:
                return self.__dict__[name]
        except KeyError:
            raise AttributeError, "'%s' is not a setting" % name

    def get(self, name = None):
        """Get the setting variable."""

        if name == None:
            return self
        else:
            return self.setdict[name]

    def getFromPath(self, path):
        """Get setting according to the path given as a list."""

        name = path[0]
        if name in self.setdict:
            val = self.setdict[name]
                
            if len(path) == 1:
                if isinstance(val, Settings):
                    raise ValueError, (
                        '"%s" is a list of settings, not a setting' % name)
                else:
                    return val
            else:
                if isinstance(val, Settings):
                    val.getFromPath(path[1:])
                else:
                    raise ValueError, '"%s" not a valid subsetting' % name
        else:
            raise ValueError, '"%s" is not a setting' % name


    def saveText(self, saveall, rootname = ''):
        """Return the text ro reload the settings.

        if saveall is true, save those which haven't been modified.
        rootname is the part to stick on the front of the settings
        """

        if rootname != '':
            rootname += '/'

        text = ''
        for name in self.setnames:
            val = self.setdict[name]

            if isinstance(val, Settings):
                # get text of sub preference
                text += val.saveText(saveall, rootname + self.name)
            else:
                if saveall or not val.isDefault():
                    text += "Set('%s%s', %s)\n" % ( rootname, name,
                                                    repr(val.get()) )

    def readDefaults(self):
        """Return default values from saved text."""

        # FIXME
        pass
    
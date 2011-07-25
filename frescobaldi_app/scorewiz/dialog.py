# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2011 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
The Score Wizard dialog.
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import app
import cursortools
import indent
import util


class ScoreWizardDialog(QDialog):
    
    pitchLanguageChanged = pyqtSignal(type(''))
    
    def __init__(self, mainwindow):
        super(ScoreWizardDialog, self).__init__(mainwindow)
        
        self._pitchLanguage = ''
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        self.tabs = QTabWidget()
        b = self.dialogButtons = QDialogButtonBox()
        b.setStandardButtons(QDialogButtonBox.Reset|QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        b.accepted.connect(self.accept)
        b.rejected.connect(self.reject)
        b.button(QDialogButtonBox.Reset).clicked.connect(self.reset)
        layout.addWidget(self.tabs)
        layout.addWidget(b)
        
        self.header = Header(self)
        self.tabs.addTab(self.header, '')
        self.parts = Parts(self)
        self.tabs.addTab(self.parts, '')
        self.settings = Settings(self)
        self.tabs.addTab(self.settings, '')
        self.preview = Preview(self)
        self.tabs.addTab(self.preview, '')
        
        self.tabs.setCurrentIndex(0)
        self.tabs.widget(0).widget() # activate it
        self.tabs.currentChanged.connect(self.slotCurrentChanged)
        util.saveDialogSize(self, "scorewiz/dialog/size")
        app.translateUI(self)
        self.accepted.connect(self.slotAccepted)
    
    def translateUI(self):
        self.setWindowTitle(app.caption(_("Score Setup Wizard")))
        for i in range(self.tabs.count()):
            self.tabs.setTabText(i, self.tabs.widget(i).title())
        self.dialogButtons.button(QDialogButtonBox.Reset).setText(_("Clear"))
        self.dialogButtons.button(QDialogButtonBox.Reset).setToolTip(_(
            "Clears the current page of the Score Wizard."))
    
    def slotCurrentChanged(self, i):
        """Lazy-loads the tab's page if shown for the first time."""
        self.tabs.widget(i).widget()
        
    def reset(self):
        self.tabs.currentWidget().widget().clear()

    def setPitchLanguage(self, language):
        if language != self._pitchLanguage:
            self._pitchLanguage = language
            self.pitchLanguageChanged.emit(language)
    
    def pitchLanguage(self):
        return self._pitchLanguage

    def slotAccepted(self):
        """Makes the score and puts it in the editor."""
        from . import build
        builder = build.Builder(self)
        cursor = self.parent().currentView().textCursor()
        cursortools.insertText(cursor, builder.text())
        indent.reIndent(cursor)


class Page(QWidget):
    """A Page in the tab widget.
    
    Basically this is just a QWidget that loads the desired page
    as soon as the widget() is called for the first time.
    
    """
    def __init__(self, dialog):
        super(Page, self).__init__(dialog)
        self._widget = None
        
    def title(self):
        """Should return a title."""

    def widget(self):
        if self._widget is None:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            self.setLayout(layout)
            w = self._widget = self.createWidget(self)
            layout.addWidget(w)
        return self._widget

    def createWidget(self, parent):
        """Should return the widget for this tab."""
        

class Header(Page):
    def title(self):
        return _("&Titles and Headers")

    def createWidget(self, parent):
        from . import header
        return header.HeaderWidget(parent)

        
class Parts(Page):
    def title(self):
        return _("&Parts")

    def createWidget(self, parent):
        from . import score
        return score.ScorePartsWidget(parent)


class Settings(Page):
    def title(self):
        return _("&Score settings")
    
    def createWidget(self, parent):
        from . import settings
        return settings.SettingsWidget(parent)


class Preview(Page):
    def title(self):
        return _("Pre&view")
    
    def createWidget(self, parent):
        from . import preview
        return preview.PreviewWidget(parent)


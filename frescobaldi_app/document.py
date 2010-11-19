# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008, 2009, 2010 by Wilbert Berendsen
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

from __future__ import unicode_literals

"""
A Frescobaldi (LilyPond) document.
"""

import os

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import app
import view


class Document(QTextDocument):
    
    urlChanged = pyqtSignal()
    closed = pyqtSignal()
    
    def __init__(self):
        super(Document, self).__init__()
        self.setDocumentLayout(QPlainTextDocumentLayout(self))
        
        self._materialized = False
        self._url = None
        self.setUrl(None)
        self.modificationChanged.connect(lambda: app.documentModificationChanged(self))
        
        
        app.documents.append(self)
        app.documentCreated(self)
        
        
    def close(self):
        app.documents.remove(self)
        self.closed.emit()
        app.documentClosed(self)

    def materialize(self):
        """Really load and instantiate ourselves.
        
        Makes lazy-loading lots of documents possible.
        
        """
        if self._materialized:
            return
        ### Implement
        app.documentMaterialized(self)
        self._materialized = True

    def createView(self):
        """Returns a new View on our document."""
        self.materialize()
        newview = view.View(self)
        return newview
    
    def url(self):
        return self._url
        
    def setUrl(self, url):
        """ Change the url for this document. """
        changed = self._url != url
        self._url = url or QUrl()
        # number for nameless documents
        if self._url.isEmpty():
            nums = [0]
            nums.extend(doc._num for doc in app.documents if doc is not self)
            self._num = max(nums) + 1
        else:
            self._num = 0
        if changed:
            self.urlChanged.emit()
            app.documentUrlChanged(self)
        
    def documentName(self):
        """ Returns a suitable name for this document. """
        if self._url.isEmpty():
            if self._num == 1:
                return _("Untitled")
            else:
                return _("Untitled ({num})").format(num=self._num)
        else:
            return os.path.basename(self._url.path())
            

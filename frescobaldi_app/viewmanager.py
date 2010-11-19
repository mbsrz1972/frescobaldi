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
ViewManager is a QSplitter containing sub-splitters to display multiple
ViewSpaces.
ViewSpace is a QStackedWidget with a statusbar, capable of displaying one of
multiple views.
"""

import contextlib

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import actioncollection
import app
import icons
import view


class ViewStatusBar(QWidget):
    def __init__(self, parent=None):
        super(ViewStatusBar, self).__init__(parent)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 1, 0, 1)
        layout.setSpacing(4)
        self.setLayout(layout)
        self.pos = QLabel()
        layout.addWidget(self.pos)
        
        self.state = QLabel()
        self.state.setFixedSize(16, 16)
        layout.addWidget(self.state)
        
        self.info = QLabel()
        layout.addWidget(self.info, 1)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(14)
        layout.addWidget(self.progress, 1)
        
        self.installEventFilter(self)
        self.translateUI()
        app.languageChanged.connect(self.translateUI)
        
    def translateUI(self):
        text = _("Line: {line}, Col: {column}").format(line=9999, column=99)
        self.pos.setMinimumWidth(self.pos.fontMetrics().width(text))
    
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonPress:
            if ev.button() == Qt.RightButton:
                self.showContextMenu(ev.globalPos())
            else:
                self.parent().activeView().setFocus()
            return True
        return False

    def showContextMenu(self, pos):
        menu = QMenu(self)
        menu.aboutToHide.connect(menu.deleteLater)
        viewspace = self.parent()
        manager = viewspace.manager
        
        a = QAction(icons.get('view-split-top-bottom'), _("Split &Horizontally"), menu)
        menu.addAction(a)
        a.triggered.connect(lambda: manager.splitViewSpace(viewspace, Qt.Vertical))
        a = QAction(icons.get('view-split-left-right'), _("Split &Vertically"), menu)
        menu.addAction(a)
        a.triggered.connect(lambda: manager.splitViewSpace(viewspace, Qt.Horizontal))
        menu.addSeparator()
        a = QAction(icons.get('view-close'), _("&Close View"), menu)
        a.triggered.connect(lambda: manager.closeViewSpace(viewspace))
        a.setEnabled(manager.canCloseViewSpace())
        menu.addAction(a)
        
        menu.exec_(pos)


class ViewSpace(QWidget):
    def __init__(self, manager, parent=None):
        super(ViewSpace, self).__init__(parent)
        self.manager = manager
        self._activeView = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)
        self.status = ViewStatusBar(self)
        self.status.setEnabled(False)
        layout.addWidget(self.status)
        app.languageChanged.connect(self.updateStatusBar)
        
    def activeView(self):
        return self._activeView

    def addView(self, view):
        self.stack.addWidget(view)
        
    def removeView(self, view):
        if view is self._activeView:
            self.connectView(view, False)
            self._activeView = None
        self.stack.removeWidget(view)
        
    def setActiveView(self, view):
        cur = self._activeView
        if view is cur:
            return
        if cur:
            cur.cursorPositionChanged.disconnect(self.updateStatusBar)
            cur.modificationChanged.disconnect(self.updateStatusBar)
            cur.focusIn.disconnect(self.setActiveViewSpace)
            cur.document().urlChanged.disconnect(self.updateStatusBar)
        view.cursorPositionChanged.connect(self.updateStatusBar)
        view.modificationChanged.connect(self.updateStatusBar)
        view.focusIn.connect(self.setActiveViewSpace)
        view.document().urlChanged.connect(self.updateStatusBar)
        self._activeView = view
        self.stack.setCurrentWidget(view)
        self.updateStatusBar()
        
    def setActiveViewSpace(self, view):
        self.manager.setActiveViewSpace(self)
        
    def updateStatusBar(self):
        view = self.activeView()
        if view:
            cur = view.textCursor()
            self.status.pos.setText(_("Line: {line}, Col: {column}").format(
                line = cur.blockNumber() + 1,
                column = cur.columnNumber()))
            if view.document().isModified():
                pixmap = icons.get('document-save').pixmap(16)
            else:
                pixmap = QPixmap()
            self.status.state.setPixmap(pixmap)
            self.status.info.setText(view.document().documentName())
            
    def views(self):
        return map(self.stack.widget, range(self.stack.count()))
        
    def showDocument(self, doc):
        for view in self.views():
            if view.document() is doc:
                break
        else:
            view = doc.createView()
            self.addView(view)
        self.setActiveView(view)




class ViewManager(QSplitter):
    
    viewChanged = pyqtSignal(view.View)
    
    def __init__(self, parent=None):
        super(ViewManager, self).__init__(parent)
        self._viewSpaces = []
        self._blockFocusChanges = False
        
        viewspace = ViewSpace(self)
        viewspace.status.setEnabled(True)
        self.addWidget(viewspace)
        self._viewSpaces.append(viewspace)
        
        self.createActions()
        self.translateUI()
        app.languageChanged.connect(self.translateUI)
    
    def createActions(self):
        self.actionCollection = ac = ViewActions(self)
        # connections
        ac.window_close_view.setEnabled(False)
        ac.window_split_horizontal.triggered.connect(
            lambda: self.splitViewSpace(self.activeViewSpace(), Qt.Vertical))
        ac.window_split_vertical.triggered.connect(
            lambda: self.splitViewSpace(self.activeViewSpace(), Qt.Horizontal))
        ac.window_close_view.triggered.connect(
            lambda: self.closeViewSpace(self.activeViewSpace()))
        ac.window_next_view.triggered.connect(lambda: self.focusNextChild())
        ac.window_previous_view.triggered.connect(lambda: self.focusPreviousChild())
    
    def translateUI(self):
        self.actionCollection.translateUI()
    
    def activeViewSpace(self):
        return self._viewSpaces[-1]
        
    def activeView(self):
        return self.activeViewSpace().activeView()
    
    def setActiveViewSpace(self, space):
        if not self._blockFocusChanges:
            prev = self._viewSpaces[-1]
            if space is prev:
                return
            self._viewSpaces.remove(space)
            self._viewSpaces.append(space)
            
            prev.status.setEnabled(False)
            space.status.setEnabled(True)
            newdoc = space.activeView().document()
            space.activeView().setFocus()
            self.viewChanged.emit(space.activeView())

    @contextlib.contextmanager
    def focusChangesBlocked(self):
        self._blockFocusChanges = True
        yield
        self.activeView().setFocus()
        self._blockFocusChanges = False
        
    def splitViewSpace(self, viewspace, orientation):
        """Split the given view.
        
        If orientation == Qt.Horizontal, adds a new view to the right.
        If orientation == Qt.Vertical, adds a new view to the bottom.
        
        """
        active = viewspace is self.activeViewSpace()
        splitter = viewspace.parentWidget()
        newspace = ViewSpace(self)
        
        if splitter.count() == 1:
            splitter.setOrientation(orientation)
            size = splitter.sizes()[0]
            splitter.addWidget(newspace)
            splitter.setSizes([size / 2, size / 2])
        elif splitter.orientation() == orientation:
            index = splitter.indexOf(viewspace)
            splitter.insertWidget(index + 1, newspace)
        else:
            with self.focusChangesBlocked():
                index = splitter.indexOf(viewspace)
                newsplitter = QSplitter()
                newsplitter.setOrientation(orientation)
                sizes = splitter.sizes()
                splitter.insertWidget(index, newsplitter)
                newsplitter.addWidget(viewspace)
                splitter.setSizes(sizes)
                size = newsplitter.sizes()[0]
                newsplitter.addWidget(newspace)
                newsplitter.setSizes([size / 2, size / 2])
        self._viewSpaces.insert(0, newspace)
        newview = viewspace.activeView().document().createView()
        newspace.addView(newview)
        newspace.setActiveView(newview)
        if active:
            self.setActiveViewSpace(newspace)
        self.actionCollection.window_close_view.setEnabled(self.canCloseViewSpace())
        
    def closeViewSpace(self, viewspace):
        """Closes the given view."""
        active = viewspace is self.activeViewSpace()
        if active:
            self.setActiveViewSpace(self._viewSpaces[-2])
        with self.focusChangesBlocked():
            splitter = viewspace.parentWidget()
            if splitter.count() > 2:
                viewspace.setParent(None)
                viewspace.deleteLater()
            elif splitter is self:
                if self.count() < 2:
                    return
                # we contain only one other widget.
                # if that is a QSplitter, add all its children to ourselves
                # and copy the sizes and orientation.
                other = self.widget(1 - self.indexOf(viewspace))
                viewspace.setParent(None)
                viewspace.deleteLater()
                if isinstance(other, QSplitter):
                    sizes = other.sizes()
                    self.setOrientation(other.orientation())
                    while other.count():
                        self.insertWidget(0, other.widget(other.count()-1))
                    other.setParent(None)
                    other.deleteLater()
                    self.setSizes(sizes)
            else:
                # this splitter contains only one other widget.
                # if that is a ViewSpace, just add it to the parent splitter.
                # if it is a splitter, add all widgets to the parent splitter.
                other = splitter.widget(1 - splitter.indexOf(viewspace))
                parent = splitter.parentWidget()
                sizes = parent.sizes()
                index = parent.indexOf(splitter)
                
                if isinstance(other, ViewSpace):
                    parent.insertWidget(index, other)
                else:
                    #QSplitter
                    sizes[index:index+1] = other.sizes()
                    while other.count():
                        parent.insertWidget(index, other.widget(other.count()-1))
                viewspace.setParent(None)
                splitter.setParent(None)
                viewspace.deleteLater()
                splitter.deleteLater()
                parent.setSizes(sizes)
            self._viewSpaces.remove(viewspace)
        self.actionCollection.window_close_view.setEnabled(self.canCloseViewSpace())
        
    def canCloseViewSpace(self):
        return bool(self.count() > 1)
        
    def showDocument(self, doc, findOpenView=False):
        """Shows the document in the currently active view.
        
        if findOpenView is True, tries to find a viewspace
        that has the document in view, and then switches to that viewspace.
        
        """
        view = self.activeView()
        if view and view.document() is doc:
            return
        if findOpenView:
            for viewspace in self._viewSpaces[::-1]:
                view = viewspace.activeView()
                if view.document() is doc:
                    view.setFocus()
                    return
        self.activeViewSpace().showDocument(doc)
        self.viewChanged.emit(self.activeView())
                    
                    


class ViewActions(actioncollection.ActionCollection):
    def __init__(self, parent):
        self.window_split_horizontal = QAction(parent)
        self.window_split_vertical = QAction(parent)
        self.window_close_view = QAction(parent)
        self.window_next_view = QAction(parent)
        self.window_previous_view = QAction(parent)
        
        # icons
        self.window_split_horizontal.setIcon(icons.get('view-split-top-bottom'))
        self.window_split_vertical.setIcon(icons.get('view-split-left-right'))
        self.window_close_view.setIcon(icons.get('view-close'))
        self.window_next_view.setIcon(icons.get('go-next-view'))
        self.window_previous_view.setIcon(icons.get('go-previous-view'))
        
        # shortcuts
        self.window_next_view.setShortcuts(QKeySequence.NextChild)
        self.window_previous_view.setShortcuts(QKeySequence.PreviousChild)

    def translateUI(self):
        self.window_split_horizontal.setText(_("Split &Horizontally"))
        self.window_split_vertical.setText(_("Split &Vertically"))
        self.window_close_view.setText(_("&Close Current View"))
        self.window_next_view.setText(_("&Next View"))
        self.window_previous_view.setText(_("&Previous View"))
    
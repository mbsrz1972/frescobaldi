# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2008 - 2012 by Wilbert Berendsen
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
The PDF preview panel context menu.
"""

from __future__ import unicode_literals

from PyQt4.QtCore import *
from PyQt4.QtGui import *


def show(position, panel, link, cursor):
    """Shows a context menu.
    
    position: The global position to pop up
    panel: The music view panel, giving access to mainwindow and view widget
    link: a popplerqt4 LinkBrowse instance or None
    cursor: a QTextCursor instance or None
    
    """
    m = QMenu(panel)
    
    # selection? -> Copy
    if panel.widget().view.surface().hasSelection():
        m.addAction(panel.actionCollection.music_copy_image)
    
    
    # no actions yet? insert Fit Width
    if not m.actions():
        a = panel.actionCollection.music_fit_width
        if not a.isChecked():
            m.addAction(a)
    
    # show it!
    if m.actions():
        m.exec_(position)
        m.deleteLater()




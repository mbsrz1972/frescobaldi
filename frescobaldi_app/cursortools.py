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
Function manipulating QTextCursors and their selections.
"""

from __future__ import unicode_literals

import contextlib

from PyQt4.QtGui import QTextCursor


def block(cursor):
    """Returns the cursor's block.
    
    If the cursor has a selection, returns the block the selection starts in
    (regardless of the cursor's position()).
    
    """
    if cursor.hasSelection():
        return cursor.document().findBlock(cursor.selectionStart())
    return cursor.block()

    
def blocks(cursor):
    """Yields the block(s) containing the cursor or selection."""
    d = cursor.document()
    block = d.findBlock(cursor.selectionStart())
    end = d.findBlock(cursor.selectionEnd())
    while True:
        yield block
        if block == end:
            break
        block = block.next()
     

def contains(c1, c2):
    """Returns True if cursor2's selection falls inside cursor1's."""
    return (c1.selectionStart() <= c2.selectionStart()
            and c1.selectionEnd() >= c2.selectionEnd())


def allBlocks(document):
    """Yields all blocks of the document."""
    block = document.firstBlock()
    while block.isValid():
        yield block
        block = block.next()


def partition(cursor):
    """Returns a three-tuple of strings (before, selection, after).
    
    'before' is the text before the cursor's position or selection start,
    'after' is the text after the cursor's position or selection end,
    'selection' is the selected text.
    
    before and after never contain a newline.
    
    """
    start = cursor.document().findBlock(cursor.selectionStart())
    end = cursor.document().findBlock(cursor.selectionEnd())
    before = start.text()[:cursor.selectionStart() - start.position()]
    selection = cursor.selection().toPlainText()
    after = end.text()[cursor.selectionEnd() - end.position():]
    return before, selection, after


@contextlib.contextmanager
def editBlock(cursor, joinPrevious = False):
    """Returns a context manager to perform operations on cursor as a single undo-item."""
    cursor.joinPreviousEditBlock() if joinPrevious else cursor.beginEditBlock()
    try:
        yield
    finally:
        cursor.endEditBlock()


@contextlib.contextmanager
def keepSelection(cursor, edit=None):
    """Performs operations inside the selection and restore the selection afterwards.
    
    If edit is given, call setTextCursor(cursor) on the Q(Plain)TextEdit afterwards.
    
    """
    start, end, pos = cursor.selectionStart(), cursor.selectionEnd(), cursor.position()
    cur2 = QTextCursor(cursor)
    cur2.setPosition(end)
    
    try:
        yield
    finally:
        if pos == start:
            cursor.setPosition(cur2.position())
            cursor.setPosition(start, QTextCursor.KeepAnchor)
        else:
            cursor.setPosition(start)
            cursor.setPosition(cur2.position(), QTextCursor.KeepAnchor)
        if edit:
            edit.setTextCursor(cursor)


def strip(cursor, chars=None):
    """Adjusts the selection of the cursor just like Python's strip().
    
    If there is no selection or the selection would vanish completely,
    nothing is done.
    
    """
    if not cursor.hasSelection():
        return
    text = cursor.selection().toPlainText()
    if not text.strip(chars):
        return
    l = len(text) - len(text.lstrip(chars))
    r = len(text) - len(text.rstrip(chars))
    s = cursor.selectionStart() + l
    e = cursor.selectionEnd() - r
    if cursor.position() < cursor.anchor():
        s, e = e, s
    cursor.setPosition(s)
    cursor.setPosition(e, QTextCursor.KeepAnchor)


def insertText(cursor, text):
    """Inserts text and then selects all inserted text in the cursor."""
    pos = cursor.selectionStart()
    cursor.insertText(text)
    new = cursor.position()
    cursor.setPosition(pos)
    cursor.setPosition(new, QTextCursor.KeepAnchor)


def isBlankBefore(cursor):
    """Returns True if there's no text on the current line before the cursor."""
    if cursor.hasSelection():
        return False
    if cursor.atBlockStart():
        return True
    c = QTextCursor(cursor)
    c.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
    return c.selection().toPlainText().isspace()


def isBlankAfter(cursor):
    """Returns True if there's no text on the current line after the cursor."""
    if cursor.hasSelection():
        return False
    if cursor.atBlockEnd():
        return True
    c = QTextCursor(cursor)
    c.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
    return c.selection().toPlainText().isspace()


def isBlankLine(cursor):
    """Returns True if the cursor is on an empty or blank line."""
    text = cursor.block().text()
    return not text or text.isspace()


def stripIndent(cursor):
    """Moves the cursor in its block to the first non-space character."""
    text = cursor.block().text()
    pos = len(text) - len(text.lstrip())
    cursor.setPosition(cursor.block().position() + pos)


class Editor(object):
    """A context manager that stores edits until it is exited.
    
    Usage:
    
    with Editor() as e:
        e.insertText(cursor, "text")
        e.removeSelectedText(cursor)
        # ... etc
    # when the code block ends, the edits will be done.
    
    All cursors should belong to the same text document.
    The edits will not be applied if the context is exited with an exception.
    
    """
    def __init__(self):
        self.edits = []
    
    def __enter__(self):
        return self
    
    def insertText(self, cursor, text):
        """Stores an insertText operation."""
        self.edits.append((cursor, text))
    
    def removeSelectedText(self, cursor):
        """Stores a removeSelectedText operation."""
        self.edits.append((cursor, ""))
    
    def apply(self):
        """Applies and clears the stored edits."""
        if self.edits:
            # don't use all the cursors directly, but copy and sort the ranges
            # otherwise inserts would move the cursor for adjacent edits.
            # We could also just start with the first, but that would require
            # all cursors to update their position during the process, which
            # notably slows down large edits (as there are already many cursors
            # used by the point and click feature).
            # We could also use QTextCursor.keepPositionOnInsert but that is
            # only available in the newest PyQt4 versions.
            edits = [(cursor.selectionStart(), cursor.selectionEnd(), text)
                      for cursor, text in self.edits]
            edits.sort(key=lambda e: e[0]) # dont reorder edits at same startpos
            edits.reverse()
            cursor = self.edits[0][0]
            del self.edits[:]
            with editBlock(cursor):
                for start, end, text in edits:
                    cursor.setPosition(end)
                    cursor.setPosition(start, QTextCursor.KeepAnchor)
                    cursor.insertText(text)
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.apply()



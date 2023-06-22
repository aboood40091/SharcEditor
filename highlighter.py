#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtGui
Qt = QtCore.Qt


keywordPatterns = [
    r'\bchar\b', r'\bclass\b', r'\bconst\b',
    r'\bdouble\b', r'\benum\b', r'\bexplicit\b',
    r'\bfriend\b', r'\binline\b', r'\bint\b',
    r'\blong\b', r'\bnamespace\b', r'\boperator\b',
    r'\bprivate\b', r'\bprotected\b', r'\bpublic\b',
    r'\bshort\b', r'\bsignals\b', r'\bsigned\b',
    r'\bslots\b', r'\bstatic\b', r'\bstruct\b',
    r'\btemplate\b', r'\btypedef\b', r'\btypename\b',
    r'\bunion\b', r'\bunsigned\b', r'\bvirtual\b',
    r'\bvoid\b', r'\bvolatile\b', r'\bbool\b',
    r'\bfloat\b', r'\blong\b', r'\bivec4\b',
    r'\bvec2\b', r'\bvec3\b', r'\bvec4\b',
    r'\buniform\b', r'\bin\b', r'\bout\b'
]


class Highlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.keywordFormat = QtGui.QTextCharFormat()
        self.keywordFormat.setForeground(Qt.darkBlue)
        self.keywordFormat.setFontWeight(QtGui.QFont.Bold)

        self.highlightingRules = []
        for pattern in keywordPatterns:
            self.highlightingRules.append((QtCore.QRegularExpression(pattern), self.keywordFormat))

        self.classFormat = QtGui.QTextCharFormat()
        self.classFormat.setFontWeight(QtGui.QFont.Bold)
        self.classFormat.setForeground(Qt.darkMagenta)
        self.highlightingRules.append((QtCore.QRegularExpression(r'\bQ[A-Za-z]+\b'), self.classFormat))

        self.quotationFormat = QtGui.QTextCharFormat()
        self.quotationFormat.setForeground(Qt.darkGreen)
        self.highlightingRules.append((QtCore.QRegularExpression('".*"'), self.quotationFormat))

        self.functionFormat = QtGui.QTextCharFormat()
        self.functionFormat.setFontItalic(True)
        self.functionFormat.setForeground(Qt.blue)
        self.highlightingRules.append((QtCore.QRegularExpression(r'\b[A-Za-z0-9_]+(?=\()'), self.functionFormat))

        self.singleLineCommentFormat = QtGui.QTextCharFormat()
        self.singleLineCommentFormat.setForeground(Qt.red)
        self.highlightingRules.append((QtCore.QRegularExpression('//[^\n]*'), self.singleLineCommentFormat))

        self.multiLineCommentFormat = QtGui.QTextCharFormat()
        self.multiLineCommentFormat.setForeground(Qt.red)

        self.commentStartExpression = QtCore.QRegExp(r'/\*')
        self.commentEndExpression = QtCore.QRegularExpression(r'\*/')

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            matchIterator = pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = self.commentStartExpression.indexIn(text)

        while startIndex >= 0:
            match = self.commentEndExpression.match(text, startIndex)
            endIndex = match.capturedStart()
            commentLength = 0
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex

            else:
                commentLength = endIndex - startIndex + match.capturedLength()

            self.setFormat(startIndex, commentLength, self.multiLineCommentFormat)
            startIndex = self.commentStartExpression.indexIn(text, startIndex + commentLength)

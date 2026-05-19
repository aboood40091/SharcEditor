#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os.path
from typing import List, Sequence, cast

from PyQt5 import QtGui, QtWidgets
import sip

from highlighter import Highlighter
import sharc


class Sharc:
    header: sharc.Header
    progList: sharc.ResList[sharc.ShaderProgram]
    codeList: sharc.ResList[sharc.ShaderCode]
    programCount: int

    def __init__(self) -> None:
        self.header = sharc.Header()
        self.progList = sharc.ResList()
        self.codeList = sharc.ResList()

    def set(
        self,
        header: sharc.Header,
        progList: sharc.ResList[sharc.ShaderProgram],
        codeList: sharc.ResList[sharc.ShaderCode],
    ) -> None:
        self.header = header
        self.progList = progList
        self.codeList = codeList
        self.programCount = len(progList)


class TableWidget(QtWidgets.QTableWidget):
    def __init__(self, headers: Sequence[str]) -> None:
        super().__init__(1, len(headers))

        self.cellChanged.connect(self.handleCellChange)
        self.setSortingEnabled(False)

        for i, header in enumerate(headers):
            self.setHorizontalHeaderItem(i, QtWidgets.QTableWidgetItem())
            self.horizontalHeaderItem(i).setText(header)

    def handleCellChange(self, r: int, c: int) -> None:
        rowCount = self.rowCount()

        if r == rowCount - 1 and self.item(r, c).text():
            self.setRowCount(rowCount + 1)

        elif not any((self.item(r, c).text() if self.item(r, c) else False) for c in range(self.columnCount())):
            self.removeRow(r)


class ShaderMacro(TableWidget):
    def __init__(self) -> None:
        super().__init__(("Name", "Value"))


class ShaderSymbol(TableWidget):
    def __init__(self) -> None:
        super().__init__(("Name", "ID", "Default Value", "Offset"))


class TabWidget(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._tabBar: QtWidgets.QTabBar = QtWidgets.QTabBar()
        self._tabBar.currentChanged.connect(self.currentTabChanged)
        sp = self._tabBar.sizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        self._tabBar.setSizePolicy(sp)

        self._stackedWidget: QtWidgets.QStackedWidget = QtWidgets.QStackedWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._tabBar)
        layout.addWidget(self._stackedWidget)

    def addTab(self, widget: QtWidgets.QWidget, name: str) -> None:
        self._tabBar.addTab(name)
        self._stackedWidget.addWidget(widget)

    def currentTabChanged(self, index: int) -> None:
        if index == -1:
            return

        self._stackedWidget.setCurrentIndex(index)


class ShaderSource(QtWidgets.QTextEdit):
    def __init__(self) -> None:
        super().__init__()

        font = QtGui.QFont("Inconsolata", 10)
        font.setFixedPitch(True)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)

        self.setFont(font)
        self.setReadOnly(True)

        self._highlighter = Highlighter(self.document())


class ShaderSourceTab(QtWidgets.QWidget):
    def __init__(self, parent: MainWindow, type: int) -> None:
        super().__init__()

        self._parent: MainWindow = parent
        self._type: int = type

        fileLabel = QtWidgets.QLabel()
        fileLabel.setText("File:")

        self._fileComboBox: QtWidgets.QComboBox = QtWidgets.QComboBox()
        self._fileComboBox.currentIndexChanged.connect(self.currentChanged)

        fileLayout = QtWidgets.QHBoxLayout()
        fileLayout.addWidget(fileLabel)
        fileLayout.addWidget(self._fileComboBox)

        self._editor: ShaderSource = ShaderSource()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(fileLayout)
        layout.addWidget(self._editor)

    def addItems(self, texts: List[str]) -> None:
        self._fileComboBox.addItem("None")
        self._fileComboBox.addItems(texts)

    def setCurrentIndex(self, index: int) -> None:
        self._fileComboBox.setCurrentIndex(index + 1)

    def currentIndex(self) -> int:
        return self._fileComboBox.currentIndex() - 1

    def clear(self) -> None:
        self._fileComboBox.clear()

    def currentChanged(self, index: int) -> None:
        if index == -1:
            return

        if index == 0:
            self._editor.clear()

        else:
            self._editor.setPlainText(self._parent.sharc.codeList[index - 1].code)


class ShaderProgram(TabWidget):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__()

        self.vertexMacros: ShaderMacro = ShaderMacro()
        self.fragmentMacros: ShaderMacro = ShaderMacro()
        self.uniformVars: ShaderSymbol = ShaderSymbol()
        self.uniformBlocks: ShaderSymbol = ShaderSymbol()
        self.samplerVars: ShaderSymbol = ShaderSymbol()
        self.vertexAttribs: ShaderSymbol = ShaderSymbol()

        self.vertexCode: ShaderSourceTab = ShaderSourceTab(parent, 0)
        self.fragmentCode: ShaderSourceTab = ShaderSourceTab(parent, 1)

        self.uniformBlocks.setColumnHidden(3, True)
        self.samplerVars.setColumnHidden(2, True)
        self.samplerVars.setColumnHidden(3, True)
        self.vertexAttribs.setColumnHidden(2, True)
        self.vertexAttribs.setColumnHidden(3, True)

        vertexTab = TabWidget()
        vertexTab.addTab(self.vertexMacros, "Macros")
        vertexTab.addTab(self.vertexCode, "Source code")

        fragmentTab = TabWidget()
        fragmentTab.addTab(self.fragmentMacros, "Macros")
        fragmentTab.addTab(self.fragmentCode, "Source code")

        uniformsTab = TabWidget()
        uniformsTab.addTab(self.uniformBlocks, "Blocks")
        uniformsTab.addTab(self.uniformVars, "Variables")

        self.addTab(vertexTab, "Vertex Shader")
        self.addTab(fragmentTab, "Fragment Shader")
        self.addTab(uniformsTab, "Uniforms")
        self.addTab(self.samplerVars, "Sampler Variables")
        self.addTab(self.vertexAttribs, "Vertex Attributes")


class MainWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("SharcEditor v0.3 - (C) 2019-2026 AboodXD")

        self.sharc: Sharc = Sharc()
        self.codeFiles: List[str] = []

        fileLabel = QtWidgets.QLabel()
        fileLabel.setText("File:")

        self.fileLineEdit: QtWidgets.QLineEdit = QtWidgets.QLineEdit()
        self.fileLineEdit.setEnabled(False)

        openButton = QtWidgets.QPushButton("Open")
        openButton.clicked.connect(self.openFile)

        saveButton = QtWidgets.QPushButton("Save")
        saveButton.clicked.connect(self.saveFile)

        saveAsButton = QtWidgets.QPushButton("Save As")
        saveAsButton.clicked.connect(self.saveFileAs)

        fileLayout = QtWidgets.QHBoxLayout()
        fileLayout.addWidget(fileLabel)
        fileLayout.addWidget(self.fileLineEdit)
        fileLayout.addWidget(openButton)
        fileLayout.addWidget(saveButton)
        fileLayout.addWidget(saveAsButton)

        self.treeWidget: QtWidgets.QTreeWidget = QtWidgets.QTreeWidget()
        QtWidgets.QTreeWidgetItem(self.treeWidget)
        QtWidgets.QTreeWidgetItem(self.treeWidget)
        self.treeWidget.headerItem().setText(0, "Shader Definition")
        self.treeWidget.topLevelItem(0).setText(0, "Shader Program")
        self.treeWidget.topLevelItem(1).setText(0, "Shader Source")
        self.treeWidget.setSortingEnabled(False)
        self.treeWidget.currentItemChanged.connect(self.currentChanged)

        addButton = QtWidgets.QPushButton("Add")
        addButton.clicked.connect(self.add)

        removeButton = QtWidgets.QPushButton("Remove")
        removeButton.clicked.connect(self.remove)

        buttonsLayout = QtWidgets.QHBoxLayout()
        buttonsLayout.addWidget(addButton)
        buttonsLayout.addWidget(removeButton)

        treeLayout = QtWidgets.QVBoxLayout()
        treeLayout.addWidget(self.treeWidget)
        treeLayout.addLayout(buttonsLayout)

        self.widgets: QtWidgets.QStackedWidget = QtWidgets.QStackedWidget()

        viewLayout = QtWidgets.QHBoxLayout()
        viewLayout.addLayout(treeLayout)
        viewLayout.addWidget(self.widgets)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(fileLayout)
        layout.addLayout(viewLayout)

    def getProgramCount(self) -> int:
        return self.sharc.programCount

    def closeFile(self) -> None:
        for i in range(self.widgets.count() - 1, -1, -1):
            j = int(i >= self.getProgramCount())
            sip.delete(self.treeWidget.topLevelItem(j).child(i - j * self.getProgramCount()))
            sip.delete(self.widgets.widget(i))

        self.treeWidget.topLevelItem(0).setSelected(False)
        self.treeWidget.topLevelItem(1).setSelected(False)

        self.sharc = Sharc()
        self.codeFiles = []

    def openFile(self) -> None:
        file = QtWidgets.QFileDialog.getOpenFileName(None, "Open File", "", "AGL Resource Shader Archive (*.sharc)")[0]
        if not (file and os.path.isfile(file)):
            return

        self.closeFile()
        self.fileLineEdit.setText(file)

        with open(file, 'rb') as inf:
            inb = inf.read()

        self.sharc.set(*sharc.load(inb))

        self.codeFiles = []
        for code in self.sharc.codeList:
            self.codeFiles.append(code.name)

        for program in self.sharc.progList:
            programWidget = ShaderProgram(self)
            programWidget.vertexCode.addItems(self.codeFiles)
            programWidget.fragmentCode.addItems(self.codeFiles)
            programWidget.vertexCode.setCurrentIndex(program.vtxShIdx)
            programWidget.fragmentCode.setCurrentIndex(program.frgShIdx)

            for i, macro in enumerate(program.vertexMacros):
                nameCell = QtWidgets.QTableWidgetItem()
                valueCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(macro.name)
                valueCell.setText(macro.value)

                programWidget.vertexMacros.setItem(i, 0, nameCell)
                programWidget.vertexMacros.setItem(i, 1, valueCell)
                programWidget.vertexMacros.setRowCount(i + 2)

            for i, macro in enumerate(program.fragmentMacros):
                nameCell = QtWidgets.QTableWidgetItem()
                valueCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(macro.name)
                valueCell.setText(macro.value)

                programWidget.fragmentMacros.setItem(i, 0, nameCell)
                programWidget.fragmentMacros.setItem(i, 1, valueCell)
                programWidget.fragmentMacros.setRowCount(i + 2)

            for i, sym in enumerate(program.uniformVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                idCell = QtWidgets.QTableWidgetItem()
                defaultValCell = QtWidgets.QTableWidgetItem()
                offsetCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.name)
                idCell.setText(sym.variable.name)
                defaultValCell.setText(str(sym.variable.default))
                offsetCell.setText(str(sym.variable.offset))

                programWidget.uniformVars.setItem(i, 0, nameCell)
                programWidget.uniformVars.setItem(i, 1, idCell)
                programWidget.uniformVars.setItem(i, 2, defaultValCell)
                programWidget.uniformVars.setItem(i, 3, offsetCell)
                programWidget.uniformVars.setRowCount(i + 2)

            for i, sym in enumerate(program.uniformBlocks):
                nameCell = QtWidgets.QTableWidgetItem()
                idCell = QtWidgets.QTableWidgetItem()
                defaultValCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.name)
                idCell.setText(sym.variable.name)
                defaultValCell.setText(str(sym.variable.default))

                programWidget.uniformBlocks.setItem(i, 0, nameCell)
                programWidget.uniformBlocks.setItem(i, 1, idCell)
                programWidget.uniformBlocks.setItem(i, 2, defaultValCell)
                programWidget.uniformBlocks.setRowCount(i + 2)

            for i, sym in enumerate(program.samplerVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                idCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.name)
                idCell.setText(sym.variable.name)

                programWidget.samplerVars.setItem(i, 0, nameCell)
                programWidget.samplerVars.setItem(i, 1, idCell)
                programWidget.samplerVars.setRowCount(i + 2)

            for i, sym in enumerate(program.attribVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                idCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.name)
                idCell.setText(sym.variable.name)

                programWidget.vertexAttribs.setItem(i, 0, nameCell)
                programWidget.vertexAttribs.setItem(i, 1, idCell)
                programWidget.vertexAttribs.setRowCount(i + 2)

            programItem = QtWidgets.QTreeWidgetItem(1)
            programItem.setText(0, program.name)
            self.treeWidget.topLevelItem(0).addChild(programItem)
            self.widgets.addWidget(programWidget)

        for code in self.sharc.codeList:
            source = ShaderSource()
            source.setPlainText(code.code)

            sourceItem = QtWidgets.QTreeWidgetItem(2)
            sourceItem.setText(0, code.name)
            self.treeWidget.topLevelItem(1).addChild(sourceItem)
            self.widgets.addWidget(source)

        if self.getProgramCount() > 0:
            self.treeWidget.topLevelItem(0).setExpanded(True)
            self.treeWidget.topLevelItem(0).child(0).setSelected(True)

        if len(self.sharc.codeList):
            self.treeWidget.topLevelItem(1).setExpanded(True)

    def add(self) -> None:
        current = self.treeWidget.currentItem()
        if current.type() == 0:
            index = self.treeWidget.indexOfTopLevelItem(current)

        else:
            index = current.type() - 1

        if index == 0:
            name = QtWidgets.QInputDialog.getText(self, "Choose name",
                                                  "Choose a name for this shader program (if exists, won't be added):",
                                                  QtWidgets.QLineEdit.Normal)[0]

            if not name:
                return

            for i in range(self.treeWidget.topLevelItem(0).childCount()):
                programItem = self.treeWidget.topLevelItem(0).child(i)
                if programItem.text(0) == name:
                    return

            programWidget = ShaderProgram(self)
            programWidget.vertexCode.addItems(self.codeFiles)
            programWidget.fragmentCode.addItems(self.codeFiles)
            programWidget.vertexCode.setCurrentIndex(-1)
            programWidget.fragmentCode.setCurrentIndex(-1)

            programItem = QtWidgets.QTreeWidgetItem(1)
            programItem.setText(0, name)
            self.treeWidget.topLevelItem(0).addChild(programItem)
            self.widgets.addWidget(programWidget)
            self.sharc.programCount += 1

        else:
            file = QtWidgets.QFileDialog.getOpenFileName(None, "Open File", "", "GLSL Shader (*.sh *.glsl)")[0]
            if not (file and os.path.isfile(file)):
                return

            name = os.path.basename(file)
            if name in self.codeFiles:
                return

            self.codeFiles.append(name)

            code = sharc.ShaderCode()
            code.name = name

            with open(file, encoding='utf-8') as inf:
                code.code = inf.read()

            self.sharc.codeList.append(code)

            source = ShaderSource()
            source.setPlainText(code.code)

            sourceItem = QtWidgets.QTreeWidgetItem(2)
            sourceItem.setText(0, code.name)
            self.treeWidget.topLevelItem(1).addChild(sourceItem)
            self.widgets.addWidget(source)

            for i in range(self.getProgramCount()):
                programWidget = cast(ShaderProgram, self.widgets.widget(i))

                vtxShIdx = programWidget.vertexCode.currentIndex()
                programWidget.vertexCode.clear()
                programWidget.vertexCode.addItems(self.codeFiles)
                programWidget.vertexCode.setCurrentIndex(vtxShIdx)

                frgShIdx = programWidget.fragmentCode.currentIndex()
                programWidget.fragmentCode.clear()
                programWidget.fragmentCode.addItems(self.codeFiles)
                programWidget.fragmentCode.setCurrentIndex(frgShIdx)

    def remove(self) -> None:
        current = self.treeWidget.currentItem()
        if current.type() == 0:
            index = self.treeWidget.indexOfTopLevelItem(current)

        else:
            index = current.type() - 1

        if index == 0:
            index = self.widgets.currentIndex()
            if index < 0:
                return

            # self.sharc.progList.pop(index)
            self.sharc.programCount -= 1

            sip.delete(self.treeWidget.topLevelItem(0).child(index))
            sip.delete(self.widgets.currentWidget())

        else:
            index = self.widgets.currentIndex() - self.getProgramCount()
            if index < 0:
                return

            for i in range(self.getProgramCount()):
                programWidget = cast(ShaderProgram, self.widgets.widget(i))
                if index in (programWidget.vertexCode.currentIndex(), programWidget.fragmentCode.currentIndex()):
                    return

            self.codeFiles.pop(index)
            self.sharc.codeList.pop(index)

            sip.delete(self.treeWidget.topLevelItem(1).child(index))
            sip.delete(self.widgets.currentWidget())

            for i in range(self.getProgramCount()):
                programWidget = cast(ShaderProgram, self.widgets.widget(i))

                vtxShIdx = programWidget.vertexCode.currentIndex()
                programWidget.vertexCode.clear()
                programWidget.vertexCode.addItems(self.codeFiles)
                if vtxShIdx > index:
                    programWidget.vertexCode.setCurrentIndex(vtxShIdx - 1)

                else:
                    programWidget.vertexCode.setCurrentIndex(vtxShIdx)

                frgShIdx = programWidget.fragmentCode.currentIndex()
                programWidget.fragmentCode.clear()
                programWidget.fragmentCode.addItems(self.codeFiles)
                if frgShIdx > index:
                    programWidget.fragmentCode.setCurrentIndex(frgShIdx - 1)

                else:
                    programWidget.fragmentCode.setCurrentIndex(frgShIdx)

    def save(self) -> None:
        self.sharc.progList = sharc.ResList()
        for i in range(self.getProgramCount()):
            programWidget = cast(ShaderProgram, self.widgets.widget(i))
            programItem = self.treeWidget.topLevelItem(0).child(i)

            program = sharc.ShaderProgram()
            program.name = programItem.text(0)
            program.vtxShIdx = programWidget.vertexCode.currentIndex()
            program.frgShIdx = programWidget.fragmentCode.currentIndex()

            for r in range(programWidget.vertexMacros.rowCount() - 1):
                nameCell = programWidget.vertexMacros.item(r, 0)
                valueCell = programWidget.vertexMacros.item(r, 1)

                macro = sharc.ShaderProgram.ShaderMacro()
                macro.name = nameCell.text()
                macro.value = valueCell.text()

                program.vertexMacros.append(macro)

            for r in range(programWidget.fragmentMacros.rowCount() - 1):
                nameCell = programWidget.fragmentMacros.item(r, 0)
                valueCell = programWidget.fragmentMacros.item(r, 1)

                macro = sharc.ShaderProgram.ShaderMacro()
                macro.name = nameCell.text()
                macro.value = valueCell.text()

                program.fragmentMacros.append(macro)

            for r in range(programWidget.uniformVars.rowCount() - 1):
                nameCell = programWidget.uniformVars.item(r, 0)
                idCell = programWidget.uniformVars.item(r, 1)
                defaultValCell = programWidget.uniformVars.item(r, 2)
                offsetCell = programWidget.uniformVars.item(r, 3)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.name = nameCell.text()
                sym.variable.name = idCell.text()
                sym.variable.default = eval(defaultValCell.text())
                sym.variable.offset = int(offsetCell.text())
                sym.variationFlags = [True]

                program.uniformVariables.append(sym)

            for r in range(programWidget.uniformBlocks.rowCount() - 1):
                nameCell = programWidget.uniformBlocks.item(r, 0)
                idCell = programWidget.uniformBlocks.item(r, 1)
                defaultValCell = programWidget.uniformBlocks.item(r, 2)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.name = nameCell.text()
                sym.variable.name = idCell.text()
                sym.variable.default = eval(defaultValCell.text())
                sym.variable.offset = len(sym.variable.default)
                sym.variationFlags = [True]

                program.uniformBlocks.append(sym)

            for r in range(programWidget.samplerVars.rowCount() - 1):
                nameCell = programWidget.samplerVars.item(r, 0)
                idCell = programWidget.samplerVars.item(r, 1)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.name = nameCell.text()
                sym.variable.name = idCell.text()
                sym.variable.default = b''
                sym.variable.offset = -1
                sym.variationFlags = [True]

                program.samplerVariables.append(sym)

            for r in range(programWidget.vertexAttribs.rowCount() - 1):
                nameCell = programWidget.vertexAttribs.item(r, 0)
                idCell = programWidget.vertexAttribs.item(r, 1)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.name = nameCell.text()
                sym.variable.name = idCell.text()
                sym.variable.default = b''
                sym.variable.offset = -1
                sym.variationFlags = [True]

                program.attribVariables.append(sym)

            self.sharc.progList.append(program)

    def saveFile(self) -> None:
        file = self.fileLineEdit.text()
        if not file:
            return self.saveFileAs()

        self.save()

        with open(file, "wb") as out:
            out.write(sharc.save(self.sharc.header, self.sharc.progList, self.sharc.codeList))

    def saveFileAs(self) -> None:
        file = QtWidgets.QFileDialog.getSaveFileName(None, "Save File As", "", "AGL Resource Shader Archive (*.sharc)")[0]
        if not file:
            return

        self.save()
        self.sharc.header.name = os.path.splitext(os.path.basename(file))[0]
        self.fileLineEdit.setText(file)

        with open(file, "wb") as out:
            out.write(sharc.save(self.sharc.header, self.sharc.progList, self.sharc.codeList))

    def currentChanged(self, item: QtWidgets.QTreeWidgetItem) -> None:
        type = item.type()
        if type == 1:
            self.widgets.setCurrentIndex(self.treeWidget.topLevelItem(0).indexOfChild(item))

        elif type == 2:
            self.widgets.setCurrentIndex(self.treeWidget.topLevelItem(1).indexOfChild(item) + self.getProgramCount())


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

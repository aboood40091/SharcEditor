#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
from PyQt5 import QtCore, QtGui, QtWidgets
import sip

from highlighter import Highlighter
import sharc


class Sharc:
    header = None
    progList = None
    codeList = None

    def set(self, progList, codeList, header):
        self.header = header
        self.progList = progList
        self.codeList = codeList


class TableWidget(QtWidgets.QTableWidget):
    def __init__(self, headers):
        super().__init__(1, len(headers))

        self.cellChanged.connect(self.handleCellChange)
        self.setSortingEnabled(False)

        for i, header in enumerate(headers):
            self.setHorizontalHeaderItem(i, QtWidgets.QTableWidgetItem())
            self.horizontalHeaderItem(i).setText(header)

    def handleCellChange(self, r, c):
        rowCount = self.rowCount()

        if r == rowCount - 1 and self.item(r, c).text():
            self.setRowCount(rowCount + 1)

        elif not any((self.item(r, c).text() if self.item(r, c) else False) for c in range(self.columnCount())):
            self.removeRow(r)


class ShaderMacro(TableWidget):
    def __init__(self):
        super().__init__(("Name", "Value"))


class ShaderSymbol(TableWidget):
    def __init__(self):
        super().__init__(("Name", "Default Value", "Offset", "Shader Symbol"))


class TabWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self._tabBar = QtWidgets.QTabBar()
        self._tabBar.currentChanged.connect(self.currentTabChanged)
        sp = self._tabBar.sizePolicy()
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.MinimumExpanding)
        self._tabBar.setSizePolicy(sp)

        self._stackedWidget = QtWidgets.QStackedWidget()

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._tabBar)
        layout.addWidget(self._stackedWidget)

    def addTab(self, widget, name):
        self._tabBar.addTab(name)
        self._stackedWidget.addWidget(widget)

    def currentTabChanged(self, index):
        if index == -1:
            return

        self._stackedWidget.setCurrentIndex(index)


class ShaderSource(QtWidgets.QTextEdit):
    def __init__(self):
        super().__init__()

        font = QtGui.QFont("Inconsolata", 10)
        font.setFixedPitch(True)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)

        self.setFont(font)
        self.setReadOnly(True)


class ShaderSourceTab(QtWidgets.QWidget):
    def __init__(self, parent, type):
        super().__init__()

        self._parent = parent
        self._type = type

        fileLabel = QtWidgets.QLabel()
        fileLabel.setText("File:")

        self._fileComboBox = QtWidgets.QComboBox()
        self._fileComboBox.currentIndexChanged.connect(self.currentChanged)

        fileLayout = QtWidgets.QHBoxLayout()
        fileLayout.addWidget(fileLabel)
        fileLayout.addWidget(self._fileComboBox)

        self._editor = ShaderSource()
        self._highlighter = Highlighter(self._editor.document())

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(fileLayout)
        layout.addWidget(self._editor)

    def addItems(self, texts):
        self._fileComboBox.addItem("None")
        self._fileComboBox.addItems(texts)

    def setCurrentIndex(self, index):
        self._fileComboBox.setCurrentIndex(index + 1)

    def currentIndex(self):
        return self._fileComboBox.currentIndex() - 1

    def clear(self):
        self._fileComboBox.clear()

    def currentChanged(self, index):
        if index == -1:
            return

        if index == 0:
            self._editor.clear()

        else:
            self._editor.setPlainText(self._parent.sharc.codeList[index - 1].code)


class ShaderModel(TabWidget):
    def __init__(self, parent):
        super().__init__()

        self.vertexMacros = ShaderMacro()
        self.fragmentMacros = ShaderMacro()
        self.uniformVars = ShaderSymbol()
        self.uniformBlocks = ShaderSymbol()
        self.samplerVars = ShaderSymbol()
        self.vertexAttribs = ShaderSymbol()

        self.vertexCode = ShaderSourceTab(parent, 0)
        self.fragmentCode = ShaderSourceTab(parent, 1)

        self.uniformBlocks.setColumnHidden(2, True)
        self.samplerVars.setColumnHidden(1, True)
        self.samplerVars.setColumnHidden(2, True)
        self.vertexAttribs.setColumnHidden(1, True)
        self.vertexAttribs.setColumnHidden(2, True)

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
    def __init__(self):
        super().__init__()

        self.setWindowTitle("SharcEditor v0.1 - (C) 2019 AboodXD")

        self.sharc = Sharc()
        self.numPrograms = 0
        self.codeFiles = []

        fileLabel = QtWidgets.QLabel()
        fileLabel.setText("File:")

        self.fileLineEdit = QtWidgets.QLineEdit()
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

        self.treeWidget = QtWidgets.QTreeWidget()
        QtWidgets.QTreeWidgetItem(self.treeWidget)
        QtWidgets.QTreeWidgetItem(self.treeWidget)
        self.treeWidget.headerItem().setText(0, "Shader Definition")
        self.treeWidget.topLevelItem(0).setText(0, "Shading model")
        self.treeWidget.topLevelItem(1).setText(0, "Source code")
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

        self.widgets = QtWidgets.QStackedWidget()

        viewLayout = QtWidgets.QHBoxLayout()
        viewLayout.addLayout(treeLayout)
        viewLayout.addWidget(self.widgets)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(fileLayout)
        layout.addLayout(viewLayout)

    def closeFile(self):
        for i in range(self.widgets.count()-1, -1, -1):
            j = int(i >= self.numPrograms)
            sip.delete(self.treeWidget.topLevelItem(j).child(i - j*self.numPrograms))
            sip.delete(self.widgets.widget(i))

        self.treeWidget.topLevelItem(0).setSelected(False)
        self.treeWidget.topLevelItem(1).setSelected(False)

        self.sharc.header = None
        self.sharc.progList = None
        self.sharc.codeList = None
        self.numPrograms = 0
        self.codeFiles = []

    def openFile(self):
        file = QtWidgets.QFileDialog.getOpenFileName(None, "Open File", "", "NW4F Shader Archive (*.sharc)")[0]
        if not (file and os.path.isfile(file)):
            return

        self.closeFile()
        self.fileLineEdit.setText(file)

        with open(file, 'rb') as inf:
            inb = inf.read()

        self.sharc.set(*sharc.load(inb), sharc.header)
        self.numPrograms = self.sharc.progList.len()

        self.codeFiles = []
        for code in self.sharc.codeList:
            self.codeFiles.append(code.name)

        for program in self.sharc.progList:
            model = ShaderModel(self)
            model.vertexCode.addItems(self.codeFiles)
            model.fragmentCode.addItems(self.codeFiles)
            model.vertexCode.setCurrentIndex(program.vtxShIdx)
            model.fragmentCode.setCurrentIndex(program.frgShIdx)

            for i, macro in enumerate(program.vertexMacros):
                nameCell = QtWidgets.QTableWidgetItem()
                valueCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(macro.name)
                valueCell.setText(macro.value)

                model.vertexMacros.setItem(i, 0, nameCell)
                model.vertexMacros.setItem(i, 1, valueCell)
                model.vertexMacros.setRowCount(i + 2)

            for i, macro in enumerate(program.fragmentMacros):
                nameCell = QtWidgets.QTableWidgetItem()
                valueCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(macro.name)
                valueCell.setText(macro.value)

                model.fragmentMacros.setItem(i, 0, nameCell)
                model.fragmentMacros.setItem(i, 1, valueCell)
                model.fragmentMacros.setRowCount(i + 2)

            for i, sym in enumerate(program.uniformVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                defaultValCell = QtWidgets.QTableWidgetItem()
                offsetCell = QtWidgets.QTableWidgetItem()
                symCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.variable.name)
                defaultValCell.setText(str(sym.variable.default))
                offsetCell.setText(str(sym.variable.offset))
                symCell.setText(sym.name)

                model.uniformVars.setItem(i, 0, nameCell)
                model.uniformVars.setItem(i, 1, defaultValCell)
                model.uniformVars.setItem(i, 2, offsetCell)
                model.uniformVars.setItem(i, 3, symCell)
                model.uniformVars.setRowCount(i + 2)

            for i, sym in enumerate(program.uniformBlocks):
                nameCell = QtWidgets.QTableWidgetItem()
                defaultValCell = QtWidgets.QTableWidgetItem()
                symCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.variable.name)
                defaultValCell.setText(str(sym.variable.default))
                symCell.setText(sym.name)

                model.uniformBlocks.setItem(i, 0, nameCell)
                model.uniformBlocks.setItem(i, 1, defaultValCell)
                model.uniformBlocks.setItem(i, 3, symCell)
                model.uniformBlocks.setRowCount(i + 2)

            for i, sym in enumerate(program.samplerVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                symCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.variable.name)
                symCell.setText(sym.name)

                model.samplerVars.setItem(i, 0, nameCell)
                model.samplerVars.setItem(i, 3, symCell)
                model.samplerVars.setRowCount(i + 2)

            for i, sym in enumerate(program.attribVariables):
                nameCell = QtWidgets.QTableWidgetItem()
                symCell = QtWidgets.QTableWidgetItem()

                nameCell.setText(sym.variable.name)
                symCell.setText(sym.name)

                model.vertexAttribs.setItem(i, 0, nameCell)
                model.vertexAttribs.setItem(i, 3, symCell)
                model.vertexAttribs.setRowCount(i + 2)

            modelItem = QtWidgets.QTreeWidgetItem(1)
            modelItem.setText(0, program.name)
            self.treeWidget.topLevelItem(0).addChild(modelItem)
            self.widgets.addWidget(model)

        for code in self.sharc.codeList:
            source = ShaderSource()
            highlighter = Highlighter(source.document())
            source.setPlainText(code.code)

            sourceItem = QtWidgets.QTreeWidgetItem(2)
            sourceItem.setText(0, code.name)
            self.treeWidget.topLevelItem(1).addChild(sourceItem)
            self.widgets.addWidget(source)

        if self.numPrograms:
            self.treeWidget.topLevelItem(0).setExpanded(True)
            self.treeWidget.topLevelItem(0).child(0).setSelected(True)

        if self.sharc.codeList.len():
            self.treeWidget.topLevelItem(1).setExpanded(True)

    def add(self):
        current = self.treeWidget.currentItem()
        if current.type() == 0:
            index = self.treeWidget.indexOfTopLevelItem(current)

        else:
            index = current.type() - 1

        if index == 0:
            name = QtWidgets.QInputDialog.getText(self, "Choose name",
                                                  "Choose a name for this shader model (if exists, won't be added):",
                                                  QtWidgets.QLineEdit.Normal)[0]

            if not name:
                return

            for i in range(self.treeWidget.topLevelItem(0).childCount()):
                modelItem = self.treeWidget.topLevelItem(0).child(i)
                if modelItem.text(0) == name:
                    return

            model = ShaderModel(self)
            model.vertexCode.addItems(self.codeFiles)
            model.fragmentCode.addItems(self.codeFiles)
            model.vertexCode.setCurrentIndex(-1)
            model.fragmentCode.setCurrentIndex(-1)

            modelItem = QtWidgets.QTreeWidgetItem(1)
            modelItem.setText(0, name)
            self.treeWidget.topLevelItem(0).addChild(modelItem)
            self.widgets.addWidget(model)

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

            if not self.sharc.codeList:
                self.sharc.codeList = sharc.List()

            self.sharc.codeList.append(code)

            source = ShaderSource()
            highlighter = Highlighter(source.document())
            source.setPlainText(code.code)

            sourceItem = QtWidgets.QTreeWidgetItem(2)
            sourceItem.setText(0, code.name)
            self.treeWidget.topLevelItem(1).addChild(sourceItem)
            self.widgets.addWidget(source)

            for i in range(self.numPrograms):
                model = self.widgets.widget(i)

                vtxShIdx = model.vertexCode.currentIndex()
                model.vertexCode.clear()
                model.vertexCode.addItems(self.codeFiles)
                model.vertexCode.setCurrentIndex(vtxShIdx)

                frgShIdx = model.fragmentCode.currentIndex()
                model.fragmentCode.clear()
                model.fragmentCode.addItems(self.codeFiles)
                model.fragmentCode.setCurrentIndex(frgShIdx)

    def remove(self):
        current = self.treeWidget.currentItem()
        if current.type() == 0:
            index = self.treeWidget.indexOfTopLevelItem(current)

        else:
            index = current.type() - 1

        if index == 0:
            index = self.widgets.currentIndex()
            if index == -1:
                return

            sip.delete(self.treeWidget.topLevelItem(0).child(index))
            sip.delete(self.widgets.currentWidget())

            self.numPrograms -= 1

        else:
            index = self.widgets.currentIndex() - self.numPrograms
            if index == -1:
                return

            for i in range(self.numPrograms):
                model = self.widgets.widget(i)
                if index in (model.vertexCode.currentIndex(), model.fragmentCode.currentIndex()):
                    return

            self.codeFiles.pop(index)
            self.sharc.codeList.pop(index)

            sip.delete(self.treeWidget.topLevelItem(1).child(index))
            sip.delete(self.widgets.currentWidget())

            for i in range(self.numPrograms):
                model = self.widgets.widget(i)

                vtxShIdx = model.vertexCode.currentIndex()
                model.vertexCode.clear()
                model.vertexCode.addItems(self.codeFiles)
                if vtxShIdx > index:
                    model.vertexCode.setCurrentIndex(vtxShIdx - 1)

                else:
                    model.vertexCode.setCurrentIndex(vtxShIdx)

                frgShIdx = model.fragmentCode.currentIndex()
                model.fragmentCode.clear()
                model.fragmentCode.addItems(self.codeFiles)
                if frgShIdx > index:
                    model.fragmentCode.setCurrentIndex(frgShIdx - 1)

                else:
                    model.fragmentCode.setCurrentIndex(frgShIdx)

    def save(self):
        self.sharc.progList = sharc.List()
        for i in range(self.numPrograms):
            model = self.widgets.widget(i)
            modelItem = self.treeWidget.topLevelItem(0).child(i)

            program = sharc.ShaderProgram()
            program.name = modelItem.text(0)
            program.vtxShIdx = model.vertexCode.currentIndex()
            program.frgShIdx = model.fragmentCode.currentIndex()

            for r in range(model.vertexMacros.rowCount() - 1):
                nameCell = model.vertexMacros.item(r, 0)
                valueCell = model.vertexMacros.item(r, 1)

                macro = sharc.ShaderProgram.ShaderMacro()
                macro.name = nameCell.text()
                macro.value = valueCell.text()

                program.vertexMacros.append(macro)

            for r in range(model.fragmentMacros.rowCount() - 1):
                nameCell = model.fragmentMacros.item(r, 0)
                valueCell = model.fragmentMacros.item(r, 1)

                macro = sharc.ShaderProgram.ShaderMacro()
                macro.name = nameCell.text()
                macro.value = valueCell.text()

                program.fragmentMacros.append(macro)

            for r in range(model.uniformVars.rowCount() - 1):
                nameCell = model.uniformVars.item(r, 0)
                defaultValCell = model.uniformVars.item(r, 1)
                offsetCell = model.uniformVars.item(r, 2)
                symCell = model.uniformVars.item(r, 3)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.variable.name = nameCell.text()
                sym.variable.default = eval(defaultValCell.text())
                sym.variable.offset = int(offsetCell.text())
                sym.name = symCell.text()
                sym.variationFlags = [True]

                program.uniformVariables.append(sym)

            for r in range(model.uniformBlocks.rowCount() - 1):
                nameCell = model.uniformBlocks.item(r, 0)
                defaultValCell = model.uniformBlocks.item(r, 1)
                symCell = model.uniformBlocks.item(r, 3)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.variable.name = nameCell.text()
                sym.variable.default = eval(defaultValCell.text())
                sym.variable.offset = len(sym.variable.default)
                sym.name = symCell.text()
                sym.variationFlags = [True]

                program.uniformBlocks.append(sym)

            for r in range(model.samplerVars.rowCount() - 1):
                nameCell = model.samplerVars.item(r, 0)
                symCell = model.samplerVars.item(r, 3)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.variable.name = nameCell.text()
                sym.variable.default = b''
                sym.variable.offset = -1
                sym.name = symCell.text()
                sym.variationFlags = [True]

                program.samplerVariables.append(sym)

            for r in range(model.vertexAttribs.rowCount() - 1):
                nameCell = model.vertexAttribs.item(r, 0)
                symCell = model.vertexAttribs.item(r, 3)

                sym = sharc.ShaderProgramBase.ShaderSymbol()
                sym.variable.name = nameCell.text()
                sym.variable.default = b''
                sym.variable.offset = -1
                sym.name = symCell.text()
                sym.variationFlags = [True]

                program.attribVariables.append(sym)

            self.sharc.progList.append(program)

    def saveFile(self):
        self.save()

        with open(self.fileLineEdit.text(), "wb") as out:
            out.write(sharc.save(self.sharc.progList, self.sharc.codeList))

    def saveFileAs(self):
        file = QtWidgets.QFileDialog.getSaveFileName(None, "Save File As", "", "NW4F Shader Archive (*.sharc)")[0]
        if not file:
            return

        self.save()
        self.sharc.header.name = os.path.splitext(os.path.basename(file))[0]
        self.fileLineEdit.setText(file)

        with open(file, "wb") as out:
            out.write(sharc.save(self.sharc.progList, self.sharc.codeList))

    def currentChanged(self, item):
        type = item.type()
        if type == 1:
            self.widgets.setCurrentIndex(self.treeWidget.topLevelItem(0).indexOfChild(item))

        elif type == 2:
            self.widgets.setCurrentIndex(self.treeWidget.topLevelItem(1).indexOfChild(item) + self.numPrograms)


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec_())

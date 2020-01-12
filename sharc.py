#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import struct


header = None
supported_versions = 10, 11


class Header:
    def __init__(self, endianness='<'):
        self.format = '5I'
        self.endianness = endianness

        self.magic = 0x53484141  # SHAA
        self.version = 11
        self.fileSize = 0
        self.name = ''

    def load(self, data, pos=0):
        (self.magic,
         self.version,
         self.fileSize,
         endianness,
         nameLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        assert self.magic == 0x53484141 and endianness == 1

        size = struct.calcsize(self.format)
        pos += size

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        self.size = size + nameLen

        assert self.version in supported_versions

    def save(self):
        name = self.name.encode('utf-8') + b'\0'

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.magic,
                self.version,
                0,
                1,
                len(name),
            ),
            name,
        ])


class ShaderProgramBase:
    class VariationMacro:
        def __init__(self, endianness='<'):
            self.format = '4I'
            self.endianness = endianness

            self.size = 0
            self.data = b''

        def __str__(self):
            return 'Variation Macro'

        def load(self, data, pos):
            (self.size,
             _4,
             _8,
             _C) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            assert self.size == 8  # Structure is incomplete
            self.data = data[pos:pos + self.size]

        def save(self):
            return self.data

    class VariationSymbol:
        def __init__(self, endianness='<'):
            self.format = '4I'
            self.endianness = endianness

            self.size = 0
            self.data = b''

        def __str__(self):
            return 'Variation Symbol'

        def load(self, data, pos):
            (self.size,
             _4,
             _8,
             _C) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            assert self.size == 8  # Structure is incomplete
            self.data = data[pos:pos + self.size]

        def save(self):
            return self.data

    class ShaderSymbol:
        class Variable:
            def __init__(self, name='', default=b'', offset=-1):
                self.name = name
                self.default = default
                self.offset = offset

        def __init__(self, endianness='<'):
            self.format = 'Ii4I'
            self.endianness = endianness

            self.size = 0

            self.name = ''
            self.variable = ShaderProgramBase.ShaderSymbol.Variable()
            self.variationFlags = []

        def __str__(self):
            return 'Shader symbol'

        def load(self, data, pos):
            (self.size,
             self.variable.offset,
             nameLen,
             variableNameLen,
             defaultValueLen,
             variationCount) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            pos += struct.calcsize(self.format)
            self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

            pos += nameLen
            self.variable.name = data[pos:pos + variableNameLen].decode('utf-8').rstrip('\0')

            pos += variableNameLen
            self.variable.default = data[pos:pos + defaultValueLen]

            pos += defaultValueLen
            self.variationFlags = list(map(bool, data[pos:pos + variationCount]))

        def save(self):
            name = self.name.encode('utf-8') + b'\0'
            variableName = self.variable.name.encode('utf-8') + b'\0'

            return b''.join([
                struct.pack(
                    '%s%s' % (self.endianness, self.format),
                    struct.calcsize(self.format) + len(name) + len(variableName) + len(self.variable.default) + len(self.variationFlags),
                    self.variable.offset,
                    len(name),
                    len(variableName),
                    len(self.variable.default),
                    len(self.variationFlags),
                ),
                name,
                variableName,
                self.variable.default,
                bytes(map(int, self.variationFlags))
            ])


class ShaderProgram:
    class ShaderMacro:
        def __init__(self, endianness='<'):
            self.format = '3I'
            self.endianness = endianness

            self.size = 0
            self.name = ''
            self.value = ''

        def __str__(self):
            return 'Shader Macro'

        def load(self, data, pos):
            (self.size,
             nameLen,
             valueLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            pos += struct.calcsize(self.format)
            self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

            pos += nameLen
            self.value = data[pos:pos + valueLen].decode('utf-8').rstrip('\0')

        def save(self):
            name = self.name.encode('utf-8') + b'\0'
            value = self.value.encode('utf-8') + b'\0'

            return b''.join([
                struct.pack(
                    '%s%s' % (self.endianness, self.format),
                    struct.calcsize(self.format) + len(name) + len(value),
                    len(name),
                    len(value),
                ),
                name,
                value,
            ])

    def __init__(self, endianness='<'):
        self.format = '2I3i'
        self.endianness = endianness

        self.size = 0
        self.vtxShIdx = -1
        self.frgShIdx = -1
        self.geoShIdx = -1

        self.vertexMacros = List(self.endianness)
        self.fragmentMacros = List(self.endianness)
        self.geometryMacros = List(self.endianness)

        self.variations = List(self.endianness)
        self.variationSymbols = List(self.endianness)

        self.uniformVariables = List(self.endianness)
        self.uniformBlocks = List(self.endianness)
        self.samplerVariables = List(self.endianness)
        self.attribVariables = List(self.endianness)

        self.name = ''

    def __str__(self):
        return 'Shader Program'

    def load(self, data, pos):
        (self.size,
         nameLen,
         self.vtxShIdx,
         self.frgShIdx,
         self.geoShIdx) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        pos += struct.calcsize(self.format)
        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

        pos += nameLen
        self.vertexMacros.load(data, pos, ShaderProgram.ShaderMacro)

        pos += self.vertexMacros.size
        self.fragmentMacros.load(data, pos, ShaderProgram.ShaderMacro)

        pos += self.fragmentMacros.size
        self.geometryMacros.load(data, pos, ShaderProgram.ShaderMacro)

        pos += self.geometryMacros.size
        self.variations.load(data, pos, ShaderProgramBase.VariationMacro)

        pos += self.variations.size
        if header.version == 11:
            self.variationSymbols.load(data, pos, ShaderProgramBase.VariationSymbol)
            pos += self.variationSymbols.size

        self.uniformVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.uniformVariables.size
        self.uniformBlocks.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.uniformBlocks.size
        self.samplerVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.samplerVariables.size
        self.attribVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

    def save(self):
        name = self.name.encode('utf-8') + b'\0'

        vertexMacros = self.vertexMacros.save()
        fragmentMacros = self.fragmentMacros.save()
        geometryMacros = self.geometryMacros.save()
        variations = self.variations.save()
        uniformVariables = self.uniformVariables.save()
        uniformBlocks = self.uniformBlocks.save()
        samplerVariables = self.samplerVariables.save()
        attribVariables = self.attribVariables.save()

        if header.version == 11:
            variationSymbols = self.variationSymbols.save()

        else:
            variationSymbols = b''

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                struct.calcsize(self.format) + len(name) + len(vertexMacros) + len(fragmentMacros) + len(geometryMacros) + len(variations) + len(variationSymbols) + len(uniformVariables) + len(uniformBlocks) + len(samplerVariables) + len(attribVariables),
                len(name),
                self.vtxShIdx,
                self.frgShIdx,
                self.geoShIdx,
            ),
            name,
            vertexMacros,
            fragmentMacros,
            geometryMacros,
            variations,
            variationSymbols,
            uniformVariables,
            uniformBlocks,
            samplerVariables,
            attribVariables,
        ])


class ShaderCode:
    def __init__(self, endianness='<'):
        self.format = '4I'
        self.endianness = endianness

        self.size = 0
        self.name = ''
        self.code = ''

    def __str__(self):
        return 'Shader Code'

    def load(self, data, pos):
        (self.size,
         nameLen,
         codeLen,
         codeLen2) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        pos += struct.calcsize(self.format)
        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

        pos += nameLen; assert codeLen == codeLen2
        self.code = data[pos:pos + codeLen].decode('shift-jis')

    def save(self):
        name = self.name.encode('utf-8') + b'\0'
        code = self.code.encode('shift-jis')

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                struct.calcsize(self.format) + len(name) + len(code),
                len(name),
                len(code),
                len(code),
            ),
            name,
            code,
        ])

    def export(self, path):
        with open(os.path.join(path, self.name), 'wb+') as out:
            out.write(self.code.encode('utf-8'))


class ListBase:
    def __init__(self, endianness='<'):
        self.format = '2I'
        self.endianness = endianness

        self.size = 0
        self.count = 0
        self.items = []

    def __getitem__(self, i):
        if not isinstance(i, int):
            raise TypeError("index must be an integer")

        return self.items[i]

    def append(self, item):
        self.items.append(item)

    def extend(self, itemList):
        self.items.extend(itemList)

    def pop(self, index):
        return self.items.pop(index)

    def len(self):
        return len(self.items)

    def load(self, data, pos, ItemClass=None):
        (self.size,
         self.count) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        pos += struct.calcsize(self.format)
        if ItemClass:
            for _ in range(self.count):
                item = ItemClass(self.endianness)
                item.load(data, pos)

                pos += item.size
                self.append(item)


class List(ListBase):
    def index(self, item):
        if isinstance(item, str):
            for i, oItem in enumerate(self.items):
                if isinstance(oItem, ShaderProgram.ShaderMacro) and oItem.name == item:
                    return i

        else:
            for i, oItem in enumerate(self.items):
                if item == oItem:
                    return i

        return -1

    def save(self):
        outBuffer = b''.join([item.save() for item in self])

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                struct.calcsize(self.format) + len(outBuffer),
                self.len(),
            ),
            outBuffer,
        ])


def load(inb, pos=0):
    global header
    header = Header()
    header.load(inb, pos)

    pos += header.size

    progList = List()
    progList.load(inb, pos, ShaderProgram)

    pos += progList.size

    codeList = List()
    codeList.load(inb, pos, ShaderCode)

    pos += codeList.size

    return progList, codeList


def save(progList, codeList):
    outBuffer = bytearray(b''.join([
        header.save(),
        progList.save(),
        codeList.save(),
    ]))

    outBuffer[8:12] = struct.pack('%sI' % header.endianness, len(outBuffer))
    return outBuffer

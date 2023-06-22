#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import struct


header = None


class Header:
    def __init__(self, endianness='<'):
        self.format = '5I'
        self.endianness = endianness

        self.name = ''
        self.size = 0

    def load(self, data, pos=0):
        (magic,
         version,
         fileSize,
         endianness,
         nameLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        assert magic == 0x53484141 and endianness == 1 and version == 11

        size = struct.calcsize(self.format)
        pos += size

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        self.size = size + nameLen

    def save(self):
        name = (self.name + '\0').encode('utf-8')
        nameLen = len(name)

        self.size = struct.calcsize(self.format) + nameLen

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                0x53484141,  # SHAA
                11,
                0,
                1,
                nameLen,
            ),
            name,
        ])


class ShaderVariation:
    def __init__(self, endianness='<'):
        self.format = '2IiI'
        self.endianness = endianness

        self.size = 0

        self.name = ''
        self.values = []
        self.ID = ''

    def __str__(self):
        return 'Shader Variation Macro'

    def getName(self):
        return repr((self.name, self.ID))

    def load(self, data, pos):
        (self.size,
         nameLen,
         valueCount,
         idLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)
        assert self.size >= struct.calcsize(self.format)
        pos += struct.calcsize(self.format)

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        pos += nameLen

        self.values.clear()
        for _ in range(valueCount):
            while data[pos] == 0:
                pos += 1

            start_pos = pos
            pos += 1

            while data[pos] != 0:
                pos += 1

            pos += 1

            self.values.append(data[start_pos:pos].decode('utf-8').rstrip('\0'))

        self.ID = data[pos:pos + idLen].decode('utf-8').rstrip('\0')

    def save(self):
        for value in self.values:
            assert value

        name = (self.name + '\0').encode('utf-8')
        values = b''.join([(value + '\0').encode('utf-8') for value in self.values])
        ID = (self.ID + '\0').encode('utf-8')

        nameLen = len(name)
        idLen = len(ID)

        self.size = struct.calcsize(self.format) + nameLen + len(values) + idLen

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                nameLen,
                len(self.values),
                idLen,
            ),
            name,
            values,
            ID,
        ])


class ShaderSymbol:
    def __init__(self, endianness='<'):
        self.format = 'Ii4I'
        self.endianness = endianness

        self.size = 0

        self.param = 0
        self.name = ''
        self.ID = ''
        self.defaultValue = b''
        self.validVariations = []

    def __str__(self):
        return 'Shader Symbol'

    def getName(self):
        return repr((self.name, self.ID))

    def load(self, data, pos):
        (self.size,
         self.param,
         nameLen,
         idLen,
         defaultValueLen,
         variationCount) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)
        assert self.size >= struct.calcsize(self.format)
        pos += struct.calcsize(self.format)

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        pos += nameLen

        self.ID = data[pos:pos + idLen].decode('utf-8').rstrip('\0')
        pos += idLen

        self.defaultValue = data[pos:pos + defaultValueLen]
        pos += defaultValueLen

        self.validVariations = list(map(bool, data[pos:pos + variationCount]))

    def save(self):
        name = (self.name + '\0').encode('utf-8')
        ID = (self.ID + '\0').encode('utf-8')

        nameLen = len(name)
        idLen = len(ID)
        defaultValueLen = len(self.defaultValue)
        variationCount = len(self.validVariations)

        self.size = struct.calcsize(self.format) + nameLen + idLen + defaultValueLen + variationCount

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                self.param,
                nameLen,
                idLen,
                defaultValueLen,
                variationCount,
            ),
            name,
            ID,
            self.defaultValue,
            bytes(map(int, self.validVariations)),
        ])


class ShaderMacro:
    def __init__(self, endianness='<'):
        self.format = '3I'
        self.endianness = endianness

        self.size = 0

        self.name = ''
        self.value = ''

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other

        return super().__eq__(other)

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
        name = (self.name + '\0').encode('utf-8')
        value = (self.value + '\0').encode('utf-8')

        nameLen = len(name)
        valueLen = len(value)

        self.size = struct.calcsize(self.format) + nameLen + valueLen

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                nameLen,
                valueLen,
            ),
            name,
            value,
        ])


class ShaderProgram:
    def __init__(self, endianness='<'):
        self.format = '2I3i'
        self.endianness = endianness

        self.size = 0

        self.name = ''
        self.vtxShIdx = -1
        self.frgShIdx = -1
        self.geoShIdx = -1

        self.vertexMacros = List(self.endianness)
        self.fragmentMacros = List(self.endianness)
        self.geometryMacros = List(self.endianness)

        self.variations = List(self.endianness)
        self.variationDefaults = List(self.endianness)

        self.uniformVariables = List(self.endianness)
        self.uniformBlocks = List(self.endianness)
        self.samplerVariables = List(self.endianness)
        self.attribVariables = List(self.endianness)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other

        return super().__eq__(other)

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

        self.vertexMacros.load(data, pos, ShaderMacro)
        pos += self.vertexMacros.size

        self.fragmentMacros.load(data, pos, ShaderMacro)
        pos += self.fragmentMacros.size

        self.geometryMacros.load(data, pos, ShaderMacro)
        pos += self.geometryMacros.size

        self.variations.load(data, pos, ShaderVariation)
        pos += self.variations.size

        self.variationDefaults.load(data, pos, ShaderVariation)
        pos += self.variationDefaults.size

        self.uniformVariables.load(data, pos, ShaderSymbol)
        pos += self.uniformVariables.size

        self.uniformBlocks.load(data, pos, ShaderSymbol)
        pos += self.uniformBlocks.size

        self.samplerVariables.load(data, pos, ShaderSymbol)
        pos += self.samplerVariables.size

        self.attribVariables.load(data, pos, ShaderSymbol)
        pos += self.attribVariables.size

        for default in self.variationDefaults:
            defaultName = default.getName()
            for variation in self.variations:
                if defaultName == variation.getName():
                    assert len(default.values) <= 1

                    break

            else:
                print("Variation default %s does not match any variation" % defaultName)

        for variation in self.variations:
            variationName = variation.getName()
            for default in self.variationDefaults:
                if variationName == default.getName():
                    if variation.values and not default.values:
                        print("Variation %s does not have a default (1)" % variationName)

                    break

            else:
                if not variation.values:
                    print("Variation %s does not have a default (2)" % variationName)

                elif len(variation.values) == 1:
                    print("Variation %s does not have a default (3)" % variationName)

                else:
                    print("Variation %s does not have a default (4)" % variationName)

        for sym in self.uniformBlocks:
            assert sym.param == len(sym.defaultValue)

        for sym in self.samplerVariables:
            assert not sym.defaultValue
            assert sym.param == -1

        for sym in self.attribVariables:
            assert not sym.defaultValue
            assert sym.param == -1

    def save(self):
        name = (self.name + '\0').encode('utf-8')
        nameLen = len(name)

        vertexMacros = self.vertexMacros.save()
        fragmentMacros = self.fragmentMacros.save()
        geometryMacros = self.geometryMacros.save()

        variations = self.variations.save()
        variationDefaults = self.variationDefaults.save()

        uniformVariables = self.uniformVariables.save()
        uniformBlocks = self.uniformBlocks.save()
        samplerVariables = self.samplerVariables.save()
        attribVariables = self.attribVariables.save()

        self.size = (
            struct.calcsize(self.format) +
            nameLen +
            self.vertexMacros.size +
            self.fragmentMacros.size +
            self.geometryMacros.size +
            self.variations.size +
            self.variationDefaults.size +
            self.uniformVariables.size +
            self.uniformBlocks.size +
            self.samplerVariables.size +
            self.attribVariables.size
        )

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                nameLen,
                self.vtxShIdx,
                self.frgShIdx,
                self.geoShIdx,
            ),
            name,
            vertexMacros,
            fragmentMacros,
            geometryMacros,
            variations,
            variationDefaults,
            uniformVariables,
            uniformBlocks,
            samplerVariables,
            attribVariables,
        ])


class ShaderSource:
    def __init__(self, endianness='<'):
        self.format = '4I'
        self.endianness = endianness

        self.size = 0

        self.name = ''
        self.code = ''

        self._codeLen = 0
        self._codeLen2 = 0

    def __str__(self):
        return 'Shader Code'

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other

        return super().__eq__(other)

    def load(self, data, pos):
        (self.size,
         nameLen,
         codeLen,
         codeLen2) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)
        pos += struct.calcsize(self.format)

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        pos += nameLen

        self.code = data[pos:pos + codeLen].decode('shift-jis')
        pos += codeLen

        self._codeLen = codeLen
        self._codeLen2 = codeLen2

    def save(self):
        name = (self.name + '\0').encode('utf-8')
        code = self.code.encode('shift-jis')

        nameLen = len(name)
        codeLen = len(code)
        codeLen2 = self._codeLen2 if codeLen == self._codeLen else codeLen

        self.size = struct.calcsize(self.format) + nameLen + codeLen

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                nameLen,
                codeLen,
                codeLen2
            ),
            name,
            code,
        ])

    def export(self, path):
        with open(os.path.join(path, self.name), 'wb+') as out:
            out.write(self.code.encode('utf-8'))


class List:
    def __init__(self, endianness='<'):
        self.format = '2I'
        self.endianness = endianness

        self.size = 0

        self.items = []

    def __getitem__(self, i):
        return self.items.__getitem__(i)

    def append(self, item):
        self.items.append(item)

    def extend(self, itemList):
        self.items.extend(itemList)

    def index(self, item):
        try:
            return self.items.index(item)

        except ValueError:
            return -1

    def pop(self, index):
        return self.items.pop(index)

    def __len__(self):
        return self.items.__len__()

    def load(self, data, pos, ItemClass=None):
        (self.size,
         count) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)
        pos += struct.calcsize(self.format)

        if ItemClass:
            for _ in range(count):
                item = ItemClass(self.endianness)
                item.load(data, pos)
                pos += item.size

                self.append(item)

    def save(self):
        outBuffer = b''.join([item.save() for item in self])
        self.size = struct.calcsize(self.format) + len(outBuffer)

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.size,
                len(self),
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
    codeList.load(inb, pos, ShaderSource)

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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import struct
from typing import Optional, Tuple, Iterable, Type, List, TypeVar, Generic, Iterator, Union
try:
    from typing import Literal, Protocol
except ImportError:
    from typing_extensions import Literal, Protocol


TVersion = Literal[10, 11, 12]
supported_versions: Tuple[TVersion, ...] = (10, 11, 12)
curr_version: TVersion = 11

TEndianness = Literal['>', '<']


class ResItemProto(Protocol):
    size: int

    def __init__(self, endianness: TEndianness = ...) -> None: ...
    def load(self, data: bytes, pos: int) -> None: ...
    def save(self) -> bytes: ...


T = TypeVar('T', bound=ResItemProto)


class Header:
    format: Literal['5I'] = '5I'
    magic: Literal[0x53484141] = 0x53484141  # SHAA

    endianness: TEndianness
    version: TVersion
    fileSize: int
    name: str
    size: int

    def __init__(self, endianness: TEndianness = '<') -> None:
        self.endianness = endianness

        self.version = 11
        self.fileSize = 0
        self.name = ''

    def load(self, data: bytes, pos: int = 0) -> None:
        (magic,
         self.version,
         self.fileSize,
         endianness,
         nameLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        assert (self.endianness == '<' and endianness == 1) or (self.endianness == '>' and endianness == 0)
        assert magic == self.magic

        size = struct.calcsize(self.format)
        pos += size

        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')
        self.size = size + nameLen

        assert self.version in supported_versions

    def save(self) -> bytes:
        endianness = {'>': 0, '<': 1}[self.endianness]
        name = self.name.encode('utf-8') + b'\0'

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                self.magic,
                self.version,
                0,
                endianness,
                len(name),
            ),
            name,
        ])


class ResListBase(Generic[T]):
    format: Literal['2I'] = '2I'

    endianness: TEndianness
    size: int
    count: int
    items: List[T]

    def __init__(self, endianness: TEndianness = '<') -> None:
        self.endianness = endianness

        self.size = 0
        self.count = 0
        self.items = []

    def __getitem__(self, i: int) -> T:
        if not isinstance(i, int):
            raise TypeError("index must be an integer")

        return self.items[i]

    def __iter__(self) -> Iterator[T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def append(self, item: T) -> None:
        self.items.append(item)

    def extend(self, itemList: Iterable[T]) -> None:
        self.items.extend(itemList)

    def pop(self, index: int) -> T:
        return self.items.pop(index)

    def len(self) -> int:
        return len(self.items)

    def load(self, data: bytes, pos: int, ItemClass: Optional[Type[T]] = None) -> None:
        base_pos = pos

        (self.size,
         self.count) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        pos += struct.calcsize(self.format)
        if ItemClass is not None:
            for _ in range(self.count):
                item = ItemClass(self.endianness)
                item.load(data, pos)

                pos += item.size
                self.append(item)

        assert pos == base_pos + self.size


class ResList(ResListBase[T]):
    def index(self, item: Union[str, T]) -> int:
        if isinstance(item, str):
            for i, oItem in enumerate(self.items):
                if isinstance(oItem, ShaderProgram.ShaderMacro) and oItem.name == item:
                    return i

        else:
            for i, oItem in enumerate(self.items):
                if item == oItem:
                    return i

        return -1

    def save(self) -> bytes:
        outBuffer = b''.join([item.save() for item in self])

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                struct.calcsize(self.format) + len(outBuffer),
                self.len(),
            ),
            outBuffer,
        ])


class ShaderProgramBase:
    class ShaderVariation:
        class Variable:
            name: str
            validValues: List[str]

            def __init__(self, name: str = '') -> None:
                self.name = name
                self.validValues = []

        format: Literal['4I'] = '4I'

        endianness: TEndianness
        size: int
        name: str
        variable: Variable

        def __init__(self, endianness: TEndianness = '<') -> None:
            self.endianness = endianness

            self.size = 0

            self.name = ''
            self.variable = self.Variable()

        def __str__(self) -> str:
            return 'Shader Variation Macro'

        def getName(self) -> str:
            return repr((self.name, self.variable.name))

        def load(self, data: bytes, pos: int) -> None:
            (self.size,
             nameLen,
             validValueCount,
             variableNameLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            assert self.size >= struct.calcsize(self.format)

            pos += struct.calcsize(self.format)
            self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

            pos += nameLen
            validValues = []
            for _ in range(validValueCount):
                # while data[pos] == 0:  # This is what agl does at runtime, but it ends up in wrong file reading
                #     pos += 1
                valueEnd = data.find(b'\0', pos); assert valueEnd != -1
                validValues.append(data[pos:valueEnd].decode('utf-8'))
                pos = valueEnd + 1

            # while data[pos] == 0:  # This is what agl does at runtime, but it ends up in wrong file reading
            #     pos += 1

            self.variable.name = data[pos:pos + variableNameLen].decode('utf-8').rstrip('\0')
            self.variable.validValues = validValues

            # if self.name == 'NUM_SKINNING_VTX':
            #     self.variable.validValues = [str(int(value) + 1) for value in self.variable.validValues]

        def save(self) -> bytes:
            name = self.name.encode('utf-8') + b'\0'
            validValues = b''.join([value.encode('utf-8') + b'\0' for value in self.variable.validValues])
            variableName = self.variable.name.encode('utf-8') + b'\0'

            return b''.join([
                struct.pack(
                    '%s%s' % (self.endianness, self.format),
                    struct.calcsize(self.format) + len(name) + len(validValues) + len(variableName),
                    len(name),
                    len(self.variable.validValues),
                    len(variableName),
                ),
                name,
                validValues,
                variableName,
            ])

    class ShaderSymbol:
        class Variable:
            name: str
            default: bytes
            offset: int

            def __init__(self, name: str = '', default: bytes = b'', offset: int = -1) -> None:
                self.name = name
                self.default = default
                self.offset = offset

        format: Literal['Ii4I'] = 'Ii4I'

        endianness: TEndianness
        size: int
        name: str
        variable: Variable
        variationFlags: List[bool]

        def __init__(self, endianness: TEndianness = '<') -> None:
            self.endianness = endianness

            self.size = 0

            self.name = ''
            self.variable = self.Variable()
            self.variationFlags = []

        def __str__(self) -> str:
            return 'Shader symbol'

        def getName(self) -> str:
            return repr((self.name, self.variable.name))

        def load(self, data: bytes, pos: int) -> None:
            (self.size,
             self.variable.offset,
             nameLen,
             variableNameLen,
             defaultValueLen,
             variationCount) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            assert self.size >= struct.calcsize(self.format)

            pos += struct.calcsize(self.format)
            self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

            pos += nameLen
            self.variable.name = data[pos:pos + variableNameLen].decode('utf-8').rstrip('\0')

            pos += variableNameLen
            self.variable.default = data[pos:pos + defaultValueLen]

            pos += defaultValueLen
            self.variationFlags = list(map(bool, data[pos:pos + variationCount]))

        def save(self) -> bytes:
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
                bytes(map(int, self.variationFlags)),
            ])


class ShaderProgram:
    class ShaderMacro:
        format: Literal['3I'] = '3I'

        endianness: TEndianness
        size: int
        name: str
        value: str

        def __init__(self, endianness: TEndianness = '<') -> None:
            self.endianness = endianness

            self.size = 0
            self.name = ''
            self.value = ''

        def __str__(self) -> str:
            return 'Shader Macro'

        def load(self, data: bytes, pos: int) -> None:
            (self.size,
             nameLen,
             valueLen) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

            pos += struct.calcsize(self.format)
            self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

            pos += nameLen
            self.value = data[pos:pos + valueLen].decode('utf-8').rstrip('\0')

        def save(self) -> bytes:
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

    format: Literal['2I3i'] = '2I3i'

    endianness: TEndianness
    size: int
    vtxShIdx: int
    frgShIdx: int
    geoShIdx: int
    vertexMacros: ResList[ShaderProgram.ShaderMacro]
    fragmentMacros: ResList[ShaderProgram.ShaderMacro]
    geometryMacros: ResList[ShaderProgram.ShaderMacro]
    variations: ResList[ShaderProgramBase.ShaderVariation]
    variationDefaults: ResList[ShaderProgramBase.ShaderVariation]
    uniformVariables: ResList[ShaderProgramBase.ShaderSymbol]
    uniformBlocks: ResList[ShaderProgramBase.ShaderSymbol]
    samplerVariables: ResList[ShaderProgramBase.ShaderSymbol]
    attribVariables: ResList[ShaderProgramBase.ShaderSymbol]
    name: str

    def __init__(self, endianness: TEndianness = '<') -> None:
        self.endianness = endianness

        self.size = 0
        self.vtxShIdx = -1
        self.frgShIdx = -1
        self.geoShIdx = -1

        self.vertexMacros = ResList(self.endianness)
        self.fragmentMacros = ResList(self.endianness)
        self.geometryMacros = ResList(self.endianness)

        self.variations = ResList(self.endianness)
        self.variationDefaults = ResList(self.endianness)

        self.uniformVariables = ResList(self.endianness)
        self.uniformBlocks = ResList(self.endianness)
        self.samplerVariables = ResList(self.endianness)
        self.attribVariables = ResList(self.endianness)

        self.name = ''

    def __str__(self) -> str:
        return 'Shader Program'

    def getVariationCount(self) -> int:
        numVariations = 1
        variation: ShaderProgramBase.ShaderVariation
        for variation in self.variations:
            numVariations *= len(variation.variable.validValues)
        return numVariations

    def searchUniformSymbolName(self, variableName: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.uniformVariables:
            if symbol.variable.name == variableName:
                return symbol.name

        return None

    def searchUniformSymbolVarName(self, name: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.uniformVariables:
            if symbol.name == name:
                return symbol.variable.name

        return None

    def searchUniformBlockSymbolName(self, variableName: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.uniformBlocks:
            if symbol.variable.name == variableName:
                return symbol.name

        return None

    def searchUniformBlockSymbolVarName(self, name: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.uniformBlocks:
            if symbol.name == name:
                return symbol.variable.name

        return None

    def searchSamplerSymbolName(self, variableName: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.samplerVariables:
            if symbol.variable.name == variableName:
                return symbol.name

        return None

    def searchSamplerSymbolVarName(self, name: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.samplerVariables:
            if symbol.name == name:
                return symbol.variable.name

        return None

    def searchAttribSymbolName(self, variableName: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.attribVariables:
            if symbol.variable.name == variableName:
                return symbol.name

        return None

    def searchAttribSymbolVarName(self, name: str) -> Optional[str]:
        symbol: ShaderProgramBase.ShaderSymbol
        for symbol in self.attribVariables:
            if symbol.name == name:
                return symbol.variable.name

        return None

    def load(self, data: bytes, pos: int) -> None:
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
        self.variations.load(data, pos, ShaderProgramBase.ShaderVariation)
        for variation in self.variations:
            assert len(variation.variable.validValues) > 0

        pos += self.variations.size
        if curr_version >= 11:
            self.variationDefaults.load(data, pos, ShaderProgramBase.ShaderVariation)
            pos += self.variationDefaults.size
            for variationDefault in self.variationDefaults:
                assert len(variationDefault.variable.validValues) == 1

        if curr_version == 12:
            # ShaderUniformBlockCount = struct.unpack_from('%sI' % self.endianness, data, pos + 4)[0]
            # if ShaderUniformBlockCount > 0:
            #     print(self.name, ShaderUniformBlockCount)
            pos += struct.unpack_from('%sI' % self.endianness, data, pos)[0]  # Skip ShaderUniformBlock

        self.uniformVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.uniformVariables.size
        self.uniformBlocks.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.uniformBlocks.size
        self.samplerVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

        pos += self.samplerVariables.size
        self.attribVariables.load(data, pos, ShaderProgramBase.ShaderSymbol)

    def save(self) -> bytes:
        name = self.name.encode('utf-8') + b'\0'

        vertexMacros = self.vertexMacros.save()
        fragmentMacros = self.fragmentMacros.save()
        geometryMacros = self.geometryMacros.save()
        variations = self.variations.save()
        uniformVariables = self.uniformVariables.save()
        uniformBlocks = self.uniformBlocks.save()
        samplerVariables = self.samplerVariables.save()
        attribVariables = self.attribVariables.save()

        if curr_version >= 11:
            variationDefaults = self.variationDefaults.save()

        else:
            variationDefaults = b''

        return b''.join([
            struct.pack(
                '%s%s' % (self.endianness, self.format),
                struct.calcsize(self.format) + len(name) + len(vertexMacros) + len(fragmentMacros) + len(geometryMacros) + len(variations) + len(variationDefaults) + len(uniformVariables) + len(uniformBlocks) + len(samplerVariables) + len(attribVariables),
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
            variationDefaults,
            uniformVariables,
            uniformBlocks,
            samplerVariables,
            attribVariables,
        ])


class ShaderCode:
    format: Literal['4I'] = '4I'

    endianness: TEndianness
    size: int
    name: str
    code: str

    def __init__(self, endianness: TEndianness = '<') -> None:
        self.endianness = endianness

        self.size = 0
        self.name = ''
        self.code = ''

    def __str__(self) -> str:
        return 'Shader Code'

    def load(self, data: bytes, pos: int) -> None:
        (self.size,
         nameLen,
         codeLen,
         codeLen2) = struct.unpack_from('%s%s' % (self.endianness, self.format), data, pos)

        pos += struct.calcsize(self.format)
        self.name = data[pos:pos + nameLen].decode('utf-8').rstrip('\0')

        # if codeLen2 != codeLen:
        #     print(self.name, codeLen, codeLen2)
        assert codeLen2 == codeLen

        pos += nameLen
        self.code = data[pos:pos + codeLen].decode('shift-jis')
        # assert not self.code.endswith('\0')

    def save(self) -> bytes:
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

    def export(self, path: str) -> None:
        with open(os.path.join(path, self.name), 'wb+') as out:
            out.write(self.code.encode('utf-8'))


def load(inb: bytes, pos: int = 0) -> Tuple[Header, ResList[ShaderProgram], ResList[ShaderCode]]:
    base_pos = pos

    header = Header()
    header.load(inb, pos)

    pos += header.size

    global curr_version
    curr_version = header.version

    progList: ResList[ShaderProgram] = ResList()
    progList.load(inb, pos, ShaderProgram)

    pos += progList.size

    codeList: ResList[ShaderCode] = ResList()
    codeList.load(inb, pos, ShaderCode)

    pos += codeList.size
    assert pos == base_pos + header.fileSize

    return header, progList, codeList


def save(header: Header, progList: ResList[ShaderProgram], codeList: ResList[ShaderCode]) -> bytearray:
    global curr_version
    curr_version = header.version

    outBuffer = bytearray(b''.join([
        header.save(),
        progList.save(),
        codeList.save(),
    ]))

    outBuffer[8:12] = struct.pack('%sI' % header.endianness, len(outBuffer))
    return outBuffer

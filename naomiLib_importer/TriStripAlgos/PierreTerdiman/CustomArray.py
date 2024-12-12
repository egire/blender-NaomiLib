import os
import struct

class CustomCell:
    def __init__(self, max_size):
        self.Item = {
            'Addy': bytearray(max_size),
            'Size': 0,
            'Max': max_size
        }
        self.NextCustomCell = None

class CustomArray:
    def __init__(self, startsize=1024, inputbuffer=None):
        self.mNbPushedAddies = 0
        self.mNbAllocatedAddies = 0
        self.mBitCount = 0
        self.mBitMask = 0
        self.mAddresses = []
        self.mCollapsed = None

        self.NewBlock(None, startsize)
        self.mInitCell = self.mCurrentCell

        if inputbuffer:
            self.mCurrentCell.Item['Addy'][:startsize] = inputbuffer

        self.mLastAddress = self.mCurrentCell.Item['Addy']

    def __del__(self):
        self.mCollapsed = None
        self.mAddresses = None

        cur_cell = self.mInitCell
        while cur_cell:
            cell = cur_cell
            cur_cell = cur_cell.NextCustomCell
            del cell

    def NewBlock(self, previouscell, size):
        cell = CustomCell(size if previouscell is None else previouscell.Item['Max'] * 2)
        self.mCurrentCell = cell

        if previouscell:
            previouscell.NextCustomCell = self.mCurrentCell

        return self

    def CheckArray(self, bytesneeded):
        expected_size = self.mCurrentCell.Item['Size'] + bytesneeded
        if expected_size > self.mCurrentCell.Item['Max']:
            self.NewBlock(self.mCurrentCell, 0)
        return self

    def ExportToDisk(self, filename):
        with open(filename, 'wb') as fp:
            return self.ExportToDiskFile(fp)

    def ExportToDiskFile(self, fp):
        self.EndBits()
        p = self.mInitCell

        while p.NextCustomCell:
            if not self.SaveCell(p, fp):
                return False
            p = p.NextCustomCell

        if not self.SaveCell(p, fp):
            return False

        return True

    def SaveCell(self, p, fp):
        bytes_to_write = p.Item['Size']
        if bytes_to_write == 0:
            return True
        if fp.write(p.Item['Addy'][:bytes_to_write]) != bytes_to_write:
            return False
        return True

    def GetOffset(self):
        offset = 0
        p = self.mInitCell

        while p.NextCustomCell:
            offset += p.Item['Size']
            p = p.NextCustomCell

        offset += p.Item['Size']
        return offset

    def Padd(self):
        self.EndBits()
        offset = self.GetOffset()
        nb_padd = offset - (offset & 7)
        for _ in range(nb_padd):
            self.Store(0)
        return self

    def Collapse(self, userbuffer=None):
        self.EndBits()
        p = self.mInitCell

        if userbuffer is None:
            self.mCollapsed = bytearray(self.GetOffset())
            addy = self.mCollapsed
        else:
            addy = userbuffer

        addy_copy = addy
        if addy:
            while p.NextCustomCell:
                addy[:p.Item['Size']] = p.Item['Addy'][:p.Item['Size']]
                addy = addy[p.Item['Size']:]
                p = p.NextCustomCell

            addy[:p.Item['Size']] = p.Item['Addy'][:p.Item['Size']]
            self.mNbPushedAddies = 0

        return addy_copy

    def Store(self, value):
        self.EndBits()
        if isinstance(value, bool):
            value = 1 if value else 0
        elif isinstance(value, int):
            value = value.to_bytes(4, byteorder='little', signed=True)
        elif isinstance(value, float):
            value = bytearray(struct.pack("f", value))
        elif isinstance(value, str):
            value = value.encode('utf-8')
        else:
            value = bytearray(value)

        self.CheckArray(len(value))
        self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']:self.mCurrentCell.Item['Size'] + len(value)] = value
        self.mLastAddress = self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']:self.mCurrentCell.Item['Size'] + len(value)]
        self.mCurrentCell.Item['Size'] += len(value)
        return self

    def StoreBit(self, bit):
        self.mBitMask <<= 1
        if bit:
            self.mBitMask |= 1
        self.mBitCount += 1
        if self.mBitCount == 8:
            self.mBitCount = 0
            self.Store(self.mBitMask)
            self.mBitMask = 0
        return self

    def EndBits(self):
        while self.mBitCount:
            self.StoreBit(False)
        return self

    def PushAddress(self):
        if (self.mNbPushedAddies + 1) > self.mNbAllocatedAddies:
            new_size = self.mNbAllocatedAddies * 2 if self.mNbAllocatedAddies else 1
            self.mAddresses.extend([None] * (new_size - len(self.mAddresses)))
            self.mNbAllocatedAddies = new_size

        self.mAddresses[self.mNbPushedAddies] = self.mLastAddress
        self.mNbPushedAddies += 1
        return True

    def PopAddressAndStore(self, value):
        if self.mNbPushedAddies:
            addy = self.mAddresses[self.mNbPushedAddies - 1]
            self.mNbPushedAddies -= 1
            if isinstance(value, bool):
                value = 1 if value else 0
            addy[:len(value)] = value
        return self

    def GetByte(self):
        current_addy = self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']]
        self.mLastAddress = current_addy
        self.mCurrentCell.Item['Size'] += 1
        return current_addy

    def GetWord(self):
        current_addy = self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']:self.mCurrentCell.Item['Size'] + 2]
        self.mLastAddress = current_addy
        self.mCurrentCell.Item['Size'] += 2
        return int.from_bytes(current_addy, byteorder='little', signed=True)

    def GetDword(self):
        current_addy = self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']:self.mCurrentCell.Item['Size'] + 4]
        self.mLastAddress = current_addy
        self.mCurrentCell.Item['Size'] += 4
        return int.from_bytes(current_addy, byteorder='little', signed=True)

    def GetFloat(self):
        current_addy = self.mCurrentCell.Item['Addy'][self.mCurrentCell.Item['Size']:self.mCurrentCell.Item['Size'] + 4]
        self.mLastAddress = current_addy
        self.mCurrentCell.Item['Size'] += 4
        return struct.unpack('f', current_addy)[0]

    @staticmethod
    def FileSize(name):
        return os.path.getsize(name) if os.path.exists(name) else 0

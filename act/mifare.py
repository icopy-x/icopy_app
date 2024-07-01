# -*- coding: UTF-8 -*-

# Tag contains 16 sectors, each with 4 blocks.
import re

# Tag contains 16 sectors, each with 4 blocks.
SIZE_1K = 1024
SECTOR_1K = 16
BLOCK_1K = 64

# Tag contains 32 sectors, each with 4 blocks.
SIZE_2K = 2048
SECTOR_2K = 32
BLOCK_2K = 128

#
# Tag contains 40 sectors. The first 32 sectors contain 4 blocks and the last 8 sectors
# contain 16 blocks.
#
SIZE_4K = 4096
SECTOR_4K = 40
BLOCK_4K = 256

# Tag contains 5 sectors, each with 4 blocks.
SIZE_MINI = 320
SECTOR_Mini = 5
BLOCK_Mini = 20

# Size of a MIFARE Classic block (in bytes) 
BLOCK_SIZE = 16

# count of block max
MAX_BLOCK_COUNT = 256
MAX_SECTOR_COUNT = 40

# 表示秘钥A
A = "A"
# 表示秘钥B
B = "B"
# 表示秘钥AB两者
AB = "AB"

EMPTY_KEY = "FFFFFFFFFFFF"
# 表示空的数据
EMPTY_DATA = "00000000000000000000000000000000"
# 表示空的尾部块
EMPTY_TRAI = f"{EMPTY_KEY}FF078069{EMPTY_KEY}"


def validateSector(sector):
    # Do not be too strict on upper bounds checking, since some cards
    # have more addressable memory than they report. For example,
    # MIFARE Plus 2k cards will appear as MIFARE Classic 1k cards when in
    # MIFARE Classic compatibility mode.
    # Note that issuing a command to an out-of-bounds block is safe - the
    # tag should report error causing IOException. This validation is a
    # helper to guard against obvious programming mistakes.
    NR_TRAILERS_4k = 40
    sector = int(sector)
    if sector < 0 or sector >= NR_TRAILERS_4k:
        return False
    return True


def validateBlock(block):
    block = int(block)
    # Just looking for obvious out of bounds...
    NR_BLOCKS_4k = 0xFF
    if block < 0 or block >= NR_BLOCKS_4k: return False
    return True


def validateValueOperand(value):
    value = int(value)
    if value < 0:
        return False
    return True


def blockToSector(blockIndex):
    blockIndex = int(blockIndex)
    if not validateBlock(blockIndex): return 0
    if blockIndex < 32 * 4:
        return int(blockIndex / 4)
    else:
        return int(32 + (blockIndex - 32 * 4) / 16)


def sectorToBlock(sectorIndex):
    sectorIndex = int(sectorIndex)
    if not validateSector(sectorIndex): return -1
    if sectorIndex < 32:
        return int(sectorIndex * 4)
    else:
        return int(32 * 4 + (sectorIndex - 32) * 16)


def isFirstBlock(uiBlock):
    # 测试我们是否处于小扇区或者大扇区？
    if uiBlock < 128:
        return uiBlock % 4 == 0
    else:
        return uiBlock % 16 == 0


def isTrailerBlock(uiBlock):
    # 测试我们处于小区块还是大扇区
    if uiBlock < 128:
        return (uiBlock + 1) % 4 == 0
    else:
        return (uiBlock + 1) % 16 == 0


def isBlockData(data):
    return re.match(r"^[a-fA-F0-9]{32}$", data) is not None


def getBlockCountInSector(sectorIndex):
    if not validateSector(sectorIndex): return -1
    if sectorIndex < 32:
        return 4
    else:
        return 16


def get_trailer_block(uiFirstBlock):
    # Test if we are in the small or big sectors
    if uiFirstBlock < 128:
        trailer_block = uiFirstBlock + (3 - (uiFirstBlock % 4))
    else:
        trailer_block = uiFirstBlock + (15 - (uiFirstBlock % 16))
    return int(trailer_block)


def getIndexOnSector(block, sector):
    index = 0
    count = getBlockCountInSector(sector)
    # 得到当前的块在扇区中的具体索引!
    for i in range(0, count):
        if block == (sectorToBlock(block) + i): break
        index += 1
    return index


def getSectorCount(size):
    if size == SIZE_1K:
        # 64 blocks, last block is 63
        return SECTOR_1K
    if size == SIZE_2K:
        # 128 blocks, last block is 127
        return SECTOR_2K
    if size == SIZE_4K:
        # 256 blocks, last block is 255
        return SECTOR_4K
    if size == SIZE_MINI:
        # 5 blocks, last block is 4
        return SECTOR_Mini
    return 0


def getKeyCount(size):
    if size == SIZE_1K:
        # 64 blocks, last block is 63
        return SECTOR_1K * 2
    if size == SIZE_2K:
        # 128 blocks, last block is 127
        return SECTOR_2K * 2
    if size == SIZE_4K:
        # 256 blocks, last block is 255
        return SECTOR_4K * 2
    if size == SIZE_MINI:
        # 5 blocks, last block is 4
        return SECTOR_Mini * 2
    return 0

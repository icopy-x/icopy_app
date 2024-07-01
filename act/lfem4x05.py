# -*- coding: UTF-8 -*-
import re

import appfiles
import executor

CMD = "lf em 4x05_info FFFFFFFF"
TIMEOUT = 5000
KEY_TEMP = None
DUMP_TEMP = None


def parser():
    if not executor.isEmptyContent() and executor.hasKeyword("Chip Type"):
        return {
            "found": True,
            "type": 24,
            "chip": executor.getContentFromRegexG(r".*Chip Type.*\|(.*)", 1).replace(" ", ""),
            "sn": executor.getContentFromRegexG(r".*Serial.*:(.*)", 1).replace("0x", "", 1).replace(" ", ""),
            "cw": executor.getContentFromRegexG(r".*ConfigWord:(.*)\(.*", 1).replace(" ", "")
        }
    return {"found": False}


def info4X05(key=None):
    """读取4X05系列的卡片信息"""
    cmd = "lf em 4x05_info"
    if key is not None and isinstance(key, str):
        cmd += " {}".format(key)
    # 最大重试两次
    for i in range(0, 2):
        # 没有密码，直接dump
        if executor.startPM3Task(cmd, TIMEOUT) == -1:
            return -2
        # dump成功，回调并且返回
        if executor.hasKeyword("ConfigWord"):
            return 1
    return -8


def set_key(key):
    """
        设置EM4X05将被使用的密钥
    :param key:
    :return:
    """
    global KEY_TEMP
    KEY_TEMP = key


def dump4X05(infos, key=None):
    """读取4X05系列的卡片数据"""
    cmd = "lf em 4x05_dump"

    appfiles.switch_linux()
    file = appfiles.create_em4x05(infos["sn"])
    appfiles.switch_current()

    global DUMP_TEMP
    DUMP_TEMP = file + ".bin"

    cmd += " f {}".format(file)
    if key is not None and isinstance(key, str):
        cmd += " {}".format(key)

    # 最大重试两次
    for i in range(0, 2):
        # 没有密码，直接dump
        if executor.startPM3Task(cmd, TIMEOUT) == -1:
            return -2
        # dump成功，回调并且返回
        kw = "saved 64 bytes to binary file"
        if executor.hasKeyword(kw):
            # 获得文件名
            DUMP_TEMP = executor.getContentFromRegexG(r"{} (.*)".format(kw), 1)
            print("读取到的EM4X05的DUMP文件: ", DUMP_TEMP)
            return 1

    return -2


def read4x05(block, key=None):
    """
        读取em4x05的块
    :param block:
    :param key:
    :return:
    """
    if key is None:
        key = ""
    cmd = "lf em 4x05_read {} {}".format(block, key)

    for count in range(2):

        if executor.startPM3Task(cmd, TIMEOUT) == -1:
            return -2

        ret = executor.getContentFromRegexG(r"\| ([a-fA-F0-9]+) -", 1)

        print(ret)

        if len(ret) != 0:
            return ret

    return None


def readBlocks(key=None):
    """
        读取所有的秘钥
    :param key:
    :return:
    """
    ret = ""

    for block in range(16):
        b_str = read4x05(block, key)

        if b_str is None:
            if block != 2:
                return None
            elif block == 2 and key is not None:
                b_str = key
            else:
                b_str = "00000000"

        ret += b_str

    return ret.upper()


def verify4x05(data1, data2):
    """
        校验4x05的数据
    :param data1:
    :param data2:
    :return:
    """

    try:
        d1_g = re.findall(r".{8}", str(data1).upper())
        d2_g = re.findall(r".{8}", str(data2).upper())

        # 先校验0块
        if d1_g[0] != d2_g[0]:
            return False

        # 然后校验第03块
        if d1_g[3] != d2_g[3]:
            return False

        # 然后校验 5 - 13
        for block in range(4, 14):
            if d1_g[block] != d2_g[block]:
                return False
    except Exception as e:
        print("校验失败: ", e)
        return False

    # 此时所有的可读写的块都已经校验完毕，结果正确
    return True


def infoAndDumpEM4x05ByKey(key):
    """读取4X05系列的卡片，使用自定义的秘钥"""
    ret = info4X05(key)
    if ret == 1:
        infos = parser()
        return dump4X05(infos, key)
    return ret


if __name__ == '__main__':
    print("读取出来的数据: ", readBlocks("AFAFAFAF"))

# -*- coding: UTF-8 -*-
import appfiles
import tagtypes
import executor
import hficlass

KEY_READ = None
FILE_READ = None


def readFromKey(infos, key, typ):
    """
        读取iclass legacy卡片
    :return:
    """
    if typ == "e":
        name = "Elite"
    else:
        name = "Legacy"
    appfiles.switch_linux()
    file = appfiles.create_iclass(name, infos["csn"])
    appfiles.switch_current()
    cmd = "hf iclass dump k " + key + " f " + file + " " + typ
    timeout = 8888

    if executor.startPM3Task(cmd, timeout) == -1:
        return -2

    if executor.hasKeyword("saving dump file - 19 blocks read"):
        global KEY_READ, FILE_READ
        KEY_READ = key
        FILE_READ = file
        return 1

    return -2


def readLegacy(infos):
    """
        读取iclass legacy卡片
    :return:
    """
    if "key" in infos and infos["key"] is not None and len(infos["key"]) > 0:
        key = infos["key"]
    else:
        key = "AFA785A7DAB33378"
    return readFromKey(infos, key, "")


def readElite(infos):
    """
        读取Elite卡片
    :return:
    """

    if "key" in infos and infos["key"] is not None and len(infos["key"]) > 0:
        key = infos["key"]
    else:  # 加速读取，不需要重复获取秘钥
        key = hficlass.chkKeys(infos)

    if key is not None:
        if isinstance(key, tuple):
            key = key[1]
        return readFromKey(infos, key, "e")

    return -2


def read(infos):
    """
        读取指定类型的iclass
    :param infos: 类型
    :return:
    """
    typ = infos["type"]
    if typ == tagtypes.ICLASS_LEGACY:
        return readLegacy(infos)
    else:
        return readElite(infos)

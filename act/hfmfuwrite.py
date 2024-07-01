# -*- coding: UTF-8 -*-
import executor
import scan
import tagtypes


def write_call(line):
    if executor.hasKeyword(r"Can't select card", line):
        print("MFU选卡失败，自动判定为失败")
        executor.stopPM3Task(wait=False)
    print(line)


def write(infos, file):
    """
        写入卡片
    :return:
    """

    typ = infos["type"]
    #
    # ULTRALIGHT,
    # ULTRALIGHT_C,
    # ULTRALIGHT_EV1,
    # NTAG213_144B,
    # NTAG215_504B,
    # NTAG216_888B
    #
    if typ == tagtypes.ULTRALIGHT:
        # 函数执行时间: 3.5898630000000002 秒
        # 我们需要实际上给出超过一定的时长的超时值
        timeout = 10888
    elif typ == tagtypes.ULTRALIGHT_C:
        timeout = 13888
    elif typ == tagtypes.ULTRALIGHT_EV1:
        timeout = 16888
    elif typ == tagtypes.NTAG213_144B:
        timeout = 18888
    elif typ == tagtypes.NTAG215_504B:
        timeout = 38888
    elif typ == tagtypes.NTAG216_888B:
        timeout = 98888
    else:
        timeout = 8888

    # 追加文件的后缀
    if not str(file).endswith(".bin"):
        file += ".bin"

    # hf mfu restore s e f {NTAG213-0497.bin}
    cmd = "hf mfu restore s e f {}".format(file)
    if executor.startPM3Task(cmd, timeout, write_call) == -1:
        return -10
    if executor.hasKeyword(r"Can't select card"):
        return -10
    if executor.hasKeyword(r"failed to write block"):
        return -10

    return 1


def verify(infos, file=None):
    """
        校验
    :param file:
    :param infos:
    :return:
    """
    # 搜索卡片，仅仅校验卡的类型和UID
    uid = infos["uid"]
    typ = infos["type"]

    new_infos = scan.scan_14a()
    if scan.isTagFound(new_infos):
        return typ == new_infos["type"] and uid == new_infos["uid"]
    return -1

# -*- coding: UTF-8 -*-
import appfiles
import executor

CMD = "hf 15 dump"
TIMEOUT = 38000

FILE_READ = None


def read(infos):
    """
        读取 ISO15693 ICODE的标签
    :return:
    """
    appfiles.switch_linux()
    global FILE_READ
    FILE_READ = appfiles.create_icode(infos["uid"])
    cmd = "{} f {}".format(CMD, FILE_READ)
    appfiles.switch_current()

    if executor.startPM3Task(cmd, TIMEOUT) == -1:
        return -2

    print("读取结果: ", executor.CONTENT_OUT_IN__TXT_CACHE)

    if executor.hasKeyword("No tag found."):
        return -2

    # saved 224 bytes to binary file /mnt/upan/dump/icode/ICODE_E00222D66D1015EB_10.bin
    if executor.hasKeyword("saved [0-9]+ bytes to binary file"):  # 兼容所有的容量
        return 1

    return -2

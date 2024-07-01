# -*- coding: UTF-8 -*-
import appfiles
import executor

CMD = "hf legic dump"
TIMEOUT = 5000


def read(infos):
    """
        读取 legic mini256的标签
    :return:
    """
    name = "{}-{}".format(infos["mcd"], infos["msn"])
    appfiles.switch_linux()
    name = appfiles.create_legic(name)
    appfiles.switch_current()
    cmd = "{} f {}".format(CMD, name)

    if executor.startPM3Task(cmd, TIMEOUT) == -1:
        return -2

    if executor.hasKeyword("Failed to identify tagtype"):
        return -2

    # MIM22, MIM256, MIM1024
    b = "saved {} bytes to binary"
    b2 = b.format(256)
    b3 = b.format(1024)
    if executor.hasKeyword(b2) or executor.hasKeyword(b3):
        return 1

    return -2


if __name__ == '__main__':
    executor.startPM3Task("hf legic dump h", TIMEOUT)

# -*- coding: UTF-8 -*-
import appfiles
import executor

CMD = "hf felica litedump"
TIMEOUT = 5000


def read(infos):
    """
        读取 ISO15693 ICODE的标签
    :return:
    """
    file = appfiles.create_felica(infos["idm"])

    if executor.startPM3Task(CMD, TIMEOUT) == -1:
        return -2

    # State:
    # Polling disabled:
    # Authenticated:
    b1 = executor.hasKeyword("State:")
    b2 = executor.hasKeyword("Polling disabled:")
    b3 = executor.hasKeyword("Authenticated:")

    if b1 and b2 and b3:
        if appfiles.save2any(executor.getPrintContent(), file):
            return 1

    return -2

# -*- coding: UTF-8 -*-
import executor

CMD = "hf felica reader"
TIMEOUT = 10000


def parser():
    """
        解析菲莉卡的寻卡结果
    :return:
    """
    b1 = executor.hasKeyword("card timeout")
    b2 = executor.hasKeyword("CRC check failed")
    if b1 or b2 or not executor.hasKeyword("FeliCa tag info"):
        return {"found": False}

    return {
        "found": True,
        "idm": executor.getContentFromRegexG(r".*IDm(.*)", 1).replace(" ", ""),
        "type": 21,
    }

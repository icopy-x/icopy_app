# -*- coding: UTF-8 -*-
import executor
import tagtypes

CMD = "hf mfu info"
TIMEOUT = 8888


def getUID():
    """
        截取UID
    """
    return executor.getContentFromRegexG(r".*UID:(.*)\n", 1).replace(" ", "")


def parser():
    """
        解析hf mfu info的信息
    """
    if (not executor.hasKeyword("Tag Information") or
            not executor.hasKeyword("TYPE:") or
            not executor.hasKeyword("UID:")):
        return {"found": False}
    map = {
        "uid": getUID(),
        "found": True,
        "isMFU": True
    }
    if executor.hasKeyword("MF0ICU1") or executor.hasKeyword("TYPE: Unknown"):
        map["type"] = tagtypes.ULTRALIGHT
    elif executor.hasKeyword("MF0ULC"):
        map["type"] = tagtypes.ULTRALIGHT_C
    elif executor.hasKeyword("MF0UL1101"):
        map["type"] = tagtypes.ULTRALIGHT_EV1
    elif executor.hasKeyword("NTAG 213"):
        map["type"] = tagtypes.NTAG213_144B
    elif executor.hasKeyword("NTAG 215"):
        map["type"] = tagtypes.NTAG215_504B
    elif executor.hasKeyword("NTAG 216"):
        map["type"] = tagtypes.NTAG216_888B
    else:
        map["type"] = -1
        map["found"] = False
        del map["isMFU"]
    return map

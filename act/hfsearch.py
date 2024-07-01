# -*- coding: UTF-8 -*-
import hffelica
import executor

CMD = "hf sea"
TIMEOUT = 10000


def parser():
    if executor.hasKeyword("No known/supported 13.56 MHz tags found"):
        return {"found": False}
    elif executor.hasKeyword("Valid iCLASS tag"):
        return {"found": True, "isIclass": True}
    elif executor.hasKeyword("Valid ISO15693"):
        if executor.hasKeyword("ST Microelectronics SA France"):
            typ = 46
        else:
            typ = 19
        return {
            "found": True,
            "uid": executor.getContentFromRegexG(r".*UID:\s(.*)", 1).replace(" ", ""),
            "type": typ,
        }
    elif executor.hasKeyword("Valid LEGIC Prime"):
        return {
            "found": True,
            "mcd": executor.getContentFromRegexG(r".*MCD:\s(.*)", 1).replace(" ", ""),
            "msn": executor.getContentFromRegexG(r".*MSN:\s(.*)", 1).replace(" ", ""),
            "type": 20,
        }
    elif executor.hasKeyword("Valid ISO18092 / FeliCa"):
        return hffelica.parser()
    elif executor.hasKeyword("Valid ISO14443-B"):
        return {
            "found": True,
            "uid": executor.getContentFromRegexG(r".*UID.*:(.*)", 1).replace(" ", ""),
            "atqb": executor.getContentFromRegexG(r".*ATQB.*:(.*)", 1).replace(" ", ""),
            "type": 22,
        }
    elif executor.hasKeyword("MIFARE"):
        return {"found": True, "isMifare": True}
    elif executor.hasKeyword("Valid Topaz"):
        return {
            "found": True,
            "uid": executor.getContentFromRegexG(r".*UID.*:(.*)", 1).replace(" ", ""),
            "atqa": executor.getContentFromRegexG(r".*ATQA.*:(.*)", 1).replace(" ", ""),
            "type": 27,
        }
    return {"found": False}

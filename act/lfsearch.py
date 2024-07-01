# -*- coding: UTF-8 -*-
import tagtypes
import executor
import re

CMD = "lf sea"
TIMEOUT = 10000
COUNT = 0

# 通用的RAW截取正则
REGEX_RAW = r".*(?:Raw|Raw|RAW|hex|HEX|Hex)\s*:*\s*([xX0-9a-fA-F ]+)"
# 通用卡片ID获取
REGEX_CARD_ID = r"(?:Card|ID|id|CARD|ID|UID|uid|Uid)\s*:*\s*([xX0-9a-fA-F ]+)"

# EM410X的截取正则
REGEX_EM410X = r"EM TAG ID\s+:[\s]+([xX0-9a-fA-F]+)"
# HID的正则截取
REGEX_HID = r"HID Prox - ([xX0-9a-fA-F]+)"
# IO Prox ID的正则截取
REGEX_PROX_ID_XSF = r"(XSF\(.*?\).*?:[xX0-9a-fA-F]+)"
# REGEX_PROX_ID = r".*\(([xX0-9a-fA-F]+)\).*"
# 动物标签的ID正则截取
REGEX_ANIMAL = r".*ID\s+([xX0-9A-Fa-f\-]{2,})"


def cleanHexStr(hexStr):
    """
        整理为纯HEX字符串
    """
    if hexStr is None:
        hexStr = ""

    if hexStr.startswith("0x"):
        hexStr = hexStr.lstrip("0x")

    if hexStr.startswith("0X"):
        hexStr = hexStr.lstrip("0X")

    return re.sub(r"\s", "", hexStr)


def cleanAndSetRaw(map_dict, raw):
    """
        整理和设置RAW内容到表里面
    """
    map_dict["raw"] = cleanHexStr(raw)


def setUID(map_dict, regex=REGEX_CARD_ID, group=0):
    """
        整理和根据表达式设置UID内容到表里面
    """
    uids = executor.getContentFromRegexA(regex)
    if len(uids) > 0 and group < len(uids):
        uid = uids[group]
    else:
        uid = ""
    map_dict["data"] = cleanHexStr(uid)


def setUID2FCCN(map_dict):
    """
        自动截取FCCN设置到UID项里
    """
    map_dict["data"] = getFCCN()
    # 分别截取其他的信息
    map_dict["fc"] = parseFC()
    map_dict["cn"] = parseCN()
    map_dict["len"] = parseLen()


def setUID2Raw(map_dict):
    """
        将UID复制到RAW里面存放
    """
    map_dict["raw"] = map_dict["data"]


def setRAWForRegex(map_dict, regex, group):
    """
        设置RAW，根据表达式
    """
    seaObj = re.search(regex, executor.CONTENT_OUT_IN__TXT_CACHE, re.I)
    if seaObj is not None:
        uid = seaObj.group(group)
        cleanAndSetRaw(map_dict, uid)
    else:
        cleanAndSetRaw(map_dict, "")


def setRAW(map_dict):
    """
        设置RAW到内容中
    """
    setRAWForRegex(map_dict, REGEX_RAW, 1)


def parseFC():
    """解析FC"""
    fc = executor.getContentFromRegexG(r"FC:*\s+([xX0-9a-fA-F]+)", 1)
    return cleanHexStr(fc)


def parseCN():
    """解析Card Num"""
    cn = executor.getContentFromRegexG(r"(CN|Card|Card ID):*\s+(\d+)", 2)
    return cleanHexStr(cn)


def parseLen():
    """
        解析len
    :return:
    """
    # len: 26
    cn = executor.getContentFromRegexG(r"(len|Len|LEN|format|Format):*\s+(\d+)", 2)
    return cleanHexStr(cn)


def hasFCCN():
    """
        有没有FCCN
    :return:
    """
    fc = parseFC()
    cn = parseCN()
    # 判断FCCN数据是否有效
    try:
        return len(fc) != 0 or len(cn) != 0
    except:
        pass

    return False


def getFCCN():
    """
        自动解析并且生成FCCN
    """
    fc = parseFC()
    cn = parseCN()

    fill_char = "X"

    # 判断是否太短，太短就补零
    try:
        fc = "{:0>3d}".format(int(fc))
    except Exception:
        fc = fill_char

    try:
        cn = "{:0>5d}".format(int(cn))
    except Exception:
        cn = fill_char

    return "FC,CN: {},{}".format(fc, cn)


def getXsf():
    """获取某些卡片的xsf信息"""
    xsf = executor.getContentFromRegexG(REGEX_PROX_ID_XSF, 1)
    if len(xsf) == 0:
        return None
    return xsf


def parser():
    """
        解析低频的卡片信息
    """
    if executor.hasKeyword("No data found!"):
        return {"found": False}
    ret = {}

    # 截取可能存在的 Chipset detection
    if executor.hasKeyword("Chipset detection"):
        chipset = executor.getContentFromRegexG(r"Chipset detection:\s(.*)", 1)
        chipset = chipset.replace(" ", "").replace("\r", "")
        if len(chipset) > 0:  # 截取到了有效的数据，保存到结果集中
            if "EM" in chipset:
                ret["chipset"] = "EM4305"
            elif "T5" in chipset:
                ret["chipset"] = "T5577"
            else:
                ret["chipset"] = "X"

    typ = -1
    if executor.hasKeyword("Valid EM410x ID"):
        typ = tagtypes.EM410X_ID
        setUID(ret, REGEX_EM410X)
        setUID2Raw(ret)
    elif executor.hasKeyword("Valid HID Prox ID"):
        typ = tagtypes.HID_PROX_ID
        setUID(ret, REGEX_HID)
        setUID2Raw(ret)
    elif executor.hasKeyword("Valid Indala ID"):
        typ = tagtypes.INDALA_ID
        setRAW(ret)
        # 判断是否需要取出FCCN来显示
        if hasFCCN():
            fccn = getFCCN()
        else:
            fccn = None
        if fccn is not None:
            ret["data"] = fccn
        else:
            ret["data"] = ret["raw"]
    elif executor.hasKeyword("Valid AWID ID"):
        typ = tagtypes.AWID_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid IO Prox ID"):
        typ = tagtypes.IO_PROX_ID
        ret["data"] = getXsf()
        setRAWForRegex(ret, REGEX_RAW, 1)
    elif executor.hasKeyword("Valid Guardall G-Prox II ID"):
        typ = tagtypes.GPROX_II_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Securakey ID"):
        typ = tagtypes.SECURAKEY_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Viking ID"):
        typ = tagtypes.VIKING_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Pyramid ID"):
        typ = tagtypes.PYRAMID_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid FDX-B ID"):
        typ = tagtypes.FDXB_ID
        setUID(ret, REGEX_ANIMAL)
        setUID2Raw(ret)
    elif executor.hasKeyword("Valid GALLAGHER ID"):
        typ = tagtypes.GALLAGHER_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Jablotron ID"):
        typ = tagtypes.JABLOTRON_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid KERI ID"):
        typ = tagtypes.KERI_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid NEDAP ID"):
        typ = tagtypes.NEDAP_ID
        setUID(ret)
        setRAW(ret)
        # 截取特有的NEDAP信息
        ret["subtype"] = executor.getContentFromRegexG(r"subtype:*\s+(\d+)", 1)
        ret["code"] = executor.getContentFromRegexG(r"customer code:*\s+(\d+)", 1)
    elif executor.hasKeyword("Valid Noralsy ID"):
        typ = tagtypes.NORALSY_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid PAC/Stanley ID"):
        typ = tagtypes.PAC_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Paradox ID"):
        typ = tagtypes.PARADOX_ID
        setUID2FCCN(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Presco ID"):
        typ = tagtypes.PRESCO_ID
        setUID(ret)
    elif executor.hasKeyword("Valid Visa2000 ID"):
        typ = tagtypes.VISA2000_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Valid Hitag"):
        typ = tagtypes.HITAG2_ID
        setUID(ret)
    elif executor.hasKeyword("Valid NexWatch ID"):
        typ = tagtypes.NEXWATCH_ID
        setUID(ret)
        setRAW(ret)
    elif executor.hasKeyword("Chipset detection: EM4x05 / EM4x69"):
        return {"found": True, "is4xXX": True}
    # 发现了一些疑似t55xx的卡片，需要去验证一下
    elif executor.hasKeyword("No known 125/134 kHz tags found!"):
        return {"found": True, "isT55XX": True}

    if typ != -1:
        ret["type"] = typ
        ret["found"] = True
    else:
        ret["found"] = False

    return ret

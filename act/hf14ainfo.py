# -*- coding: UTF-8 -*-
import tagtypes
import executor

CMD = "hf 14a info"
TIMEOUT = 5000


def has_static_nonce():
    """
        是否有静态的随机数
    :return:
    """
    b1 = executor.hasKeyword("Static nonce: yes")
    b2 = executor.hasKeyword("static nonce")
    return b1 or b2


def has_prng_level():
    """
        判断是否有随机数漏洞
    :return:
    """
    if executor.hasKeyword("Prng detection"):
        level = executor.getContentFromRegexG(r".*Prng detection: (.*)\n", 1).replace(" ", "")
        return level != "fail"
    return False


def is_gen1a_magic():
    if executor.hasKeyword("Magic capabilities : Gen 1a"):
        return True
    infos_cache = executor.getPrintContent()
    cmd = "hf mf cgetblk 0"
    if executor.startPM3Task(cmd, 5888) == -1:
        return False
    ret = executor.hasKeyword("data:")
    # 我们需要恢复查询的14a信息
    executor.CONTENT_OUT_IN__TXT_CACHE = infos_cache
    return ret


def parser():
    """
        解析指令的输出
    """

    # 没有卡片应答内容，说明没有发现14A协议的卡片，直接跳过
    if executor.isEmptyContent():
        return {"found": False}

    # 输出为空或者如果发现了非标准的14433-3卡片的错误消息，直接跳过
    if executor.hasKeyword("Card doesn't support standard iso14443-3 anticollision"):
        return {"found": False}

    # 如果发现了多张卡片重叠，则返回错误
    if executor.hasKeyword("Multiple tags detected"):
        return {"found": True, "hasMulti": True}

    # 如果是UL卡，则直接返回
    isUL = (executor.hasKeyword("MIFARE Ultralight")
            | executor.hasKeyword("NTAG") and not executor.hasKeyword("MIFARE DESFire"))

    # 如果发现卡片但是出现了校验位异常
    bbcErr = executor.hasKeyword("BCC0 incorrect")

    b_prng = has_prng_level()
    b_static = has_static_nonce()
    b_gen1a = is_gen1a_magic()

    # UL卡没有随机数生成器，更没有随机数漏洞
    if not b_prng and not b_static and isUL:
        return {"found": True, "isUL": True}

    if bbcErr:
        uid = "BCC0 incorrect"
        uid_len = 0
        sak = 'no'
        atqa = 'no'
        ats = ''
    else:
        uid = executor.getContentFromRegexG(r".*UID:(.*)\n", 1).replace(" ", "")
        uid_len = 0 if len(uid) < 8 else int(len(uid) / 2)
        sak = executor.getContentFromRegexG(r".*SAK:(.*)\[.*\n", 1).replace(" ", "")
        atqa = executor.getContentFromRegexG(r".*ATQA:(.*)\n", 1).replace(" ", "")
        ats = executor.getContentFromRegexG(r".*ATS:(.*)", 1).replace(" ", "")

    # 初始化一个表，存放基本信息
    map_ret = {
        "found": True,
        "uid": uid,
        "len": uid_len,
        "sak": sak,
        "atqa": atqa,
        "bbcErr": bbcErr,
    }

    if len(ats) > 0:
        map_ret["ats"] = ats

    # 先判断基本的类型
    is_mifare = (
            b_prng or
            b_static or
            b_gen1a or
            executor.hasKeyword("MIFARE Classic") or
            executor.hasKeyword("MIFARE Plus")
    )
    if is_mifare:
        # 是否有静态随机数
        map_ret["static"] = b_static
        # 是否是UID后门卡
        map_ret["gen1a"] = b_gen1a

        if executor.hasKeyword("MIFARE Mini"):
            typ = tagtypes.M1_MINI
        elif executor.hasKeyword("MIFARE Classic 4K") or executor.hasKeyword("MIFARE Plus 4K"):
            typ = tagtypes.M1_S70_4K_4B
        elif executor.hasKeyword("MIFARE Classic 1K") or executor.hasKeyword("Magic capabilities : Gen 2 / CUID"):
            typ = tagtypes.M1_S50_1K_4B
        else:
            # 当我们发现了M1卡的特征但是又没有相关类型信息打印的时候
            # 我们可以指定为 M1_POSSIBLE_*
            typ = tagtypes.M1_POSSIBLE_4B

    elif executor.hasKeyword("MIFARE DESFire"):
        # 发现了类似DESFIRE的卡片，默认归类到DESFIRE里面
        typ = tagtypes.MIFARE_DESFIRE
    else:
        # 发现了卡片但是没有任何一个类型能匹配上，默认归类到14A大类型
        typ = tagtypes.HF14A_OTHER

    map_ret["type"] = typ

    # 当前如果是M1经典系列的卡片
    if typ in tagtypes.getM1Types():

        # 类型纠正，只有类型是M1确定类型时才自动纠正
        if map_ret["len"] == 7:
            # 自动纠正14为17
            if typ == tagtypes.M1_S50_1K_4B:
                map_ret["type"] = tagtypes.M1_S50_1K_7B

            # 自动纠正44为47
            if typ == tagtypes.M1_S70_4K_4B:
                map_ret["type"] = tagtypes.M1_S70_4K_7B

            # 自动纠正P4为P7
            if typ == tagtypes.M1_POSSIBLE_4B:
                map_ret["type"] = tagtypes.M1_POSSIBLE_7B

        # 只能算是可能是M1卡，但是不确定类型信息，
        # 所以需要截取厂商信息用于标志唯一的类型。
        manufacturer = executor.getContentFromRegexG(r".*MANUFACTURER:(.*)", 1).strip()
        if typ == tagtypes.M1_POSSIBLE_4B:
            if len(manufacturer) == 0:
                manufacturer = "Default 1K (4B)"
            map_ret["manufacturer"] = manufacturer
        elif typ == tagtypes.M1_POSSIBLE_7B:
            if len(manufacturer) == 0:
                manufacturer = "Default 1K (7B)"
            map_ret["manufacturer"] = manufacturer

    return map_ret

# -*- coding: UTF-8 -*-
import executor
import lfsearch
import tagtypes
import lft55xx
import lfem4x05


def createRetObj(uid, raw, ret):
    """
        创建返回值字典对象
    """
    return {"return": ret, "data": uid, "raw": raw}


def read(cmd, uid_regex, raw_regex, uid_index=0, raw_index=0):
    """通用的读取标签信息函数，执行指定的命令进行卡号获取"""
    # 判断执行命令是否超时
    if executor.startPM3Task(cmd, 5000) == -1:
        print("执行命令 \"" + cmd + "\" 超时")
        return createRetObj(None, None, -1)
    # 判断是否寻找到卡片
    b1 = executor.hasKeyword("Found")
    b2 = executor.hasKeyword("ID")
    b3 = executor.hasKeyword("crc ok")
    b4 = executor.hasKeyword("FC")
    b5 = executor.hasKeyword("Raw")
    is_content_empty = executor.isEmptyContent()
    if (not b1 and not b2 and not b3 and not b4 and not b5) or is_content_empty:
        # if cmd == "lf io read":
        # 	util.printContent()
        print("lfread没有发现卡片。")
        return createRetObj(None, None, -1)
    # else:
    # 	util.printContent()
    uid = ""
    raw = ""
    # 根据传入的正则表达式或者处理函数进行数据截取
    if uid_regex is not None:
        if isinstance(uid_regex, str):
            uid_group = executor.getContentFromRegexA(uid_regex)
            if len(uid_group) <= 0 or uid_index >= len(uid_group):
                return createRetObj(None, None, -1)
            uid = lfsearch.cleanHexStr(uid_group[uid_index])

        # UID或者FCCN或者其他的信息截取
        elif callable(uid_regex):
            uid = uid_regex()

        # 出现了不被识别的操作
        else:
            raise Exception("不被识别的参数传入: ", uid_regex)

        if len(uid) <= 0:
            return createRetObj(None, None, -1)

    if raw_regex is not None:
        if isinstance(raw_regex, str):

            raw_group = executor.getContentFromRegexA(raw_regex)
            if len(raw_group) <= 0 or raw_index >= len(raw_group):
                return createRetObj(None, None, -1)

            raw = lfsearch.cleanHexStr(raw_group[raw_index])

        # RAW截取
        elif callable(raw_regex):
            raw = raw_regex()

        # 出现了不被识别的操作
        else:
            raise Exception("不被识别的参数传入: ", raw_regex)

        if len(raw) <= 0:
            createRetObj(None, None, -1)

    # 防止空数据的存在，进行交替赋值
    if (uid is None or len(uid) == 0) and (raw is not None and len(raw) > 0):
        uid = raw
    if (raw is None or len(raw) == 0) and (uid is not None and len(uid) > 0):
        raw = uid

    # 最后再次确认读取到的数据没问题
    # 如果但凡一个有问题，我们还是要
    # 将读卡结果置为失败
    if uid is None or raw is None:
        return createRetObj(None, None, -1)

    return createRetObj(uid, raw, 1)


def readFCCNAndRaw(cmd, uid_index=0, raw_index=0):
    """读取FCCN和RAW"""
    return read(cmd, lfsearch.getFCCN, lfsearch.REGEX_RAW, uid_index, raw_index)


def readCardIdAndRaw(cmd, uid_index=0, raw_index=0):
    """读取卡片ID和RAW"""
    return read(cmd, lfsearch.REGEX_CARD_ID, lfsearch.REGEX_RAW, uid_index, raw_index)


def readEM410X(listener=None, infos=None):
    """读取EM410X"""
    return read("lf em 410x_read", lfsearch.REGEX_EM410X, lfsearch.REGEX_EM410X)


def readHID(listener=None, infos=None):
    """读取HID标签"""
    return read("lf hid read", lfsearch.REGEX_HID, lfsearch.REGEX_HID)


def readIndala(listener=None, infos=None):
    """读取indala标签"""
    return readFCCNAndRaw("lf indala read")


def readAWID(listener=None, infos=None):
    """读取AWID标签"""
    return readFCCNAndRaw("lf awid read")


def readProxIO(listener=None, infos=None):
    """读取ProxID"""
    return read("lf io read", lfsearch.getXsf, lfsearch.REGEX_RAW)


def readGProx2(listener=None, infos=None):
    """读取G-ProxII"""
    return readFCCNAndRaw("lf gproxii read")


def readSecurakey(listener=None, infos=None):
    """读取Securakey"""
    return readFCCNAndRaw("lf securakey read")


def readViking(listener=None, infos=None):
    """读取Viking"""
    return readCardIdAndRaw("lf viking read")


def readPyramid(listener=None, infos=None):
    """读取Pyramid"""
    return readFCCNAndRaw("lf pyramid read")


def readFDX(listener=None, infos=None):
    """读取动物标签"""
    return read("lf fdx read", lfsearch.REGEX_ANIMAL, lfsearch.REGEX_ANIMAL)


def readGALLAGHER(listener=None, infos=None):
    """读取GALLAGHER"""
    return readFCCNAndRaw("lf gallagher read")


def readJablotron(listener=None, infos=None):
    """读取Jablotron"""
    return readCardIdAndRaw("lf jablotron read")


def readKeri(listener=None, infos=None):
    """读取KERI"""
    return readFCCNAndRaw("lf keri read")


def readNedap(listener=None, infos=None):
    """读取NEDAP"""
    return readCardIdAndRaw("lf nedap read")


def readNoralsy(listener=None, infos=None):
    """读取Noralsy"""
    return readCardIdAndRaw("lf noralsy read")


def readPAC(listener=None, infos=None):
    """读取PAC"""
    return readCardIdAndRaw("lf pac read")


def readParadox(listener=None, infos=None):
    """读取Paradox"""
    return readFCCNAndRaw("lf paradox read")


def readPresco(listener=None, infos=None):
    """读取Presco"""
    return readCardIdAndRaw("lf presco read")


def readVisa2000(listener=None, infos=None):
    """读取Visa2000"""
    return readCardIdAndRaw("lf visa2000 read")


def readT55XX(listener=None, infos=None):
    """读取T55xx或者EM4x05系列的卡片系列的卡片"""
    if listener is None:
        print("readT55XX的回调不可以为空哦！")
        return
    # 先侦测是否是T55XX
    if infos is not None and "key" in infos:
        key = infos["key"]
    else:
        key = None
    ret = lft55xx.detectT55XX(key)
    # 无法判断是否是T55XX
    if ret < 0: return createRetObj(None, None, -2)
    # 如果卡片加密，或卡片型号不对
    if ret == 1 or ret == 3:
        return createRetObj(None, None, lft55xx.chkAndDumpT55xx(listener))
    # 如果是未加密的卡，则直接读取
    if ret == 2:
        return createRetObj(None, None, lft55xx.dumpT55XX(listener))
    # 如果卡片加密，但是已经知道秘钥
    if ret == 4:
        return createRetObj(None, None, lft55xx.dumpT55XX(listener, key))


def readEM4X05(listener=None, infos=None):
    """读取4X05系列的卡片"""
    # 先侦测是否是T55XX
    if infos is not None and "key" in infos:
        key = infos["key"]
    else:
        key = None
    return createRetObj(None, None, lfem4x05.infoAndDumpEM4x05ByKey(key))


def readNexWatch(listener=None, infos=None):
    """读取NexWatch"""
    return readCardIdAndRaw("lf nexwatch read")


# 读取操作映射表，可以根据卡片类型直接取出对应的读取实现函数执行
READ = {
    tagtypes.EM410X_ID: readEM410X,
    tagtypes.HID_PROX_ID: readHID,
    tagtypes.INDALA_ID: readIndala,
    tagtypes.AWID_ID: readAWID,
    tagtypes.IO_PROX_ID: readProxIO,
    tagtypes.GPROX_II_ID: readGProx2,
    tagtypes.SECURAKEY_ID: readSecurakey,
    tagtypes.VIKING_ID: readViking,
    tagtypes.PYRAMID_ID: readPyramid,
    tagtypes.FDXB_ID: readFDX,
    tagtypes.GALLAGHER_ID: readGALLAGHER,
    tagtypes.JABLOTRON_ID: readJablotron,
    tagtypes.KERI_ID: readKeri,
    tagtypes.NEDAP_ID: readNedap,
    tagtypes.NORALSY_ID: readNoralsy,
    tagtypes.PAC_ID: readPAC,
    tagtypes.PARADOX_ID: readParadox,
    tagtypes.PRESCO_ID: readPresco,
    tagtypes.VISA2000_ID: readVisa2000,
    tagtypes.T55X7_ID: readT55XX,
    tagtypes.EM4305_ID: readEM4X05,
    tagtypes.NEXWATCH_ID: readNexWatch,
}

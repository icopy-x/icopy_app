# -*- coding: UTF-8 -*-
import base64
import re
import hashlib
import platform
import subprocess

from Crypto.Cipher import AES

import version

UNSUPPORTED = -1
M1_S70_4K_4B = 0
M1_S50_1K_4B = 1
ULTRALIGHT = 2
ULTRALIGHT_C = 3
ULTRALIGHT_EV1 = 4
NTAG213_144B = 5
NTAG215_504B = 6
NTAG216_888B = 7
EM410X_ID = 8
HID_PROX_ID = 9
INDALA_ID = 10
AWID_ID = 11
IO_PROX_ID = 12
GPROX_II_ID = 13
SECURAKEY_ID = 14
VIKING_ID = 15
PYRAMID_ID = 16
ICLASS_LEGACY = 17
ICLASS_ELITE = 18
ISO15693_ICODE = 19
LEGIC_MIM256 = 20
FELICA = 21
ISO14443B = 22
T55X7_ID = 23
EM4305_ID = 24
M1_MINI = 25
M1_PLUS_2K = 26
TOPAZ = 27
FDXB_ID = 28
GALLAGHER_ID = 29
JABLOTRON_ID = 30
KERI_ID = 31
NEDAP_ID = 32
NORALSY_ID = 33
PAC_ID = 34
PARADOX_ID = 35
PRESCO_ID = 36
VISA2000_ID = 37
HITAG2_ID = 38
MIFARE_DESFIRE = 39
HF14A_OTHER = 40
M1_S70_4K_7B = 41
M1_S50_1K_7B = 42
M1_POSSIBLE_4B = 43
M1_POSSIBLE_7B = 44
NEXWATCH_ID = 45
ISO15693_ST_SA = 46
ICLASS_SE = 47

types = {
    # 类型ID  类型名称   是否可读   读取成功后是否可写
    UNSUPPORTED: ("Unsupported", False, False),

    M1_S70_4K_4B: ("M1 S70 4K 4B", True, True),  # 1type
    M1_S50_1K_4B: ("M1 S50 1K 4B", True, True),  # 1type

    # UL卡
    ULTRALIGHT: ("Ultralight", True, True),  # 2type
    ULTRALIGHT_C: ("Ultralight C", True, True),  # 2type
    ULTRALIGHT_EV1: ("Ultralight EV1", True, True),  # 2type
    NTAG213_144B: ("NTAG213 144b", True, True),  # 2type
    NTAG215_504B: ("NTAG215 504b", True, True),  # 2type
    NTAG216_888B: ("NTAG216 888b", True, True),  # 2type

    # 标准型ID卡
    EM410X_ID: ("EM410x ID", True, True),  # 3type
    HID_PROX_ID: ("HID Prox ID", True, True),  # 3type
    INDALA_ID: ("Indala ID", True, True),  # 3type
    AWID_ID: ("AWID ID", True, True),  # 3type
    IO_PROX_ID: ("IO Prox ID", True, True),  # 3type
    GPROX_II_ID: ("GProx II ID", True, True),  # 3type
    SECURAKEY_ID: ("Securakey ID", True, True),  # 3type
    VIKING_ID: ("Viking ID", True, True),  # 3type
    PYRAMID_ID: ("Pyramid ID", True, True),  # 3type

    # 特殊型HF卡
    ICLASS_LEGACY: ("iClass Legacy", True, True),
    ICLASS_ELITE: ("iClass Elite", True, True),
    ISO15693_ICODE: ("ISO15693 ICODE", True, True),
    LEGIC_MIM256: ("Legic MIM256", True, False),
    FELICA: ("Felica", True, False),
    ISO14443B: ("ISO14443B", False, False),

    # 特殊型ID卡
    T55X7_ID: ("T55x7_ID", True, True),
    EM4305_ID: ("EM4305_ID", True, True),

    M1_MINI: ("M1 Mini", True, True),  # 1type
    M1_PLUS_2K: ("M1 Plus 2K", True, True),  # 1type

    TOPAZ: ("Topaz", False, False),

    # 扩展型ID卡
    FDXB_ID: ("FDXB ID", True, True),  # 3type
    GALLAGHER_ID: ("GALLAGHER ID", True, True),  # 3type
    JABLOTRON_ID: ("Jablotron ID", True, True),  # 3type
    KERI_ID: ("KERI ID", True, True),  # 3type
    NEDAP_ID: ("NEDAP ID", True, True),  # 3type
    NORALSY_ID: ("Noralsy ID", True, True),  # 3type
    PAC_ID: ("PAC ID", True, True),  # 3type
    PARADOX_ID: ("Paradox ID", True, True),  # 3type
    PRESCO_ID: ("Presco ID", True, True),  # 3type
    VISA2000_ID: ("Visa2000 ID", True, True),  # 3type
    HITAG2_ID: ("Hitag2 ID", False, False),  # 3type

    MIFARE_DESFIRE: ("MIFARE DESFire", False, False),
    HF14A_OTHER: ("HF14A Other", True, True),

    # 特殊型M1卡
    M1_S70_4K_7B: ("M1 S70 4K 7B", True, True),  # 1type
    M1_S50_1K_7B: ("M1 S50 1K 7B", True, True),  # 1type
    M1_POSSIBLE_4B: ("M1 POSSIBLE 4B", True, True),  # 1type
    M1_POSSIBLE_7B: ("M1 POSSIBLE 7B", True, True),  # 1type

    # 扩展型ID卡
    NEXWATCH_ID: ("NexWatch ID", True, True),  # 3type

    # 其他特殊卡
    ISO15693_ST_SA: ("ISO15693 ST SA", True, True),
    ICLASS_SE:  ("iClass SE", True, True),
}


def isTagCanRead(typ, infos=None):
    """
        指定的类型的卡片是否可读
    :param infos:
    :param typ:
    :return:
    """

    def box():
        """
            内部封箱
        :return:
        """
        if infos is not None:
            # 单独处理14A的特殊卡
            if typ == HF14A_OTHER:
                uid_len = infos["len"]
                if uid_len != 4 and uid_len != 7:
                    return False
                else:
                    return True

            # 单独处理iclass的没有密钥的卡
            if typ == ICLASS_ELITE:  # 如果遇到了没有可用密钥的iclass卡片，我们应该直接返回不可读的状态
                if "key" in infos and (infos["key"] is None or len(infos["key"]) == 0):
                    return False

        if typ not in types:
            print("tagtypes.py -> isTagCanRead 无法判断类型: ", typ, "是否可读。")
            return False

        readable = types[typ][1]
        print("{} -> 是否可读: {}".format(getName(typ), readable))
        return readable

    # 测试开始 <
    # 没错，为了windows下能正常测试，我们需要加入测试区域
    if platform.system() == "Windows":
        return box()
    # 测试结束 >

    # 验证开始 <
    try:
        # Serial          : 02c000814f54266f
        output_str = str(subprocess.check_output("cat /proc/cpuinfo", shell=True), errors='ignore')
        sn_str = re.search(r"Serial\s*:\s*([a-fA-F0-9]+)", output_str).group(1)
        sn_bytes = sn_str.encode("utf-8")  # Unicode字符串解码为字节流
        # 经过三次MD5 16后，我们获得了解密UID的秘钥
        m = hashlib.md5()
        m.update(sn_bytes)
        m.update(sn_bytes)
        m.update(sn_bytes)
        r = m.hexdigest()
        # 进行MD5求和
        count = 0
        ret = ""  # 这个是秘钥，
        while count < len(r):
            tmp = format(int(r[count], 16) + int(r[count + 1], 16), "x")
            ret += tmp[0]
            count += 2
        # 这里我们不做判断，只去映射
        maps = {
            sn_str: "a",
        }

        # 解密UID
        aes_obj = AES.new(
            ret.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        if i[0] not in maps:
            raise Exception("?")
        if sn_str != i[0]:
            raise Exception("!")
    except Exception as e:
        print(e)
        return False
    # 验证结束 >

    return box()


def isTagCanWrite(typ, infos=None):
    """
        指定的类型的卡片是否可写
    :param typ:
    :return:
    """

    def box():
        """
            内部封箱
        :return:
        """
        if typ not in types:
            print("tagtypes.py -> isTagCanWrite 无法判断类型: ", typ, "是否可写。")
            return False
        writeable = types[typ][2]
        print("{} -> 是否可写: {}".format(getName(typ), writeable))
        return writeable

    # 测试开始 <
    # 没错，为了windows下能正常测试，我们需要加入测试区域
    if platform.system() == "Windows":
        return box()
    # 测试结束 >

    # 验证开始 <
    try:
        # Serial          : 02c000814f54266f
        output_str = str(subprocess.check_output("cat /proc/cpuinfo", shell=True), errors='ignore')
        sn_str = re.search(r"Serial\s*:\s*([a-fA-F0-9]+)", output_str).group(1)
        sn_bytes = sn_str.encode("utf-8")  # Unicode字符串解码为字节流
        # 经过三次MD5 16后，我们获得了解密UID的秘钥
        m = hashlib.md5()
        m.update(sn_bytes)
        m.update(sn_bytes)
        m.update(sn_bytes)
        r = m.hexdigest()
        # 进行MD5求和
        count = 0
        ret = ""  # 这个是秘钥，
        while count < len(r):
            tmp = format(int(r[count], 16) + int(r[count + 1], 16), "x")
            ret += tmp[0]
            count += 2
        # 这里我们不做判断，只去映射
        maps = {
            sn_str: "a",
        }

        # 解密UID
        aes_obj = AES.new(
            ret.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        if i[0] not in maps:
            raise Exception("?")
        if sn_str != i[0]:
            raise Exception("!")
    except Exception as e:
        print(e)
        return False
    # 验证结束 >

    return box()


def getM1Types():
    """
        获取所有的M1经典类型标签
    :return:
    """
    return [
        M1_MINI,
        M1_S50_1K_4B,
        M1_S70_4K_4B,
        M1_PLUS_2K,
        M1_S50_1K_7B,
        M1_S70_4K_7B,
        M1_POSSIBLE_4B,
        M1_POSSIBLE_7B,
    ]


def getM14BTypes():
    """
        获取所有的M1的4字节的UID的类型
    :return:
    """
    return [
        M1_MINI,
        M1_S50_1K_4B,
        M1_S70_4K_4B,
        M1_PLUS_2K,
        M1_POSSIBLE_4B,
    ]


def getM17BTypes():
    """
        获取所有的M1的7字节的UID的类型
    :return:
    """
    return [
        M1_S50_1K_7B,
        M1_S70_4K_7B,
        M1_POSSIBLE_7B,
    ]


def getM14KTypes():
    """
        获取所有的M1卡4K容量的类型
    :return:
    """
    return [
        M1_S70_4K_4B,
        M1_S70_4K_7B
    ]


def getM11KTypes():
    """
        获取所有的M1卡1K容量的类型
    :return:
    """
    return [
        M1_S50_1K_7B,
        M1_S50_1K_4B,
        M1_POSSIBLE_7B,
        M1_POSSIBLE_4B
    ]


def getM12KTypes():
    """
        获取所有的M1卡2K容量的类型
    :return:
    """
    return [
        M1_PLUS_2K
    ]


def getM1MiniTypes():
    """
        获取所有的M1卡Mini的类型
    :return:
    """
    return [
        M1_MINI
    ]


def getiClassTypes():
    """
        获取所有的普通可读iclass类型的系列
    :return:
    """
    return [
        ICLASS_LEGACY,
        ICLASS_ELITE,
        ICLASS_SE,
    ]


def getHfOtherTypes():
    """
        获取所有的高频不被单独处理的卡的类型
    :return:
    """
    ret = list()
    ret.extend([
        LEGIC_MIM256,
        ISO15693_ICODE,
        ISO15693_ST_SA,
        FELICA,
        HF14A_OTHER,
    ])
    ret.extend(getiClassTypes())
    return ret


def getULTypes():
    """
        获取所有的UL类型标签
    :return:
    """
    return [
        ULTRALIGHT,
        ULTRALIGHT_C,
        ULTRALIGHT_EV1,
        NTAG213_144B,
        NTAG215_504B,
        NTAG216_888B
    ]


def getAllHigh():
    """
        获取所有的高频标签
    :return:
    """
    return [
        ISO15693_ICODE,
        ISO15693_ST_SA,
        LEGIC_MIM256,
        FELICA,
        ICLASS_LEGACY,
        ICLASS_ELITE,
    ]


def getAllLow():
    """
        获取搜索的可读低频卡
    :return:
    """
    return [
        EM410X_ID,
        HID_PROX_ID,
        INDALA_ID,
        AWID_ID,
        IO_PROX_ID,
        GPROX_II_ID,
        SECURAKEY_ID,
        VIKING_ID,
        PYRAMID_ID,
        FDXB_ID,
        GALLAGHER_ID,
        JABLOTRON_ID,
        KERI_ID,
        NEDAP_ID,
        NORALSY_ID,
        PAC_ID,
        PARADOX_ID,
        PRESCO_ID,
        VISA2000_ID,
        NEXWATCH_ID,
        T55X7_ID,
        EM4305_ID
    ]


def getAllLowCanDump():
    """
        获取所有的可以dump的低频卡
    :return:
    """
    return [
        EM4305_ID,
        T55X7_ID,
    ]


def getAllLowNoDump():
    """
        获得所有的不可以dump的低频卡
        也就是仅有卡号的低频卡
    :return:
    """
    ret = []
    lf_can_dump = getAllLowCanDump()
    for typ in getAllLow():
        if typ in lf_can_dump:
            continue
        ret.append(typ)
    return ret


def _get_name(typ):
    """
        内部使用的名称获取函数
    :param typ:
    :return:
    """
    if typ == T55X7_ID:
        return "T5577"
    if typ == EM4305_ID:
        return "EM4305"
    return types[typ][0]


def getName(typ):
    """
        根据传入的类型获得对应的名称
    """
    if isinstance(typ, int):
        if typ in types:
            return _get_name(typ)
    if isinstance(typ, list):
        names = []
        for t in typ:
            if t in types:
                names.append(_get_name(t))
        return names
    return "None"


def getReadable():
    """
        返回经过手动排序的可读列表
    :return:
    """
    list_ret = [
        M1_S50_1K_4B,
        M1_S50_1K_7B,

        M1_S70_4K_4B,
        M1_S70_4K_7B,

        M1_MINI,
        M1_PLUS_2K,

        ULTRALIGHT,
        ULTRALIGHT_C,
        ULTRALIGHT_EV1,
        NTAG213_144B,
        NTAG215_504B,
        NTAG216_888B,

        ISO15693_ICODE,
        ISO15693_ST_SA,
        LEGIC_MIM256,
        FELICA,
        ICLASS_LEGACY,
        ICLASS_ELITE,

        EM410X_ID,
        HID_PROX_ID,
        INDALA_ID,
        AWID_ID,
        IO_PROX_ID,
        GPROX_II_ID,
        SECURAKEY_ID,
        VIKING_ID,
        PYRAMID_ID,
        FDXB_ID,
        GALLAGHER_ID,
        JABLOTRON_ID,
        KERI_ID,
        NEDAP_ID,
        NORALSY_ID,
        PAC_ID,
        PARADOX_ID,
        PRESCO_ID,
        VISA2000_ID,
        NEXWATCH_ID,
        T55X7_ID,
        EM4305_ID
    ]

    def box():
        ret = []
        for typ in list_ret:
            if typ not in types:
                print("tagtypes.py -> getReadable 无法判断类型: ", typ, "是否可读。")
                continue
            if types[typ][1]:
                ret.append(typ)
        return ret

    # 测试开始 <
    # 没错，为了windows下能正常测试，我们需要加入测试区域
    if platform.system() == "Windows":
        return box()
    # 测试结束 >

    # 验证开始 <
    try:
        # Serial          : 02c000814f54266f
        output_str = str(subprocess.check_output("cat /proc/cpuinfo", shell=True), errors='ignore')
        sn_str = re.search(r"Serial\s*:\s*([a-fA-F0-9]+)", output_str).group(1)
        sn_bytes = sn_str.encode("utf-8")  # Unicode字符串解码为字节流
        # 经过三次MD5 16后，我们获得了解密UID的秘钥
        m = hashlib.md5()
        m.update(sn_bytes)
        m.update(sn_bytes)
        m.update(sn_bytes)
        r = m.hexdigest()
        # 进行MD5求和
        count = 0
        key_device = ""  # 这个是秘钥，
        while count < len(r):
            tmp = format(int(r[count], 16) + int(r[count + 1], 16), "x")
            key_device += tmp[0]
            count += 2
        # 这里我们不做判断，只去映射
        maps = {
            sn_str: "a",
        }

        # 解密UID
        aes_obj = AES.new(
            key_device.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        if i[0] not in maps:
            raise Exception("?")
        if sn_str != i[0]:
            raise Exception("!")
    except Exception as e:
        print(e)
        return False
    # 验证结束 >

    return box()


def getUnreadable():
    temp = []
    for t in types.values():
        if not t[1]:
            temp.append(t[0])
    return temp

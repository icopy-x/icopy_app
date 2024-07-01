"""
    维护TAG搜索到的时候的信息模板
"""
import re

import resources
import tagtypes
from tkinter import font


def create_by_parent(parent, tag):
    return str(id(parent)) + ":" + tag


def __drawFinal(title, typStr, nameStr, parent):
    """
        绘制顶端固定的两行数据
    :param typStr:
    :param parent:
    :return:
    """
    parent.create_text(18, 48, text=title, font=resources.get_font_force_en(22, True), anchor="nw", tags=create_by_parent(parent, "title"))

    parent.create_text(18, 82, text=nameStr, font=resources.get_font_force_en(14, True), anchor="nw",
                       tags=create_by_parent(parent, "nameStr"))

    typStr = "Frequency: {}".format(typStr)
    parent.create_text(18, 106, text=typStr, font=resources.get_font_force_en(13), anchor="nw", tags=create_by_parent(parent, "typStr"))


def __drawFinalByData(data, parent):
    # 先绘制固定数据
    # 大标题
    title = TYPE_TEMPLATE[data["type"]][2]
    # 频率
    typ = TYPE_TEMPLATE[data["type"]][0]
    # 小标题
    name = TYPE_TEMPLATE[data["type"]][1]
    # 如果小标题为空，尝试从数据中提取
    if name is None:
        if "chip" in data:
            name = data["chip"]
        elif "manufacturer" in data:
            m = data["manufacturer"]
            if m is not None and len(m) > 15:
                m = m[0:12] + "..."
            name = m
    __drawFinal(title, typ, name, parent)


def __drawDataLines(parent, *lines, base_y=128, pady=2):
    """
        绘制通用的数据视图
    :param data:
    :param parent:
    :return:
    """
    y = base_y
    for line in lines:
        if line is None:
            continue
        f = font.Font(font=resources.get_font_force_en(13))
        w = parent.create_text(18, y, text=line, font=f, width=200, justify='left', anchor="nw",
                               tags=create_by_parent(parent, "lines"))
        # 获取它的xy，来获取高度
        xy = parent.bbox(w)
        # print(xy)
        y = xy[3] + pady
        # print(y)


def __drawM1(data, parent):
    """
        绘制M1卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    uid = "UID: {}".format(data["uid"])
    if "ats" in data:
        v1 = "ATS"
        v2 = data["ats"]
    else:
        v1 = "ATQA"
        v2 = data["atqa"]

    if len(v2) > 6:
        v2 = str(v2)[0:6] + "+"
        sa = "SAK: {} {}: {}".format(data["sak"], v1, v2)
    else:
        sa = "SAK: {}  {}: {}".format(data["sak"], v1, v2)
    # 绘制
    __drawDataLines(parent, uid, sa)
    # __drawDataLines(parent, uid, base_y=135, pady=2)


def __drawMFU(data, parent):
    """
        绘制MFU卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    uid = "UID: {}".format(data["uid"])
    __drawDataLines(parent, uid)


def __drawID(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    typ = data["type"]
    if "chipset" in data:
        chipset = data["chipset"]
    else:
        chipset = "X"

    if data['data'] is None:
        data = "unknown"
    else:
        data = data["data"]

    if re.match(r"[a-fA-F0-9 -]+", data) and "(" not in data and "," not in data:
        if typ != tagtypes.INDALA_ID:
            data = "UID: {}".format(data)
        else:
            data = "RAW: {}".format(data)

    if len(data) > 19:
        data = data[:16]
        data = data + "..."

    chipset = "Chipset: {}".format(chipset)
    __drawDataLines(parent, data, chipset)


def __drawEM4x05(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    sn = "SN: {}".format(data["sn"])
    cw = "CW: {}".format(data["cw"])
    __drawDataLines(parent, sn, cw)


def __drawT55xx(data, parent):
    """
        绘制T55XX的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    m = "Modulate: {}".format(data["modulate"])
    b = "B0: {}".format(data["b0"])
    __drawDataLines(parent, m, b)


def __drawLEGIC_MIM256(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    m = "MCD: {}".format(data["mcd"])
    b = "MSN: {}".format(data["msn"])
    __drawDataLines(parent, m, b)


def __drawFelica(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    m = "IDM: {}".format(data["idm"])
    __drawDataLines(parent, m)


def __draw14B(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    uid = "UID: {}".format(data["uid"])
    # atqb = "ATQB: {}".format(data["atqb"]) 不需要显示ATQB
    __drawDataLines(parent, uid)


def __drawTopaz(data, parent):
    """
        绘制ID卡的数据视图
    :param data:
    :param parent:
    :return:
    """
    __drawFinalByData(data, parent)
    # 绘制DATA
    uid = "UID: {}".format(data["uid"])
    atqb = "ATQA: {}".format(data["atqa"])
    __drawDataLines(parent, uid, atqb)


def __draw_iclass(data, parent):
    """
        绘制iclass的数据视图
    :param data:
    :param parent:
    :return:
    """

    # /SE/SEOS
    typ = data["type"]
    
    if typ == tagtypes.ICLASS_ELITE:
        data["chip"] = "Elite"

    if "key" not in data or data["key"] is None or len(data["key"]) <= 0:
        data["chip"] = "Elite/SE/SEOS"

    __drawFinalByData(data, parent)
    # 绘制DATA
    uid = "CSN: {}".format(data["csn"])
    __drawDataLines(parent, uid)


def __draw_iclass_se(data, parent):
    """
        绘制iclass的数据视图
    :param data:
    :param parent:
    :return:
    """
    # 确保存在type参数，这很重要
    data["type"] = tagtypes.ICLASS_SE
    __drawFinalByData(data, parent)
    # 绘制DATA
    uid = "CSN: {}".format(data["blck7"])
    # 绘制FC CN
    fc_cn = "FC,CN: {},{}".format(data["fc"], data["id"])
    __drawDataLines(parent, uid, fc_cn)


# 类型到模板的映射
TYPE_TEMPLATE = {
    # M1
    tagtypes.M1_S70_4K_4B: ("13.56MHZ", "M1 S70 4K (4B)", "MIFARE", __drawM1),
    tagtypes.M1_S50_1K_4B: ("13.56MHZ", "M1 S50 1K (4B)", "MIFARE", __drawM1),
    tagtypes.M1_S70_4K_7B: ("13.56MHZ", "M1 S70 4K (7B)", "MIFARE", __drawM1),
    tagtypes.M1_S50_1K_7B: ("13.56MHZ", "M1 S50 1K (7B)", "MIFARE", __drawM1),
    tagtypes.M1_MINI: ("13.56MHZ", "M1 Mini 0.3K", "MIFARE", __drawM1),
    tagtypes.M1_PLUS_2K: ("13.56MHZ", "M1 Mini 0.3K", "MIFARE", __drawM1),
    tagtypes.M1_POSSIBLE_4B: ("13.56MHZ", None, "MF POSSIBLE", __drawM1),
    tagtypes.M1_POSSIBLE_7B: ("13.56MHZ", None, "MF POSSIBLE", __drawM1),
    # UL
    tagtypes.ULTRALIGHT: ("13.56MHZ", "Ultralight", "MIFARE", __drawMFU),
    tagtypes.ULTRALIGHT_C: ("13.56MHZ", "Ultralight C", "MIFARE", __drawMFU),
    tagtypes.ULTRALIGHT_EV1: ("13.56MHZ", "Ultralight EV1", "MIFARE", __drawMFU),
    tagtypes.NTAG213_144B: ("13.56MHZ", "NTAG213 144b", "NFCTAG", __drawMFU),
    tagtypes.NTAG215_504B: ("13.56MHZ", "NTAG215 504b", "NFCTAG", __drawMFU),
    tagtypes.NTAG216_888B: ("13.56MHZ", "NTAG216 888b", "NFCTAG", __drawMFU),
    tagtypes.MIFARE_DESFIRE: ("13.56MHZ", "DESFire", "MIFARE", __drawM1),
    # 特殊的高频卡
    tagtypes.HF14A_OTHER: ("13.56MHZ", "ISO/IEC 14443-A", "ISO14443-A", __drawM1),
    tagtypes.ISO15693_ICODE: ("13.56MHZ", "ISO15693 ICODE", "ICODE", __drawMFU),
    tagtypes.ISO15693_ST_SA: ("13.56MHZ", "ISO15693 ST SA", "ISO15693", __drawMFU),
    tagtypes.LEGIC_MIM256: ("13.56MHZ", "Legic MIM256", "Legic", __drawLEGIC_MIM256),
    tagtypes.FELICA: ("13.56MHZ", "Felica", "Felica", __drawFelica),
    tagtypes.ISO14443B: ("13.56MHZ", "ISO14443-B", "STR512", __draw14B),
    tagtypes.TOPAZ: ("13.56MHZ", "Topaz", "TOPAZ", __drawTopaz),
    tagtypes.ICLASS_LEGACY: ("13.56MHZ", "Legacy", "iCLASS", __draw_iclass),
    tagtypes.ICLASS_ELITE: ("13.56MHZ", None, "iCLASS", __draw_iclass),
    # ID
    tagtypes.EM410X_ID: ("125KHZ", "EM410x ID", "EM Marin", __drawID),
    tagtypes.HID_PROX_ID: ("125KHZ", "HID Prox ID", "HID Prox", __drawID),
    tagtypes.INDALA_ID: ("125KHZ", "Indala ID", "HID Indala", __drawID),
    tagtypes.AWID_ID: ("125KHZ", "AWID ID", "AWID", __drawID),
    tagtypes.IO_PROX_ID: ("125KHZ", "IO Prox ID", "IoProx", __drawID),
    tagtypes.GPROX_II_ID: ("125KHZ", "G-Prox II ID", "G-Prox", __drawID),
    tagtypes.SECURAKEY_ID: ("125KHZ", "Securakey ID", "SecuraKey ", __drawID),
    tagtypes.VIKING_ID: ("125KHZ", "Viking ID", "Viking", __drawID),
    tagtypes.PYRAMID_ID: ("125KHZ", "Pyramid ID", "Pyramid", __drawID),
    tagtypes.FDXB_ID: ("125KHZ", "Animal ID", "FDX-B", __drawID),
    tagtypes.GALLAGHER_ID: ("125KHZ", "GALLAGHER ID", "Gallagher", __drawID),
    tagtypes.JABLOTRON_ID: ("125KHZ", "Jablotron ID", "Jablotron", __drawID),
    tagtypes.KERI_ID: ("125KHZ", "KERI ID", "Keri", __drawID),
    tagtypes.NEDAP_ID: ("125KHZ", "NEDAP ID", "Nedap", __drawID),
    tagtypes.NORALSY_ID: ("125KHZ", "Noralsy ID", "Noralsy", __drawID),
    tagtypes.PAC_ID: ("125KHZ", "PAC/Stanley ID", "PAC/Stanley", __drawID),
    tagtypes.PARADOX_ID: ("125KHZ", "Paradox ID", "Paradox", __drawID),
    tagtypes.PRESCO_ID: ("125KHZ", "Presco ID", "Presco", __drawID),
    tagtypes.VISA2000_ID: ("125KHZ", "Visa2000 ID", "Visa2000", __drawID),
    tagtypes.HITAG2_ID: ("125KHZ", "Hitag", "HITAG", __drawID),
    tagtypes.NEXWATCH_ID: ("125KHZ", "NexWatch ID", "NexWatch", __drawID),
    # 特殊的低频卡
    tagtypes.EM4305_ID: ("125KHZ", None, "EM4305", __drawEM4x05),
    tagtypes.T55X7_ID: ("125KHZ", None, "T5577", __drawT55xx),

    # 特殊的ICLASS
    tagtypes.ICLASS_SE: ("13.56MHZ", "iCLASS SE", "iCLASS", __draw_iclass_se),
}


def draw(typ, data, parent):
    """
        自动根据类型调用模板进行绘制
    :param typ: 卡片类型
    :param data: 数据
    :param parent: 承载的父容器，绘制的UI在在此基础上进行
    :return:
    """
    # print("将被绘制的数据: ", data)
    if typ not in TYPE_TEMPLATE:
        print("没有找到对应类型的模板注册: ", typ)
        return
    fun = TYPE_TEMPLATE[typ][3]
    if fun is None:
        print("该模板没有实现绘制函数: ", typ)
        return
    if data is None:
        print("传入的数据是空的，无法绘制。: ", typ)
        return
    fun(data, parent)


def dedraw(parent):
    """
        取消绘制数据
    :param parent:
    :return:
    """
    parent.delete(create_by_parent(parent, "lines"))
    parent.delete(create_by_parent(parent, "title"))
    parent.delete(create_by_parent(parent, "nameStr"))
    parent.delete(create_by_parent(parent, "typStr"))
    return

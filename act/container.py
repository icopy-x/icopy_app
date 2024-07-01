import tagtypes


TYP0 = 0
TYP1 = 1
TYP2 = 2
TYP3 = 3
TYP4 = 4
TYP5 = 5
TYP6 = 6
TYP7 = 7
TYP8 = 8
TYP9 = 9
TYP10 = 10
TYP11 = 11
TYP12 = 12
TYP13 = 13
TYP14 = 14

types = {
    # 类型ID      类型名称                          对外id           提示语文件子id
    -1:          ("Unsupported",                   "Unsupported",   ""),

    TYP0:        ("MF1-1K-4b-UID/CUID/UFUID",      "M1-4b",         "1"),
    TYP1:        ("MF1-1K-7b-Gen2",                "M1-7b",         "4"),
    TYP2:        ("MF1-4K-4b-Gen2",                "M4-4b",         "5"),
    TYP3:        ("MF1-4K-7b-Gen2",                "M4-7b",         "6"),
    TYP4:        ("Ultralight-Gen2",               "UL",            "7"),
    TYP5:        ("Ultralight C-Gen2",             "UL-C",          "8"),
    TYP6:        ("Ultralight Ev1-Gen2",           "ULEv1",         "9"),
    TYP7:        ("NTAG213/5/6",                   "Ntag",          "10"),
    TYP8:        ("ICODE",                         "ICODE",         "11"),
    TYP9:        ("iCLASS Legacy",                 "iCL",           "12"),
    TYP10:       ("iCLASS Elite",                  "iCE",           "13"),
    TYP11:       ("T5577",                         "ID1",           "14"),
    TYP12:       ("EM4305",                        "ID2",           "15"),

    TYP13:       ("ISO15693 ST SA",                "特斯联",         None),
    TYP14:       ("iCLASS SE",                     "iCS",            None),
}

containermap = {
    # 类型ID                        复制卡类型   卡片原本
    tagtypes.ULTRALIGHT          : (TYP4,),
    tagtypes.ULTRALIGHT_C        : (TYP5,),
    tagtypes.ULTRALIGHT_EV1      : (TYP6,),
    tagtypes.NTAG213_144B        : (TYP7,),
    tagtypes.NTAG215_504B        : (TYP7,),
    tagtypes.NTAG216_888B        : (TYP7,),

    tagtypes.ICLASS_LEGACY       : (TYP9,),
    tagtypes.ICLASS_ELITE        : (TYP10,),
    tagtypes.ICLASS_SE           : (TYP14,),

    tagtypes.ISO15693_ST_SA      : (TYP13,),
    tagtypes.ISO15693_ICODE      : (TYP8,),
    tagtypes.LEGIC_MIM256        : (None,),
    tagtypes.FELICA              : (None,),
    tagtypes.ISO14443B           : (None,),
    tagtypes.TOPAZ               : (None,),
    tagtypes.HF14A_OTHER         : (TYP0,),

    tagtypes.MIFARE_DESFIRE      : (None,),
    tagtypes.M1_MINI             : (TYP0,),
    tagtypes.M1_PLUS_2K          : (TYP2,),
    tagtypes.M1_S70_4K_4B        : (TYP2,),
    tagtypes.M1_S50_1K_4B        : (TYP0,),
    tagtypes.M1_S70_4K_7B        : (TYP3,),
    tagtypes.M1_S50_1K_7B        : (TYP1,),
    tagtypes.M1_POSSIBLE_4B      : (TYP0,),
    tagtypes.M1_POSSIBLE_7B      : (TYP1,),

    tagtypes.EM410X_ID           : (TYP11,),
    tagtypes.HID_PROX_ID         : (TYP11,),
    tagtypes.INDALA_ID           : (TYP11,),
    tagtypes.AWID_ID             : (TYP11,),
    tagtypes.IO_PROX_ID          : (TYP11,),
    tagtypes.GPROX_II_ID         : (TYP11,),
    tagtypes.SECURAKEY_ID        : (TYP11,),
    tagtypes.VIKING_ID           : (TYP11,),
    tagtypes.PYRAMID_ID          : (TYP11,),

    tagtypes.T55X7_ID            : (TYP11,),
    tagtypes.EM4305_ID           : (TYP12,),

    tagtypes.FDXB_ID             : (TYP11,),
    tagtypes.GALLAGHER_ID        : (TYP11,),
    tagtypes.JABLOTRON_ID        : (TYP11,),
    tagtypes.KERI_ID             : (TYP11,),
    tagtypes.NEDAP_ID            : (TYP11,),
    tagtypes.NORALSY_ID          : (TYP11,),
    tagtypes.PAC_ID              : (TYP11,),
    tagtypes.PARADOX_ID          : (TYP11,),
    tagtypes.PRESCO_ID           : (TYP11,),
    tagtypes.VISA2000_ID         : (TYP11,),
    tagtypes.HITAG2_ID           : (None,),
    tagtypes.NEXWATCH_ID         : (TYP11,),
}


def get_public_id(infos):
    """
        获取公共的卡片ID标志
    :return:
    """
    typ = infos["type"]
    if typ == tagtypes.HF14A_OTHER:
        # 14a的卡片需要根据UID长度特殊处理
        len_uid = infos["len"]
        if len_uid == 4:
            return types[TYP0][1]
        else:
            return types[TYP1][1]
    else:
        ret = ""
        cgroup = containermap[typ]
        for c in cgroup:
            ret += types[c][1] + ","
        return ret.strip(",")


def get_audio_typ(infos):
    """
        获取音频ID信息组
    :param infos:
    :return:
    """
    typ = infos["type"]
    ret = None

    if typ == tagtypes.HF14A_OTHER:
        print("单独处理 14A 标签的音频")
        # 14a的卡片需要根据UID长度特殊处理
        len_uid = infos["len"]
        if len_uid == 4:
            ret = types[TYP0]
        else:
            ret = types[TYP1]
    else:
        if typ in containermap:
            ret = types[containermap[typ][0]]

    return ret


if __name__ == '__main__':
    print(get_public_id(tagtypes.M1_POSSIBLE_4B))


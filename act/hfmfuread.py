# -*- coding: UTF-8 -*-
import appfiles
import executor
import tagtypes

FILE_MFU_READ = None


def createFileNamePreByType(typ):
    if typ == tagtypes.ULTRALIGHT:
        return appfiles.PREFIX_NAME_UL

    if typ == tagtypes.ULTRALIGHT_C:
        return appfiles.PREFIX_NAME_ULC

    if typ == tagtypes.ULTRALIGHT_EV1:
        return appfiles.PREFIX_NAME_UL_EV1

    if typ == tagtypes.NTAG213_144B:
        return appfiles.PREFIX_NAME_NTAG213

    if typ == tagtypes.NTAG215_504B:
        return appfiles.PREFIX_NAME_NTAG215

    if typ == tagtypes.NTAG216_888B:
        return appfiles.PREFIX_NAME_NTAG216

    return "Unknow"


def read(infos):
    """
        读取MFU卡片并且保存数据
    """
    prefix = createFileNamePreByType(infos["type"])
    uid = infos["uid"]
    s_e = appfiles.isWindows()
    if s_e:
        appfiles.switch_linux()
    global FILE_MFU_READ
    FILE_MFU_READ = appfiles.create_mfu(prefix, uid)
    cmd = " hf mfu dump f " + FILE_MFU_READ
    # 将环境切换回来
    if s_e:
        appfiles.switch_windows()
    # 开始执行命令
    if executor.startPM3Task(cmd, 8888) == -1:
        print("执行mfu dump超时")
        return -1
    # util.printContent()
    # 判断是否选卡成功
    if executor.hasKeyword("iso14443a card select failed"):
        print("未发现任何14a卡片")
        return -1
    # 判断是否放错卡
    if executor.isEmptyContent():
        print("发现了非MFU卡，放错卡了")
        return -1
    # 判断是否读取到了完整的数据
    if executor.hasKeyword("Partial dump created"):
        print("读取到了部分的数据")
        return 2
    else:
        print("读取到了全部MFU的数据")
        return 1
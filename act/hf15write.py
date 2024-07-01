# -*- coding: UTF-8 -*-
import executor
import scan


def write(infos, file):
    """
        写入 ISO15693 ICODE的标签
    :return:
    """
    setuid_cmd = "hf 15 csetuid {}".format(infos["uid"])
    write_cmd = "hf 15 restore f {}.bin".format(file)

    # -----------------------------------------------------------------
    #                  先写数据

    if executor.startPM3Task(write_cmd, 28888) == -1:
        return -10

    if executor.hasKeyword(r"restore failed") or executor.hasKeyword(r"Too many retries"):
        return -10

    if not (executor.hasKeyword(r"Write OK") and executor.hasKeyword("done")):
        return -10

    # -----------------------------------------------------------------
    #                  后写UID

    if executor.startPM3Task(setuid_cmd, 5000) == -1:
        return -10

    if executor.hasKeyword(r"can't read card UID"):
        return -10

    if executor.hasKeyword(r"setting new UID \(ok\)"):
        print("ICode卡号设置成功")
        return 1

    return -10


def verify(infos, file):
    """
        校验写入结果
    :param infos:
    :param file:
    :return:
    """
    uid = infos["uid"]
    # typ = infos["type"]

    infos_new = scan.scan_hfsea()

    scan.set_infos_cache(False)
    if not scan.isTagFound(infos_new):
        return -1
    scan.set_infos_cache(True)

    return uid == infos_new["uid"]  # and typ == infos_new["type"]

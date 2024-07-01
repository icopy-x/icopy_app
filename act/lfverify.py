"""
    专用于校验LF的实现
"""
import os
import platform

import lfem4x05
import lfread
import lft55xx
import scan
import tagtypes


def verify_t55xx(file):
    """
        校验5577
    :param file:
    :return:
    """
    # 首先我们需要先把5577的数据从文件里读出来
    try:
        # 测试开始 <
        # TODO 测试的时候，我们需要作出windows的兼容测试处理
        if platform.system() == "Windows":
            return True
        # 测试结束 >

        # 先校验文件
        if os.path.getsize(file) != 48:
            return -10

        with open(os.path.abspath(file), "rb+") as fd:
            data_hex = bytes.hex(fd.read())

        key = None

        # """
        # 000880B9
        # C9AA000C
        # 80580101
        # 016AC733
        # 05C73B00
        # 86007B02
        # 4E648A44
        # DD440902
        # 000880B9
        # E0152A03
        # 2A4C8BDA
        # """

        # 开始判断，T55XX恒定12个Block
        # 我们需要先判断写入的数据是否是配置了加密块
        is_data_lock = lft55xx.is_b0_lock(data_hex[0:8])
        if is_data_lock:
            key = data_hex[56:64]  # T55XX的秘钥是存放在07块的，也就是坐标为零，第七块。语义上的第8块。
        print(f"当前数据 {data_hex[0:8]} 是否加密了: {is_data_lock}")
        if is_data_lock:
            print("当前数据是加密数据，我们应该使用秘钥进行detect: ", key)

        # 第一次判断，detect阶段，如果数据加密了，但是读出来的卡片没有加密，说明写入失败了
        detect_ret = lft55xx.detectT55XX(key, False)
        if is_data_lock:
            if detect_ret != 3 and detect_ret != 4:
                return -10
        else:  # 如果没有加密，我们需要判断卡片是否没有加密，如果未发现没有加密的卡片，则说明写入失败了
            if detect_ret != 2:
                return -10

        # 第二判断，我们需要进行数据读取，以校验所有写入的块
        dump_text = lft55xx.dumpT55XX_Text(key)
        if dump_text is None:  # 读取失败了，我们可能遇到了一些影响读取的情况
            print("Dump T55xx文本数据时出现了一些卡片丢失或者秘钥错误的异常，不允许继续校验。")
            return -10
        dump_text = dump_text.upper()[0:64]
        data_hex = data_hex.upper()[0:64]
        if dump_text != data_hex:  # 我们校验T55XX的写卡结果的时候，应当跳过page1的校验！
            print("T55xx在Dump的文本数据与Read的数据对比不一致: ")
            print("在线Dump的数据: ", dump_text)
            print("Read保存的数据: ", data_hex)
            return -10

    except Exception as e:
        print("T55XX校验失败", e)
        return -10

    return 1


def verify_em4x05(file):
    """
        校验4x05
    :param file:
    :return:
    """
    # 首先我们需要先把5577的数据从文件里读出来
    try:
        # 测试开始 <
        # TODO 测试的时候，我们需要作出windows的兼容测试处理
        if platform.system() == "Windows":
            return True
        # 测试结束 >

        # 先校验文件
        if os.path.getsize(file) != 64:
            raise Exception("EM4X05文件长度异常" + str(os.path.getsize(file)))

        # 第一步，先把em4x05的数据读取出来
        with open(file, "rb+") as fd:
            data_hex = bytes.hex(fd.read())

        # 取出读取的数据文件中的秘钥
        key = data_hex[16:24]
        # 读取所有的块
        data2_hex = lfem4x05.readBlocks(key)

        if data2_hex is None:
            return False

        # 开始校验，如果校验不通过，则返回错误码
        if not lfem4x05.verify4x05(data_hex, data2_hex):
            return -10

    except Exception as e:
        print("EM4X05校验失败", e)
        # raise e
        return -10

    return 1


def verify(typ, uid_par, raw_par):
    """
        校验数据是否写入成功
    :param typ:
    :param uid_par:
    :param raw_par:
    :return:
    """
    # 回读数据，查看是否写入成功
    # 注意，我们需要关闭信息缓存，
    # 避免更新最先读出来的卡信息
    ret = -10

    if typ in tagtypes.getAllLowCanDump():
        # 特殊一些的，比如T55XX，需要Dump出来才能判断

        if typ == tagtypes.T55X7_ID:
            ret = verify_t55xx(raw_par)

        if typ == tagtypes.EM4305_ID:
            ret = verify_em4x05(raw_par)

    else:
        scan.set_infos_cache(False)
        infos = scan.scan_lfsea()
        # 先判断是否找到了卡
        if scan.isTagFound(infos):
            print("verity() -> 卡片发现")
            # 然后判断类型是否符合
            # 普通的ID卡只需要判断ID或者RAW
            if infos["type"] == typ:
                print("verity() -> 类型一致")
                # 然后使用lfread读取信息再查看卡号或者RAW是否一样
                infos = lfread.READ[typ](None, None)
                uid_e = uid_par == infos["data"]
                raw_e = raw_par == infos["raw"]
                if uid_e or raw_e:  # 当RAW或者UID任何一项符合的时候，判定为写入成功
                    ret = 1
        scan.set_infos_cache(True)

    return ret

"""
    专用于普通LF写卡的实现
"""
import platform
import re

import lft55xx
import tagtypes
import executor

# B0的卡片类型映射
B0_WRITE_MAP = {
    # tagtypes.T55X7_ID: "000880E8",
    # tagtypes.EM410X_ID: "00148040",
    tagtypes.VISA2000_ID: "00148068",  # 可以通过RAW进行克隆√
    tagtypes.VIKING_ID: "00088040",  # 可以通过RAW进行克隆√
    tagtypes.NORALSY_ID: "00088C6A",  # 可以通过RAW进行克隆√
    tagtypes.PRESCO_ID: "00088088",  # 可以通过RAW进行克隆√
    # tagtypes.SECURAKEY_ID: "000C8060",
    # tagtypes.FDXB_ID: "00098080", FDXB必须使用自带的clone指令，它读出来的RAW无法被使用
    tagtypes.HID_PROX_ID: "00107060",  # 可以通过RAW进行克隆√
    # tagtypes.PARADOX_ID: "00107060",
    tagtypes.AWID_ID: "00107060",  # 可以通过RAW进行克隆√
    tagtypes.PYRAMID_ID: "00107080",  # 可以通过RAW进行克隆√
    tagtypes.IO_PROX_ID: "00147040",  # 可以通过RAW进行克隆√
    # tagtypes.INDALA_ID: "00081040",
    # tagtypes.INDALA_ID_LONG: "000810E0",
    tagtypes.KERI_ID: "603E1040",  # 可以通过RAW进行克隆√
    tagtypes.JABLOTRON_ID: "00158040",  # 可以通过RAW进行克隆√
    tagtypes.GPROX_II_ID: "00150060",  # 可以通过RAW进行克隆√
    tagtypes.NEDAP_ID: "907F0042",  # 可以通过RAW进行克隆X
    # tagtypes.PAC_ID: "00080080",
    # tagtypes.GALLAGHER_ID: "00088070",
}

# 可以用自带的clone指令写RAW的卡片类型映射表
RAW_CLONE_MAP = {
    tagtypes.SECURAKEY_ID: "lf securakey clone b {}",
    tagtypes.GALLAGHER_ID: "lf gallagher clone b {}",
    tagtypes.PAC_ID: "lf pac clone b {}",
    tagtypes.PARADOX_ID: "lf paradox clone b {}",
    tagtypes.NEXWATCH_ID: "lf nexwatch clone r {}",
}

"""
    这是clone指令的例程列表
    
    lf awid clone 50 2001 13371337
    
    lf securakey clone b 7FCB400001ADEA5344300000  可用RAW
    
    em: {
        lf em 410x_write 0F0368568B 1
        lf em 4x05_write 1 deadc0de 11223344
    }  可用ID
    
    lf fdx clone c 999 n 112233 e 16a
    
    lf gallagher clone b 0FFD5461A9DA1346B2D1AC32  可用RAW
    
    lf gprox clone 26 123 11223
    lf hid clone l 2006ec0c86
    
    indala: {
        lf indala clone -r a0000000a0002021
        lf indala clone -l -r 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5
    }  可用RAW
    
    lf io clone 01 101 1337
    lf jablotron clone 112233
    
    keri: {
        lf keri clone t i fc 6 cn 12345

        RAW: {
            E0000000
            8001E240
        }     
    }
    
    lf motorola clone a0000000a0002021   可用RAW
    
    lf nedap clone s 1 c 123 i 12345
    
    lf nexwatch clone r 5600000000213C9F8F150C   可用RAW
    
    lf noralsy clone 112233
    
    lf pac clone b FF2049906D8511C593155B56D5B2649F   可用RAW
    lf paradox clone b 0f55555695596a6a9999a59a   可用RAW
    
    lf presco clone d 123456789
    lf pyramid clone 123 11223
    
    lf viking clone 1A337 Q5 -- encode for Q5/T5555
    lf visa2000 clone 112233 q5      -- encode for Q5/T5555
"""


def write_fdx_par(animal_id):
    """
        根据传入的参数来写入卡片
    :param animal_id:
    :return:
    """
    cn = str(animal_id).split("-")
    c = cn[0]
    n = cn[1]
    cmd = "lf fdx clone c {} n {}".format(c, n)
    if executor.startPM3Task(cmd, 5000) != -1:
        return 1
    else:
        return -1


def write_em410x(em410x_id):
    """
        写标准ID卡
    :param em410x_id:
    :return:
    """
    cmd = "lf em 410x_write {} 1".format(em410x_id)
    if executor.startPM3Task(cmd, 5000) != -1:
        return 1
    else:
        return -1


def write_hid(hid_id):
    """
        写标准ID卡
    :param hid_id:
    :return:
    """
    # 22006ec0c86
    if len(hid_id) <= 11:
        hid_id = " " + hid_id
    else:
        hid_id = " l " + hid_id

    cmd = "lf hid clone" + hid_id
    if executor.startPM3Task(cmd, 5000) != -1:
        return 1
    else:
        return -1


def write_indala(raw):
    # lf indala clone -r {}
    # a0000000a0002021
    # 80000001b23523a6c2e31eba3cbee4afb3c6ad1fcf649393928c14e5
    if len(raw) > 16:  # 长ID的INDALA
        long_opt = "-l"
    else:
        long_opt = ""
    cmd = "lf indala clone {} -r {}".format(long_opt, raw)
    if executor.startPM3Task(cmd, 5000) != -1:
        return 1
    else:
        return -1


def write_nedap(raw):
    """
        1、写数据
        2、写密钥
        3、写配置块
    """
    # 第一步，先写数据
    if not write_raw_t55xx(raw):
        return -10
    # 第二步，手动进行配置块配置与加密
    b0 = B0_WRITE_MAP[tagtypes.NEDAP_ID]
    if not lft55xx.lock(b0=b0, check_detect=False):  # lock的时候进行自定义B0，并且免去detect流程
        return -10
    return 1


# 可以用传入的参数来单独写
PAR_CLONE_MAP = {
    tagtypes.FDXB_ID: write_fdx_par,
    tagtypes.EM410X_ID: write_em410x,
    tagtypes.HID_PROX_ID: write_hid,
    tagtypes.INDALA_ID: write_indala,
    tagtypes.NEDAP_ID: write_nedap,
}


def write_b0_need(typ, key=None):
    """
        写B0配置块，如果需要
    :return:
    """
    if typ in B0_WRITE_MAP:
        # 取出配置位
        config_block = B0_WRITE_MAP[typ]
        # 拼凑密钥
        base_cmd = "lf t55xx write b 0 d " + config_block
        if key is not None:
            base_cmd += " p " + key
        # 执行指令，写入B0
        executor.startPM3Task(base_cmd, 5000)

    return None


def write_raw_clone(typ, raw):
    """
        使用卡片自带的clone指令写RAW，如果支持
    :param typ:
    :param raw:
    :return:
    """
    if typ in RAW_CLONE_MAP:
        cmd = RAW_CLONE_MAP[typ].format(raw)
        return executor.startPM3Task(cmd, 8000) != -1
    return False


def write_raw_t55xx(raw):
    """
        全部使用t55xx的指令进行写卡
        1、先写B0，
        2、后写读出来的RAW
    :param raw:
    :return:
    """
    if len(raw) % 8 != 0:
        print("RAW的长度不是8的整数倍，不符合8B1B的规范，不允许操作。")
        return False
    # 先进行分段
    # 00010101
    # 02439dd9
    # a8d3c85b
    # 91b6d389
    str_group = re.findall(r".{8}", raw)
    if len(str_group) < 1:
        print("RAW无法被分段为最少一个块")
        return False
    # 分段写入
    for index in range(0, len(str_group)):

        failed = True

        for count in range(2):
            cmd = "lf t55xx write b {} d {}".format(index + 1, str_group[index])
            if executor.startPM3Task(cmd, 8000) != -1:
                failed = False
                break

        if failed:
            return False

    return True


def write_raw(typ, raw, key=None):
    """
        写入RAW，根据用户给定的类型
    :param raw:
    :param typ:
    :param key:
    :return:
    """
    raw = raw.replace(" ", "")
    # 然后看看能不能调用指令直接写RAW
    if not write_raw_clone(typ, raw):
        if not write_raw_t55xx(raw):
            return -10
    # 看看需不需要写B0，需要的话写一波
    write_b0_need(typ, key)
    print("低频卡写RAW完成。")
    return 1


def write_dump_t55xx(file, key=None):
    """
        写T55XX的Dump
    :param file:
    :param key:
    :return:
    """
    detect_ret = lft55xx.detectT55XX(key, False)
    if detect_ret == 2 or detect_ret == 4:  # 加密但是已知秘钥或者没有加密
        print("开始进行T55XX容器卡对拷。")
        cmd = "lf t55xx restore f " + file
        if key is not None:
            cmd += " p " + key
        print("将执行的指令: ", cmd)
        if executor.startPM3Task(cmd, 5000) != -1:
            return 1
    return -9


def write_block_em4x05(blocks, start, end, key):
    # 第三步，从尾部开始写
    base_cmd = "lf em 4x05_write {} {} {}"
    for block in range(start, end):

        print("当前写的块: ", block)

        # lf em 4x05_write 1 deadc0de 11223344
        if key is None:
            key = ""
        cmd = base_cmd.format(block, blocks[block], key)

        # 在N次重试中写入块
        failed = True
        for count in range(3):
            if executor.startPM3Task(cmd, 5000) != -1:
                if executor.hasKeyword("Success writing to tag") or executor.hasKeyword("Done"):
                    failed = False
                    break

        if failed:
            return -10
    return 1


def write_dump_em4x05(file, key=None):
    """
        写EM4X05的Dump
    :param file:
    :param key:
    :return:
    """
    try:
        if platform.system() == "Windows":
            data_hex = executor.startPM3Plat(f"sudo xxd -ps {file}")
            data_hex = re.sub(r"\s+", '', data_hex)
            print("通过远程执行器读取到的文件: ", data_hex)
        else:
            # 第一步，先把em4x05的数据读取出来
            fd = open(file, "rb+")
            data_hex = bytes.hex(fd.read())
            fd.close()
        if len(data_hex) != 128: raise Exception("EM4x05的数据长度异常")

        # 第二步，进行分段
        data_group = re.findall(r".{8}", data_hex)

        print("开始写入")

        ret = write_block_em4x05(data_group, 0, 4, key)
        if ret != 1:
            print("写前4块出现异常")
            return ret

        ret = write_block_em4x05(data_group, 5, 14, key)
        if ret != 1:
            print("写 5 -13 块出现异常")
            return ret

        ret = write_block_em4x05(data_group, 4, 5, key)
        if ret != 1:
            print("写第 04 块出现异常")
            return ret

        # 注意，我们需要重复写02块，因为配置了04块后，
        # 02块会被清空为默认的 00000000
        ret = write_block_em4x05(data_group, 2, 3, "00000000")
        if ret != 1:
            print("写第 02 块出现异常")
            return ret

        # 注意，写 14 -15 块必须要放在最后写
        ret = write_block_em4x05(data_group, 14, 16, key)
        if ret != 1:
            print("写 14 - 15 块出现异常")
            return ret

    except Exception as e:
        print("写em4x05的时候出错了: ", e)
        return -10

    return 1


# 可以写dump的卡片的映射表
DUMP_WRITE_MAP = {
    tagtypes.T55X7_ID: write_dump_t55xx,
    tagtypes.EM4305_ID: write_dump_em4x05,
}


def write(listener, typ, infos, raw_par, key=None):
    """
        根据传入的参数决定写卡方式
    :param listener: 写卡回调
    :param infos: 读取的卡片的信息
    :param typ: 读取的卡片的类型
    :param raw_par: 读取的卡片的数据
    :param key: 卡片写入需要的秘钥
    :return:
    """

    lock_unavailable_list = [
        tagtypes.T55X7_ID,
        tagtypes.EM4305_ID,
        tagtypes.NEDAP_ID,
    ]

    # 不是EM4X05卡片的情况下
    # 必须清空卡片，我们只支持空卡。
    if typ is not tagtypes.EM4305_ID and not lft55xx.wipe(listener):
        return -9

    lft55xx.call_listener(listener, 100, 20, "writing")

    if typ in PAR_CLONE_MAP:
        # 非通用RAW写卡逻辑，使用lf t55xx的写卡指令或者特殊的clone指令
        ret = PAR_CLONE_MAP[typ](raw_par)
    elif typ in DUMP_WRITE_MAP:
        # 非通用DUMP写卡逻辑，使用各自的dump的restore指令
        ret = DUMP_WRITE_MAP[typ](raw_par, key)
    else:
        # 通用的RAW写卡逻辑，使用lf t55xx的写卡指令或者通用的clone指令
        ret = write_raw(typ, raw_par, key)

    lft55xx.call_listener(listener, 100, 50, "writing")

    if ret != 1:
        print("write() -> 写低频卡失败，返回值是: ", ret)
        return ret

    # 写卡后，需要看情况上锁
    if typ not in lock_unavailable_list:
        # 如果不是indala长卡号，则需要写秘钥块
        # 长卡号的Indala，我们只能配置配置块使能加密，而不能写b7
        if not lft55xx.lock(not (typ is tagtypes.INDALA_ID and len(raw_par) >= 56)):
            # return -9
            print("警告，加密失败，有可能出现了未知的异常。")

    lft55xx.call_listener(listener, 100, 80, "writing")

    return ret

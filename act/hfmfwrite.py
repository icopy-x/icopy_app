"""
    MifareClassic 标签写卡
"""
import base64
import hashlib
import os
import platform
import re
import subprocess

from Crypto.Cipher import AES

import executor
import mifare
import scan
import tagtypes
import hfmfread
import hfmfkeys
import version


def tagChk1(infos, file, newinfos):
    """
        第一项检测
    :return:
    """
    typ = infos["type"]

    # 测试开始 <
    if platform.system() == "Windows":
        print("windows测试下，自动切换为高版本的函数")
        return True
    # 测试结束 >

    def init_tag():
        """
            低版本的卡片初始化函数
            适用于 ICopy-X & ICopy-XR
        :return:
        """
        if typ == tagtypes.M1_S50_1K_4B or typ == tagtypes.M1_MINI:
            # 无法控制渠道的标签
            block = hfmfread.readBlock(3, hfmfread.A, "E00000000000")
            if isinstance(block, str):
                return True
            else:
                return False

        # 其他的卡，我们直接进行返回True，不检测
        return True

    def init_tag1():
        """
            适用于 ICopy-X 的UK版本的初始化校验过程
        :return:
        """
        # 第一步，先判断是否是M1 1K4B
        if typ == tagtypes.M1_S50_1K_4B:

            # 1、如果是UID后门卡，我们直接返回False，因为UK定制清单不允许M11K4B除了写自家的
            # FUID卡之外的其他卡
            if "gen1a" in newinfos and newinfos["gen1a"]:
                print("错误负1")
                return False

            # Ok，通过上面的逻辑，我们可以确认用户不是用UID卡来写的了
            # 2、不允许专门定制的卡号之外的卡进行写卡
            if newinfos['uid'] != "AA55C396":
                print("错误0")
                return False

            # 3、第三，我们需要进行第三块的写入，
            # 如果能写入成功，则是可以写入UID的卡
            datas = read_blocks_4file(file)
            if datas is None:
                # 读取卡片数据有问题
                return False
            if len(datas) != 64:
                # 卡片数据有问题
                return False
            # 取出0块，也就是厂商块
            block0_origin = datas[0]
            # 先写入厂商块
            if not write_block(0, mifare.A, mifare.EMPTY_KEY, block0_origin):
                # 写入失败，可能是有一些问题，但我们不允许写入失败的卡进行接下来的步骤
                print("错误1")
                return False

            # 4、并且我们再写入一次其他的卡号，如果成功，则说明这个卡有问题，不是专门定制的卡
            # 再次尝试写入其他的数据用来做FUID验证，避免客户使用的是CUID
            block0_empty = hfmfread.createManufacturerBlock({
                "uid": "FF" * int(newinfos["len"]),
                "sak": newinfos["sak"],
                "atqa": newinfos["atqa"],
                "len": newinfos["len"],
            })
            # 此次写入可能会失败，这里我们不做处理
            if write_block(0, mifare.A, mifare.EMPTY_KEY, block0_empty):
                # 第二次写入0块必须要失败，成功了就是卡片有问题
                print("错误2")
                return False

            # 5、回读数据
            block0_read = hfmfread.readBlock(0, mifare.A, mifare.EMPTY_KEY)
            if not isinstance(block0_read, str):
                # 读取失败，说明卡片有毛病，既然有毛病就不让通过
                print("错误3")
                return False
            # 全部都转换为小写，然后进行比较
            if block0_origin.lower() != block0_read.lower():
                print("错误4")
                return False

            # 6、最终，如果我们的数据校验完成了
            # 经过了第二次乱写厂商块后，如果原先第一次被写入的数据与现在读出来的数据相同，
            # 则校验成功，否则校验失败。
            return True

        # 如果不是M1 1K4B的卡，直接通过验证
        return True

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
            "x": init_tag,  # 低配需要验证我司卡片
            "xr": init_tag,  # 中配同上亦然
            "zh": lambda: True,  # 中文版不需要验证，直接返回正确
            "xs": lambda: True,  # 高配同上亦然
            "uk": init_tag1,  # 英国定制版本我们需要进行1K4B FUID卡的专卡处理
            "xsc": lambda: True,  # 中文定制权限全开
        }

        # 解密UID
        aes_obj = AES.new(
            ret.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        return maps[i[3]]()
    except Exception as e:
        print("无法通过验证，必须使用我司的卡片: ", e)
        return False
    # 验证结束 >


def tagChk2(infos, newinfos):
    """
        第二项检测
    :param newinfos:
    :param infos:
    :return:
    """
    if scan.isTagFound(newinfos) and not scan.isTagMulti(newinfos):
        if infos["len"] == newinfos["len"]:  # 先检测卡号长度
            return True
    return False


def tagChk3(infos, newinfos):
    """
        第三项检测
    :param newinfos:
    :param infos:
    :return:
    """
    if "gen1a" in newinfos and newinfos["gen1a"]:
        origin_type = infos["type"]
        is_m1_4b = (origin_type == tagtypes.M1_S50_1K_4B) or (origin_type == tagtypes.M1_POSSIBLE_4B)
        is_14a_4b = origin_type == tagtypes.HF14A_OTHER and newinfos["len"] == 4
        if is_m1_4b or is_14a_4b:
            return 1  # 只有1K卡有UID，我们目前支持的
        return -9  # 原卡不是1K4B类型，放UID卡是错的
    return 0  # 如果容器卡不是UID卡，那么我们就可以默认是CUID卡


def tagChk4(infos):
    """
        第四项检测
    :return:
    """

    # """
    #     0：hf mf rdbl 4 A {FFFFFFFFFFFF}
    #     1：hf mf rdbl 63 A {FFFFFFFFFFFF}
    #     2：hf mf rdbl 127 A {FFFFFFFFFFFF}
    #     4：hf mf rdbl 255 A {FFFFFFFFFFFF}
    # """

    size = hfmfread.sizeGuess(infos["type"])
    if size == mifare.SIZE_1K:
        block_index = 63
    elif size == mifare.SIZE_2K:
        block_index = 127
    elif size == mifare.SIZE_4K:
        block_index = 255
    elif size == mifare.SIZE_MINI:
        block_index = 4
    else:
        print("容量检测异常，没有匹配的容量！")
        return False

    sector = mifare.blockToSector(block_index)
    print("取出的扇区: ", sector)
    key = hfmfkeys.getKey4Map(sector, hfmfkeys.A)
    print("取出来的秘钥: ", key)
    block_data = hfmfread.readBlock(block_index, hfmfread.A, key)

    return isinstance(block_data, str)  # 判断是否是有效的数据


def read_blocks_4file(file: str):
    """
        从文件里读取所有的块
    :param file:
    :return:
    """
    ret_list = list()
    # 文件路径修正，非常重要
    if not file.endswith(".bin"):
        file += ".bin"
    try:
        # 读取文件
        with open(file, "rb+") as fd:
            data = fd.read()

        # 按照16byte一个block来分割
        count = 0
        size = 16
        while count + size <= len(data):
            ret_list.append(data[count:count + size].hex().upper())
            count += size

        # 校验块数是否正确
        if len(ret_list) < 4 or len(ret_list) > mifare.MAX_BLOCK_COUNT:
            return None

        return ret_list
    except Exception as e:
        print("读取出现问题: ", e)
        print("文件路径: ", os.path.abspath(file))
    return None


def start_wrbl_cmd(cmd):
    """
        执行写块的指令
    :param cmd:
    :return:
    """
    if executor.startPM3Task(cmd, 5888) == -1:
        return False
    if executor.hasKeyword("isOk:01"):
        return True
    return False


def write_block(block, typ, key, data, retry=3):
    """
        写单块
    :return:
    """
    temp = "hf mf wrbl {} {} {} {}"
    cmds = []

    # 生成写普通卡单块指令
    # hf mf wrbl 块 秘钥类型 秘钥 数据
    if isinstance(key, str):
        cmds.append(temp.format(block, typ, key, data))
    elif isinstance(key, list):
        for k in key:
            cmds.append(temp.format(block, typ, k, data))
    else:
        raise Exception("不被支持的秘钥格式: " + type(key))

    # 在循环中进行写卡，如果成功的话，会直接返回，否则的话，自动重试N次
    for count in range(retry):
        # 迭代所有的写卡指令
        for cmd in cmds:
            # 如果写入成功，直接结束任务，
            # 返回成功写入的结果
            if start_wrbl_cmd(cmd):
                return True

    return False


def call_progress(listener, max_value, progress):
    """
        回调写卡进度
    :param listener: 
    :param max_value:
    :param progress:
    :return:
    """
    listener(
        {
            "max": max_value,
            "progress": progress,
        }
    )


def gen1afreeze():
    """
        封锁UFUID的卡
    :return:
    """
    cmds = [
        "hf 14a raw -p -a -b 7 40",
        "hf 14a raw -p -a 43",
        "hf 14a raw -c -p -a e000",
        "hf 14a raw -c -p -a e100",
        "hf 14a raw -c -p -a 85000000000000000000000000000008",
        "hf 14a raw -c -a 5000",
    ]

    for cmd in cmds:
        if executor.startPM3Task(cmd, 8888) == -1:
            print("执行器出现异常，封卡失败。")
            return

    print("命令执行成功，封卡成功。")


def write_with_standard(listener, file_or_datas, size):
    """
        写标准M1卡
    :return:
    """
    # 读出文件
    if isinstance(file_or_datas, list):
        datas = file_or_datas  # 传过来的貌似直接就是可用的数据组，那我们就不需要读取了
    else:
        datas = read_blocks_4file(file_or_datas)
    write_success_list = []
    if datas is None:
        print("读取出来的数据是空的！")
        return False
    try:
        call_progress(listener, len(datas), 0)

        def write_internal(write_data=True):
            """
                内部实现的写块
            :param write_data:
            :return:
            """
            sector_max = mifare.getSectorCount(size)
            for sector in range(sector_max - 1, -1, -1):
                call_progress(listener, len(datas), len(write_success_list))
                # 取出该扇区的秘钥A
                keyA = hfmfkeys.getKey4Map(sector, hfmfkeys.A)
                # 取出该扇区的秘钥B
                keyB = hfmfkeys.getKey4Map(sector, hfmfkeys.B)
                # 取出该扇区的块计数
                block_count = mifare.getBlockCountInSector(sector)
                # 开始单独写某一块
                start_block = mifare.sectorToBlock(sector)
                if write_data:
                    # 迭代写入数据
                    for block in range(start_block, start_block + block_count - 1):
                        print("开始写数据块: ", block)
                        aw = write_block(block, mifare.A, keyA, datas[block])
                        if aw:
                            write_success_list.append(block)
                            continue
                        bw = write_block(block, mifare.B, keyB, datas[block])
                        if bw:
                            write_success_list.append(block)
                            continue
                        if block == 0:
                            write_success_list.append(block)
                            continue  # 0块写不成功可以忽略
                        else:
                            return False  # 其他块写不成功直接返回失败
                else:
                    block = mifare.get_trailer_block(start_block)
                    print("开始写尾部块: ", block)
                    aw = write_block(block, mifare.A, keyA, datas[block])
                    if aw:
                        write_success_list.append(block)
                        continue
                    bw = write_block(block, mifare.B, keyB, datas[block])
                    if bw:
                        write_success_list.append(block)
                        continue
                    return False  # 但凡全部写不成功，直接返回失败
            return True  # 全部写卡过程无异常，返回成功

        # 先写数据
        if not write_internal(True):
            print("写数据块失败")
            return False
        # 再写密码
        if not write_internal(False):
            print("写密码块失败")
            return False

        call_progress(listener, len(datas), len(datas), )

        # 全部成功
        return True
    except Exception as e:
        print("写卡出现异常: ", e)
    return False


def write_with_gen1a(file):
    """
        写GEN1A的标签
    :return:
    """
    if not str(file).endswith(".bin"):
        file += ".bin"

    cmd = "hf mf cload b {}".format(file)

    for retry in range(3):
        # 执行指令
        if executor.startPM3Task(cmd, 8888) == -1:
            return False

        if executor.hasKeyword(r"Can't set magic card block"):
            return False

        # 判断是否加载成功
        if executor.hasKeyword(r"Card loaded \d+ blocks from file"):
            return True

    return False


def write_with_standard_only_uid(infos):
    # 只写0块，尝试写
    # 取出该扇区的秘钥A
    key_a = hfmfkeys.getKey4Map(0, hfmfkeys.A)
    # 取出该扇区的秘钥B
    key_b = hfmfkeys.getKey4Map(0, hfmfkeys.B)
    if write_block(0, mifare.A, key_a, hfmfread.createManufacturerBlock(infos)):
        return True
    if write_block(0, mifare.B, key_b, hfmfread.createManufacturerBlock(infos)):
        return True
    return False


def write_with_gen1a_only_uid(infos):
    if infos["len"] != 4:
        print("UID后门卡目前只支持4B的UID长度，你的原卡长度是: ", infos["len"])
        return False
    cmd = "hf mf csetuid {} {} {} w".format(
        infos["uid"],
        infos["atqa"],
        infos["sak"],
    )
    if executor.startPM3Task(cmd, 5888) == -1:
        return False
    if executor.hasKeyword("Old UID") and executor.hasKeyword("New UID"):
        return True
    return False


def write_common(infos, file, write_on_standard, write_on_magic):
    """
        通用写入函数
    :param file: 将要写入的数据文件
    :param infos: 卡片原本的信息
    :param write_on_standard: 标准卡写入实现函数
    :param write_on_magic:  UID后门卡写入实现函数
    :return:
    """
    typ = infos["type"]
    newinfos = scan.scan_14a()

    if not tagChk1(infos, file, newinfos):  # 第一项检测，定制专卡，失败
        print("第一项检测失败")
        return -9

    if not tagChk2(infos, newinfos):  # 第二项检测，卡号长度，失败
        print("第二项检测失败")
        return -9

    ret = tagChk3(infos, newinfos)  # 第三项检测，UID后门检测

    if ret == 0:  # 不是UID卡。我们应当进入fhck流程
        size = hfmfread.sizeGuess(typ)
        hfmfkeys.fchks(infos, size, False)
        if hfmfkeys.hasAllKeys(size):
            print("发现了完整的容器卡秘钥，将判断容量。")
            if tagChk4(infos):
                print("普通卡容量检测通过")
            else:
                print("普通卡容量检测失败")
                return -9
            if write_on_standard():
                print("普通卡写卡成功")
                return 1
            else:
                print("普通卡写卡失败")
        else:
            print("加密卡无法写入。")
            return -11
    elif ret < 0:
        print("是UID卡但是不符合原卡和容器卡的可写映射类型")
        return ret  # 是UID卡但是不符合原卡和容器卡的可写映射类型
    else:
        if write_on_magic():
            gen1afreeze()
            print("UID后门卡写卡成功")
            return 1
        else:
            print("UID后门卡写卡失败")

    return -10


def write_unlimited(infos, write_on_standard, write_on_magic):
    """
        特殊的，无限制的标签写入函数
    :param infos: 卡片原本的信息
    :param write_on_standard: 标准卡写入实现函数
    :param write_on_magic:  UID后门卡写入实现函数
    :return:
    """
    typ = infos["type"]
    newinfos = scan.scan_14a()

    if not tagChk2(infos, newinfos):  # 第一项检测，卡号长度，失败
        print("第二项检测失败")
        return -9

    ret = tagChk3(infos, newinfos)  # 第二项检测，UID后门检测

    if ret == 0:  # 不是UID卡。我们应当进入fhck流程
        size = hfmfread.sizeGuess(typ)
        hfmfkeys.fchks(infos, size, False)
        if hfmfkeys.hasAllKeys(size):
            print("发现了完整的容器卡秘钥，将判断容量。")

            if tagChk4(infos):
                print("普通卡容量检测通过")
            else:
                print("普通卡容量检测失败")
                return -9

            if write_on_standard():
                print("普通卡写卡成功")
                return 1
            else:
                print("普通卡写卡失败")
        else:
            print("加密卡无法写入。")
            return -11
    elif ret < 0:
        print("是UID卡但是不符合原卡和容器卡的可写映射类型")
        return ret  # 是UID卡但是不符合原卡和容器卡的可写映射类型
    else:
        if write_on_magic():
            print("UID后门卡写卡成功")
            return 1
        else:
            print("UID后门卡写卡失败")

    # 这个返回值是写卡失败都会返回的
    # 为何会写卡失败呢？
    # 第一，可能是卡片的控制位损坏，导致数据无法写入
    # 第二，可能是卡片的放置位置不是很理想，信号不稳定导致写入失败
    return -10


def write_only_uid(infos):
    """
        只写入M1卡片
    :param infos:
    :return:
    """

    def write_on_standard():
        return write_with_standard_only_uid(infos)

    def write_on_magic():
        return write_with_gen1a_only_uid(infos)

    return write_common(infos, None, write_on_standard, write_on_magic)


def write_only_uid_unlimited(infos):
    """
        用来写手环的媒介容器卡的实现逻辑
    :param infos:
    :return:
    """

    def write_on_standard():
        return write_with_standard_only_uid(infos)

    def write_on_magic():
        return write_with_gen1a_only_uid(infos)

    return write_unlimited(infos, write_on_standard, write_on_magic)


def write_only_blank(listener, typ, file_or_datas):
    """
        写空白卡，对指定的数据
    :return:
    """
    size = hfmfread.sizeGuess(typ)

    # 读出文件
    if isinstance(file_or_datas, list):
        datas = file_or_datas  # 传过来的貌似直接就是可用的数据组，那我们就不需要读取了
    else:
        datas = read_blocks_4file(file_or_datas)

    write_success_list = []

    if datas is None:
        print("读取出来的数据是空的！")
        return False
    try:
        call_progress(listener, len(datas), 0)

        def write_internal(write_data=True):
            """
                内部实现的写块
            :param write_data:
            :return:
            """
            sector_max = mifare.getSectorCount(size)
            for sector in range(sector_max - 1, -1, -1):
                call_progress(listener, len(datas), len(write_success_list))

                # 取出该扇区的块计数
                block_count = mifare.getBlockCountInSector(sector)
                # 起始块，位于每个扇区的起始位置
                start_block = mifare.sectorToBlock(sector)
                # 尾部块，存放秘钥和控制位
                end_block = mifare.get_trailer_block(start_block)
                end_block_data = datas[end_block]

                # 取出该扇区的秘钥A
                key_a = [
                    "FFFFFFFFFFFF",
                    end_block_data[0:12]
                ]
                # 取出该扇区的秘钥B
                key_b = [
                    "FFFFFFFFFFFF",
                    end_block_data[20:32]
                ]

                # 开始写入数据块或者尾部块
                if write_data:
                    # 迭代写入数据
                    for block in range(start_block, start_block + block_count - 1):
                        print("开始写数据块: ", block)
                        retry = (10 if block != 0 else 3)

                        # A秘钥写数据
                        aw = write_block(block, mifare.A, key_a, datas[block], retry)
                        if aw:
                            write_success_list.append(block)
                            continue

                        # B秘钥写数据
                        bw = write_block(block, mifare.B, key_b, datas[block], retry)
                        if bw:
                            write_success_list.append(block)
                            continue

                        # BLOCK0不计入写数据的成功与否的判断结果
                        if block == 0:
                            write_success_list.append(block)
                            continue  # 0块写不成功可以忽略
                        else:
                            return False  # 其他块写不成功直接返回失败
                else:
                    print("开始写尾部块: ", end_block)
                    # A秘钥写尾部块
                    aw = write_block(end_block, mifare.A, key_a, end_block_data, 10)
                    if aw:
                        write_success_list.append(end_block)
                        continue

                    # B秘钥写尾部块
                    bw = write_block(end_block, mifare.B, key_b, end_block_data, 10)
                    if bw:
                        write_success_list.append(end_block)
                        continue

                    return False  # 但凡全部写不成功，直接返回失败

            return True  # 全部写卡过程无异常，返回成功

        # 先写数据
        if not write_internal(True):
            print("写数据块失败")
            return False
        # 再写密码
        if not write_internal(False):
            print("写密码块失败")
            return False

        call_progress(listener, len(datas), len(datas), )

        # 全部成功
        return True
    except Exception as e:
        print("写卡出现异常: ", e)
    return False


def verify_only_uid(infos):
    """
        校验M1卡写入结果
    :return:
    """

    newinfos = scan.scan_14a()

    if scan.isTagFound(newinfos):
        if newinfos["uid"] == infos["uid"]:
            return 1

    return -1


def write(listener, infos, bundle):
    """
        写入M1卡片
    :return:
    """
    file = bundle
    typ = infos["type"]

    def write_on_standard():
        return write_with_standard(listener, file, hfmfread.sizeGuess(typ))

    def write_on_magic():
        return write_with_gen1a(file)

    return write_common(infos, file, write_on_standard, write_on_magic)


def verify(infos, bundle):
    """
        校验M1卡写入结果
    :return:
    """
    return verify_only_uid(infos)  # 目前我们只需要校验UID

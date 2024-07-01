# -*- coding: UTF-8 -*-
import hficlass
import tagtypes
import executor

# 定义了写iclass legacy需要写的block
ICLASS_L_WRITE_BLOCK = [
    6, 7, 8, 9, 10, 11, 12,
    13, 14, 15, 16, 17, 18
]

# 定义了写iclass elite需要写的block
ICLASS_E_WRITE_BLOCK = [
    6, 7, 8, 9, 10, 11, 12,
    13, 14, 15, 16, 17, 18
]


def getNeedWriteBlock(typ):
    """
        获得对应的iclass需要写的数据块
    :param typ:
    :return:
    """
    if typ == tagtypes.ICLASS_LEGACY:
        return ICLASS_L_WRITE_BLOCK
    else:
        return ICLASS_E_WRITE_BLOCK


def readBlockHex(file, block, block_size=8):
    """
        从iclass的dump中读取指定的块
    :param block_size:
    :param file:
    :param block:
    :return:
    """
    try:
        with open(file, "rb+") as fd:
            # 读取所有的字节数据
            data = fd.read()
            if len(data) == 0:
                raise Exception("IClass数据文件长度为0")
            # 进行索引定位
            start = block * block_size
            end = start + block_size
            return data[start:end].hex().upper()
    except Exception as e:
        print("读取出错: ", e)
        return None


def writeDataBlock(typ, block, data, key):
    """
        写入数据到扇区
    :return:
    """
    if data is None:
        return -10

    # 将要执行写入的指令
    cmd = "hf iclass wrbl -b {} -d {} -k {}".format(
        block,  # 我们移植了新版本的wrbl，因此参数的格式也有所变化，此处使用十进制
        data,
        key,
    )

    # print("将执行的ICLASS写卡指令: ", cmd)

    if typ == tagtypes.ICLASS_ELITE:
        cmd += " --elite"

    # 执行
    if executor.startPM3Task(cmd, 5888) == -1:
        return -10
    if executor.hasKeyword("Writing failed"):
        return -10
    if executor.hasKeyword(r"successful"):
        return 1

    return -10


def writeDataBlocks(typ, file_or_dict, key="2020666666668888"):
    """
        写入数据到各个扇区
        1、如果传入的是一个文件路径字符串，则我们需要读取数据进行逐个写入
        2、如果传入的是一个字典，那么这个字典应该是 {index: data, }规范的
            这样我们可以根据key的index写入data的值数据
    :return:
    """
    if isinstance(file_or_dict, dict):
        for block in file_or_dict.keys():
            print("ICLASS将写入扇区: ", block)
            if writeDataBlock(typ, block, file_or_dict[block], key) != 1:
                print("有扇区写入失败: ", block)
                return -10
    elif isinstance(file_or_dict, str):
        for block in getNeedWriteBlock(typ):
            print("ICLASS将写入扇区: ", block)
            if writeDataBlock(typ, block, readBlockHex(file_or_dict, block), key) != 1:
                print("有扇区写入失败: ", block)
                return -10
    else:
        print("不支持的iclass写卡数据格式: ", type(file_or_dict))
        return -10
    print("写入数据到卡片（从文件中）成功！")
    return 1


def calcNewKey(typ, oldkey, newkey, l2e=False):
    """
        计算新秘钥需要的block数据
    :param typ: 当前要写的容器卡的类型
    :param oldkey: 旧的密钥
    :param newkey: 新的密钥
    :param l2e: 是否需要将Legacy写为Elite
    :return: 计算到的校验值
    """
    cmd = "hf iclass calcnewkey o {} n {}".format(oldkey, newkey)
    if typ == tagtypes.ICLASS_ELITE:  # 原本就是Elite的卡的密钥需要更新的话，需要带 ee 参数
        cmd += " ee"
    elif typ == tagtypes.ICLASS_LEGACY and l2e:  # Legacy卡的更新为Elite的加密类型的话，需要带 e 参数
        cmd += " e"
    elif typ == tagtypes.ICLASS_LEGACY:  # Legacy更改自己的密钥的话，不需要带任何 e 参数
        pass

    # 警告一些操作
    if typ == tagtypes.ICLASS_ELITE and l2e:
        print("警告：您当前选择了操作Elite卡片，但是又想将Legacy卡片转为Elite卡片，这是一个互斥的操作。")

    if executor.startPM3Task(cmd, 5888) == -1:
        return -10
    if executor.hasKeyword("failed tag-select"):
        return -10
    if executor.hasKeyword("Xor div key :"):
        # 86 49 08 97 58 2C BA 36
        return executor.getContentFromRegexG("Xor div key : ([0-9A-Fa-f ]+)", 1).replace(" ", "")
    return None


def writePassword(typ, new_key, oldkey="2020666666668888", l2e=False):
    """
        写入秘钥到03扇区
    :return:
    """
    # 先计算
    key_calc_result = calcNewKey(typ, oldkey, new_key, l2e)
    # 计算失败，则不能继续写入
    if key_calc_result is None:
        return -10
    return writeDataBlock(typ, 3, key_calc_result, oldkey)


def append_suffix(file):
    """
        追加文件后缀
    :param file:
    :return:
    """
    suffix = ".bin"
    if not str(file).endswith(suffix):
        return file + suffix
    return file


def make_se_data(blk7):
    """
        生成se卡韦根码模拟的legacy卡数据
    :param blk7:
    :return:
    """
    return {
        6: "000000000000E014",
        7: blk7,
        8: "0000000000000000",
        9: "0000000000000000",
    }


def write(infos, bundle):
    """
        写入iclass卡片
    :return:
    """
    typ = infos["type"]

    # 我们现在在读普通的iclass，
    # 所以可以拿到dump文件进行写卡
    if (typ == tagtypes.ICLASS_LEGACY or
            typ == tagtypes.ICLASS_ELITE):

        key = bundle["key"]
        file = bundle["file"]

        # 第一，先写入数据
        if writeDataBlocks(typ, append_suffix(file)) == 1:
            # 第二，写入更改秘钥
            return writePassword(typ, key)

        print("iclass数据文件写入失败！")

    else:
        # 不是上述两种卡的话
        # PM3现在暂时无法读写，所以我们需要
        # 外置读头，并且写卡时写卡的韦根码
        blocks = make_se_data(bundle['blck7'])
        if writeDataBlocks(typ, blocks, "6666202066668888") == 1:
            # 第二，写入更改秘钥
            # 此处我们更改为默认的legacy秘钥，因为我们是在legacy的基础上
            # 模拟一个SE卡片输出的韦根
            return writePassword(typ, new_key="AFA785A7DAB33378", oldkey="6666202066668888")

        print("iclass数据文件写入失败！")

    return -10


def verify(infos, bundle):
    """
        校验iclass卡片
    :return:
    """
    typ = infos["type"]

    # 我们现在在读普通的iclass，
    # 所以可以拿到dump文件进行写卡
    if (typ == tagtypes.ICLASS_LEGACY or
            typ == tagtypes.ICLASS_ELITE):

        key = bundle["key"]
        file = bundle["file"]

        # 首先，我们需要校验秘钥是否正确!
        if hficlass.checkKey(typ, key):  # 秘钥验证通过，我们需要进行数据块验证

            for verify_block in getNeedWriteBlock(typ):

                # 迭代上述的扇区，读取数据进行校验
                block_from_file = readBlockHex(append_suffix(file), verify_block)
                print("读取出来的扇区(block_from_file): ", block_from_file)
                block_from_tag = hficlass.readTagBlock(typ, verify_block, key)
                print("读取出来的扇区(block_from_tag): ", block_from_tag)

                if block_from_file.upper() != block_from_tag.upper():
                    return -1

            print("所有写入的扇区都校验完成，写入成功。")
            return 1

        else:
            print("校验时，验证秘钥不正确！")
            return -1

    else:
        # 当前我们是处于iClass SE 卡片验证？
        # 那我们默认读取一些块就好了
        # 首先，我们需要校验秘钥是否正确!
        if hficlass.checkKey(typ, "AFA785A7DAB33378"):  # 秘钥验证通过，我们需要进行数据块验证

            blocks = make_se_data(bundle['blck7'])
            for verify_block in blocks.keys():
                # 迭代上述的扇区，读取数据进行校验

                block_from_dict = blocks[verify_block]
                print("读取出来的扇区(block_from_dict): ", block_from_dict)

                block_from_tag = hficlass.readTagBlock(typ, verify_block, "AFA785A7DAB33378")
                print("读取出来的扇区(block_from_tag): ", block_from_tag)

                if block_from_dict.upper() != block_from_tag.upper():
                    return -1

            print("所有写入的扇区都校验完成，写入成功。")
            return 1

        else:
            print("校验时，验证秘钥不正确！")
            return -1

    # 警告个鬼哦
    # return -1

# -*- coding: UTF-8 -*-
import appfiles
import commons
import mifare
import hfmfkeys
import tagtypes

# 导入常用的mifare常量
from mifare import A
from mifare import B

# 导入常用的工具
from executor import startPM3Task
from executor import hasKeyword
from executor import getContentFromRegexG
from executor import getContentFromRegexA

# 数据映射表，保存数据专用
DATA_MAP = {}
# 保存的数据文件
FILE_READ = None


def cacheFile(file):
    """
        缓存文件引用
    :param file:
    :return:
    """
    global FILE_READ
    FILE_READ = file


def parseAllKeyFromDataFile(infos, file):
    """
        解析秘钥，从数据文件中
    :return:
    """
    try:
        uid = infos['uid']
        suffix = ".eml"
        if not file.endswith(suffix):
            file += suffix
        # 第一步，先加载数据文件
        with open(file) as fd:
            # 读取数据从文件中
            data_raw = fd.read().split("\n")
            if len(data_raw) <= 0:
                print("不合法的数据")
                return
            data_list = []
            # 迭代筛选有效地数据段
            for data in data_raw:
                data = data.strip()
                data_len = len(data)
                if data_len == 0:
                    continue
                if mifare.isBlockData(data):
                    data_list.append(data)
            # 判断数据是否有效
            data_len = len(data_list)
            valid_block_size = [mifare.BLOCK_1K, mifare.BLOCK_2K, mifare.BLOCK_4K, mifare.BLOCK_Mini, ]
            if data_len not in valid_block_size:
                print("无效的块数量")
                return
            # 迭代解析秘钥
            key_list = []
            for index in range(data_len):
                # 判断是否是尾部块，是的话就可以解析尾部块的秘钥了
                if mifare.isTrailerBlock(index):
                    data = data_list[index]
                    # 截取AB秘钥
                    keyA = data[0:12]
                    keyB = data[20:32]
                    # 进行保存
                    if keyA not in key_list:
                        key_list.append(keyA)
                    if keyB not in key_list:
                        key_list.append(keyB)
            # 保存秘钥
            hfmfkeys.genKeyFile(uid, key_list)

    except Exception as e:
        print(e)


def readIfIsGen1a(infos):
    """
        读取后门卡
    """

    appfiles.switch_linux()
    file = appfiles.create_m1(create_name_by_type(infos), "")
    appfiles.switch_current()

    size = sizeGuess(infos["type"])
    cmd = "hf mf csave {} o {}".format(hfmfkeys.getSizeFromBigSize(size), file)

    if startPM3Task(cmd, 8888) != -1:

        line = "saved {} bytes to binary file".format(size)
        if hasKeyword(line):
            # 首先，需要缓存文件句柄，以便写卡的时候可以调用
            cacheFile(file)
            # 其次，我们需要进行秘钥解析保存
            parseAllKeyFromDataFile(infos, file)
            return 1  # 有指定size的卡片读取成功就是成功

    # 读取失败的话，我们要删除这个文件，避免出现空文件堆叠的情况
    commons.delfile_on_icopy(file + ".bin")
    commons.delfile_on_icopy(file + ".eml")
    commons.delfile_on_icopy(file + ".json")
    return -2


def readBlock(block, typ, key):
    """
        读取单块
    """
    cmd = "hf mf rdbl {} {} {}".format(block, typ, key)
    # 出错计数
    select_count = 0
    auth_count = 0
    while True:
        # 执行指令
        if startPM3Task(cmd, 5000) == -1: return -2
        # printContent()
        # 判断当前的输出，查看是否读取成功
        data = getContentFromRegexG(r"data:\s([a-fA-F0-9\s]{47})", 1).replace(" ", "")
        if len(data) == 32:
            return data
        elif hasKeyword("Read block error"):
            print("因为权限的原因读取失败，将返回-4提醒外部调用做出处理")
            # 读取失败，判断当前是否是数据块
            # if mifareutils.isTrailerBlock(block):
            # 	return mifareutils.EMPTY_TRAI   # 是数据块则用数据填充
            # else: return mifareutils.EMPTY_DATA # 如果是数据块则用数据进行填充
            return -4
        elif hasKeyword("Auth error"):
            if auth_count == 3:
                print("readBlocks密码错误，读取失败")
                return -2
            auth_count += 1
            continue
        elif hasKeyword("Can't select card"):
            print("未找到卡")
            if select_count == 3:
                print("超过三次未找到卡片，将会停止寻找，结束读取。")
                return -1
            select_count += 1
            continue
        else:
            print("读取块失败")
            return -2
    print("readBlock执行结束")


def readBlocks(sector, keyA, keyB, infos):
    "通过此函数你可以读取一个扇区内的所有块，使用rdbl指令，如果读取失败则默认填充0"
    # 构建指令
    first_block = mifare.sectorToBlock(sector)
    last_block = mifare.get_trailer_block(first_block) + 1
    blocks = list(range(first_block, last_block))
    datas = []
    # 开始循环
    for block in blocks:
        if keyB is not None and keyA is not None:
            # 先用B秘钥读一个块
            ret = readBlock(block, B, keyB)
            # 读取成功，则跳过下一步的操作，进入下一个块的读取
            if isinstance(ret, str):
                datas.append(ret)
                continue
            # 读取失败，判断是否是-4，-4则需要更换使用A秘钥读取
            if ret != -4: return ret
            # -4，使用A秘钥读取
            ret = readBlock(block, A, keyA)
            # 读取成功，则跳过下一步的操作，进入下一个块的读取
            if isinstance(ret, str):
                datas.append(ret)
                continue
            # 读取失败，判断是否是-4，-4则需要使用空数据填充
            if ret != -4: return ret
            # 使用空的数据填充
            datas.append(createEmptyBlock(block, infos))
            continue
        elif keyB is not None:
            ret = readBlock(block, B, keyB)
            if isinstance(ret, str):
                datas.append(ret)
                continue
            if ret != -4: return ret
            datas.append(createEmptyBlock(block, infos))
            continue
        elif keyA is not None:
            ret = readBlock(block, A, keyA)
            if isinstance(ret, str):
                datas.append(ret)
                continue
            if ret != -4: return ret
            datas.append(createEmptyBlock(block, infos))
            continue
    # 将结果放置到映射表中
    DATA_MAP[sector] = datas
    print("readBlocks() -> 扇区读取完成: ", sector)
    return 1


def readSector(sector, typ, key):
    """
        读取扇区，根据指定的扇区号
    """
    # 构建指令
    cmd = "hf mf rdsc {} {} {}".format(sector, typ, key)
    # 在一个循环内进行读取，如果三次找不到卡则退出
    # 如果密码验证错误超过三次也退出
    # 如果读取到卡片也直接退出
    select_count = 0
    auth_count = 0
    while True:
        # 执行
        if startPM3Task(cmd, 5000) == -1: return -2
        # printContent()
        # 尝试截取并且获得数据

        # 数据截取
        regex = r"\s\|\s([a-fA-F0-9\s]{47})"
        data_g = getContentFromRegexA(regex)
        # 进行数据的空格去除
        count = 0
        for i in range(len(data_g)):
            data_g[i] = data_g[i].replace(r" ", "")
            if len(data_g[i]) != 32: count = -2
            count += 1
        if count != 4 and count != 16:
            print("块个数不符合规范: ", count)
            count = -2

        if count != -2:
            # 提交到全局缓冲表中存放
            DATA_MAP[sector] = data_g
            return 1
        elif hasKeyword(r"Read sector\s+\d+\s+block\s+\d+\s+error"):
            print("扇区中可能存在块没有权限读")
            # 出现了没有权限读取的块，我们可以尝试单独进行块读取
            # 不可以直接进入读取
            # return readBlocks(sector, typ, key)
            return -4
        elif hasKeyword("Auth error"):
            if auth_count == 3:
                print("readSector密码错误，读取失败")
                return -2
            auth_count += 1
            continue
        elif hasKeyword("Can't select card"):
            print("未找到卡")
            if select_count == 3:
                print("超过三次未找到卡片，将会停止寻找，结束读取。")
                break
            select_count += 1
            continue
        else:
            print("读取扇区失败")
            return -2
    print("readSector执行结束")
    return -1


def xor(datahex):
    """
        异或校验
    :return:
    """
    bs = bytearray.fromhex(datahex.replace(" ", ""))
    # 计算异或值
    ret = 0
    for b in bs: ret ^= b
    return hex(ret).replace("0X", "").replace("0x", "").rjust(2, "0")


def endian(atqa):
    """
        大小端转换
        atqa在数据块里需要转换大小端
    :param atqa:
    :return:
    """
    a1 = str(atqa)[0:2]
    a2 = str(atqa)[2:4]
    return a2 + a1


def createManufacturerBlock(infos):
    """
        创建模板厂商块
    """

    uid_temp = "{uid}{xor}{sak}{atqa}{mcode}"

    uid = infos["uid"]
    sak = infos["sak"]
    atqa = endian(infos["atqa"])
    len_uid = infos["len"]

    if uid is None or len(uid) == 0: uid = "12345678"

    # 我们需要进行UID的长度判断
    if len_uid == 4:
        mb = uid_temp.format(
            uid=uid,
            xor=xor(uid),
            sak=sak,
            atqa=atqa,
            mcode="016F016D4568F81D"
        ).upper()
    else:
        mb = uid + ("0" * 18)

    print("最终生成的产商块: ", mb)
    return mb


def createEmptyBlock(block, infos):
    """创建模板块"""
    if block == 0: return createManufacturerBlock(infos)
    if mifare.isTrailerBlock(block): return mifare.EMPTY_TRAI
    return mifare.EMPTY_DATA


def createTempSector(sector, infos):
    """创建模板扇区"""
    # 扇区0的模板填充
    temp = []
    if sector == 0:
        temp.append(createManufacturerBlock(infos))
        temp.extend(["00000000000000000000000000000000"] * 2)
    else:
        # 获取数据块计数
        count = mifare.getBlockCountInSector(sector)
        if count == 4: temp.extend(["00000000000000000000000000000000"] * 3)
        if count == 16: temp.extend(["00000000000000000000000000000000"] * 15)
    # 追加尾部块
    temp.append("FFFFFFFFFFFFFF078069FFFFFFFFFFFF")
    return temp


def createTempDatas(size, infos):
    """
        生成模板数据
    :return:
    """
    ret_list = []
    sector_max = mifare.getSectorCount(size)
    for sector in range(sector_max):
        ret_list.extend(createTempSector(sector, infos))
    return ret_list


def fillKeys2DataMap():
    """填充已知的秘钥到数据表里面"""
    for tk in hfmfkeys.KEYS_MAP:
        # 取出扇区
        sec = hfmfkeys.getSectorFromTK(tk)
        # 取出秘钥类型
        typ = hfmfkeys.getTypeFromTK(tk)
        if sec in DATA_MAP:
            # 取出尾部块数据
            last_block = mifare.getBlockCountInSector(sec) - 1
            # print("\n填充的扇区: ", sec)
            # print("填充的最后的块: ", last_block)
            # print("填充的数据: ", DATA_MAP[sec], "\n")
            trail = DATA_MAP[sec][last_block]
            # 取出秘钥并且更新到本地
            if typ == A: trail = hfmfkeys.KEYS_MAP[tk] + trail[12:]
            if typ == B: trail = trail[:20] + hfmfkeys.KEYS_MAP[tk]
            trail = trail.upper()
            # 更新到全局的数据池中
            DATA_MAP[sec][last_block] = trail
    # print("秘钥填充完成")
    # print("")


def callListener(sector, sectorMax, listener):
    """
        计算进度值并且回调
    """
    # 计算百分比并且回调
    if listener is not None and callable(listener):
        p = int(float(sector + 1) / float(sectorMax) * 20) + 80
        listener({"sector": sector, "sectorMax": sectorMax, "progress": p})


def readAllSector(size, infos, listener):
    """
        读取所有的扇区
    """
    # 建立一个表，记录是否成功读取一个扇区
    sector_max = mifare.getSectorCount(size)
    # 返回值
    ret = 1

    def readByKeyA(s, key, info):
        """
            内部函数，实现以秘钥A的形式读取扇区
        """
        # 开始读取
        ret_v = readSector(s, A, key)
        # 判断A秘钥是否读取成功
        if ret_v == 1:
            callListener(s, sector_max, listener)
            return ret_v

        # 如果秘钥A也出现了权限之类的问题，则需要尝试分块读取
        if ret_v != -4: return ret_v

        # 重试读取
        ret_v = readBlocks(s, key, keyB, info)
        if ret_v == 1:
            callListener(s, sector_max, listener)
            return ret_v
        else:
            return ret_v

    for sector in range(0, sector_max):
        # 取出该扇区的秘钥A
        keyA = hfmfkeys.getKey4Map(sector, A)
        # 取出该扇区的秘钥B
        keyB = hfmfkeys.getKey4Map(sector, B)

        # 尝试用B秘钥读取
        if keyB is not None and keyA is not None:
            ret = readSector(sector, B, keyB)
            # 如果秘钥B读取成功那么可以直接跳过
            if ret == 1:
                callListener(sector, sector_max, listener)
                continue
            # 如果秘钥B读取失败并且返回值不为-4，则是出现了影响读取的问题，需要中断读取
            if ret != -4: return ret
            # 当前可能没有权限读取，尝试用A秘钥进行读取
            ret = readByKeyA(sector, keyA, infos)
            if ret == 1:
                continue
            else:
                return ret
        elif keyB is not None:
            ret = readSector(sector, B, keyB)
            # 如果秘钥B读取成功那么可以直接跳过
            if ret == 1:
                callListener(sector, sector_max, listener)
                continue
            # 如果秘钥B读取失败并且返回值不为-4，则是出现了影响读取的问题，需要中断读取
            if ret != -4: return ret
            # 尝试以单块的形式读取所有的扇区
            ret = readBlocks(sector, keyA, keyB, infos)
            if ret == 1:
                callListener(sector, sector_max, listener)
            else:
                return ret
        elif keyA is not None:
            # 尝试用A秘钥进行读取
            ret = readByKeyA(sector, keyA, infos)
            if ret == 1:
                continue
            else:
                return ret
        else:
            # AB秘钥都为空，需要根据当前的扇区用空数据填充
            print("AB秘钥都为空，自动根据当前的扇区用空数据填充")
            DATA_MAP[sector] = createTempSector(sector, infos)
            callListener(sector, sector_max, listener)

    # 秘钥填充
    fillKeys2DataMap()
    # 如果读取成功，则保存数据
    if ret == 1:
        data_list = list()
        for sector in range(0, sector_max):
            sector_data = DATA_MAP[sector]
            data_list.extend(sector_data)
        print(data_list)
        # 保存一份EML
        save_eml(infos, data_list)
        # 保存一份BIN
        save_bin(infos, data_list)
    return ret


def create_name_by_type(infos):
    typ = infos["type"]
    uid_str = infos["uid"]
    uid_len = str(int(infos["len"])) + "B"

    if typ in tagtypes.getM1MiniTypes():
        size = "Mini"
    elif typ in tagtypes.getM12KTypes():
        size = "2K"
    elif typ in tagtypes.getM14KTypes():
        size = "4K"
    elif typ in tagtypes.getM11KTypes():
        size = "1K"
    else:
        size = "Unknown"

    return size + "-" + uid_len + "_" + uid_str


def save_eml(infos, data_list):
    # 先创建文件
    file = appfiles.create_m1(create_name_by_type(infos), "eml")
    cacheFile(file)
    # 然后进行写入
    data_str = ""
    # 迭代加入换行符
    for data_line in data_list:
        data_str += data_line + "\n"
    # 去除多余的换行符然后保存
    return appfiles.save2any(data_str.rstrip("\n"), file)


def save_bin(infos, data_list):
    # 先创建文件
    file = appfiles.create_m1(create_name_by_type(infos), "bin")
    cacheFile(file)
    # 然后进行写入
    data_str = ""
    for data_line in data_list:
        data_str += data_line
    # 去除多余的换行符然后保存
    return appfiles.save2any(bytearray.fromhex(data_str), file)


def sizeGuess(typ):
    """
        标签容量猜测
    """
    if typ in tagtypes.getM1MiniTypes():
        size = mifare.SIZE_MINI
    elif typ in tagtypes.getM12KTypes():
        size = mifare.SIZE_2K
    elif typ in tagtypes.getM14KTypes():
        size = mifare.SIZE_4K
    elif typ in tagtypes.getM11KTypes():
        size = mifare.SIZE_1K
    else:
        return mifare.SIZE_MINI  # 遇到了不被支持的类型，但是有可能是14A的卡片，我们需要使用14a的UID写入方式实现
    return size


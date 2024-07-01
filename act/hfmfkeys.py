# -*- coding: UTF-8 -*-
import os
import threading
import time

import appfiles
import commons
import executor
import re

import mifare
from mifare import A
from mifare import B
from mifare import AB

# 建表，秘钥映射专用
KEYS_MAP = {}
# 回调，进度专用
progressListener = None
# 当前解密的秘钥计数
keyFound = 0
# 上限解密的秘钥计数
keyInTagMax = 32

# 支持的破解流程
RECOVERY_FCHK = "ChkDIC"  # 跑字典
RECOVERY_DARK = "Darkside"  # 跑全加密
RECOVERY_NEST = "Nested"  # 跑半加密
RECOVERY_STNE = "STnested"  # 跑静态漏洞
RECOVERY_ALL = "REC_ALL"  # 全部都跑成功了
# 当前处于哪个破解流程
RECOVERY_TYPE = None

# nested一个密钥时需要用到的时间
TIME_NESTED_ONE = 11
# darkside一个密钥需要用到的时间（最多）
TIME_DARKSIDE_ONE = 60
# 验证一个密钥需要的时间
TIME_FHCK_ONE = 0.01
# 当前操作剩余的时间
TIME_ACT_REMAIN = 0
# 当前如果是ST，每个密钥需要用上多少时间
TIME_ST_ONEKEY_MAX = 0
# 如果是ST，总共需要用到多少时间
TIME_ST_ALLKEY_MAX = 0

# 标志当前的倒计时线程是否需要工作
LABEL_RUN_COUNT_DOWN = False

# 用户秘钥文件的规范名
KEY_FILE_USER_NAME = "user"

# 默认秘钥文件
DEFAULT_KEYS = [
    "FFFFFFFFFFFF",  # Default key (first key used by program if no user defined key)
    "000000000000",  # Blank key
    "111111111111",
    "A0A1A2A3A4A5",  # NFCForum MAD key
    "B0B1B2B3B4B5",
    "C0C1C2C3C4C5",
    "D0D1D2D3D4D5",
    "AABBCCDDEEFF",
    "1A2B3C4D5E6F",
    "123456789ABC",
    "010203040506",
    "123456ABCDEF",
    "ABCDEF123456",
    "4D3A99C351DD",
    "1A982C7E459A",
    "D3F7D3F7D3F7",  # NDEF public key
    "714C5C886E97",
    "587EE5F9350F",
    "A0478CC39091",
    "533CB6C723F6",
    "8FD0A4F256E9",
    "0000014B5C31",
    "B578F38A5C61",
    "96A301BCE267",
    "E00000000000",
    "050908080008",
    "160A91D29A9C",
    "B7BF0C13066E",
    "E7D6064C5860",
    "B27CCAB30DBD",

    # UK代理给的区域性秘钥，我们可以添加进去
    "F7EF6DE261F4",
    "F1EC94AACD81",
    "E64A986A5D94",
    "BF1F4424AF76",
    "AA0720018738",
    "A6CAC2886412",
    "A22AE129C013",
    "8FA1D601D0A2",
    "8AD5517B4B18",
    "89347350BD36",
    "8829DA9DAF76",
    "7F33625BC129",
    "6C78928E1317",
    "6C697365722E",
    "6C6520706173",
    "6C20494E5049",
    "6BC1E1AE547D",
    "6A1987C40A21",
    "66D2B7DC39EF",
    "6465706F7420",
    "62D0C424ED8E",
    "564C505F4D41",
    "536653644C65",
    "509359F131B1",
    "4F47454C4543",
    "4D61071B7254",
    "4D414C414741",
    "4A6352684677",
    "4A4C474F524D",
    "49FAE4E3849F",
    "484558414354",
    "444156494442",
    "434456495243",
    "434143445649",
    "4338265AFB87",
    "424C41524F4E",
    "41636365730F",
    "41636365730E",
    "41636365730D",
    "41636365730C",
    "41636365730B",
    "41636365730A",
    "416363657309",
    "416363657308",
    "416363657307",
    "416363657306",
    "416363657305",
    "416363657304",
    "416363657303",
    "416363657302",
    "414C41524F4E",
    "414354616374",
    "4143532D494E",
    "38FCF33072E0",
    "34016FAC127D",
    "314B49464956",
    "2EF720F2AF76",
    "2A2C13CC242A",
    "22729A9BD40F",
    "199404281970",
    "0A65CB3EB977",
    "021209197591",
    "EEB420209D0C",
    "911E52FD7CE4",
    "752FBB5B7B45",
    "66B03ACA6EE9",
    "48734389EDC3",
    "17193709ADF4",
    "1ACC3189578C",
    "C2B7EC7D4EB1",
    "369A4663ACD2",
    "0D258FE90296",
    "5E594208EF02",
    "AF9E38D36582",
]


def updateRecovery(rec):
    """
        更新当前的恢复操作类型
    :param rec:
    :return:
    """
    global RECOVERY_TYPE
    RECOVERY_TYPE = rec


def updateKeyFound(count):
    """
        更新已经发现的秘钥个数
    """
    if count > keyInTagMax:
        print("updateKeyFound检测到秘钥个数超出上限，自动修正。")
        return
    global keyFound
    keyFound = count


def updateKeyMax(key_count_max):
    """
        更新秘钥个数上限
    :param key_count_max:
    :return:
    """
    global keyInTagMax
    keyInTagMax = key_count_max


def createTk(sector, typ):
    """
        创建秘钥映射表的键
    :param sector:
    :param typ:
    :return:
    """
    return str(sector) + ":" + typ


def getSectorFromTK(tk):
    """
        从映射键里面获取扇区信息
    :param tk:
    :return:
    """
    return int(tk.split(":")[0])


def getTypeFromTK(tk):
    """
        从映射键里面获取秘钥类型信息
    :param tk:
    :return:
    """
    return tk.split(":")[1]


def putKey2Map(sector, typ, key):
    """
        提交一个秘钥到表里
    :param sector:
    :param typ:
    :param key:
    :return:
    """
    KEYS_MAP[createTk(sector, typ)] = key


def getKey4Map(sector, typ):
    """
        从表里面获取秘钥
    :param sector:
    :param typ:
    :return:
    """
    tK = createTk(sector, typ)
    if tK in KEYS_MAP: return KEYS_MAP[tK]
    return None


def delKey4Map(sector, typ):
    """
        从表里面删除秘钥
    :param sector:
    :param typ:
    :return:
    """
    del KEYS_MAP[createTk(sector, typ)]


def hasAllKeys(size):
    """
        判断映射表里面是否已经存放了完整的秘钥
    :param size:
    :return:
    """
    if getSizeFromBigSize(size) == 0:
        return len(KEYS_MAP) == 10
    if getSizeFromBigSize(size) == 1:
        return len(KEYS_MAP) == 32
    if getSizeFromBigSize(size) == 2:
        return len(KEYS_MAP) == 64
    if getSizeFromBigSize(size) == 4:
        return len(KEYS_MAP) == 80


def hasKeyA(sector):
    """
        判断对应的扇区是否有秘钥A在表里面
    :param sector:
    :return:
    """
    return createTk(sector, A) in KEYS_MAP


def hasKeyB(sector):
    """
        判断对应的扇区是否有秘钥B在表里面
    :param sector:
    :return:
    """
    return createTk(sector, B) in KEYS_MAP


def getAnyKey():
    """
        获取任意一个秘钥，从表里面
    :return:
    """
    for k in sorted(KEYS_MAP):
        ret = {
            "sector": getSectorFromTK(k),
            "type": getTypeFromTK(k),
            "key": KEYS_MAP[k]
        }
        return ret


def getLostKeySector(size):
    """
        获取缺失秘钥的扇区的信息
    :param size:
    :return:
    """
    retMap = {}
    for sector in range(0, mifare.getSectorCount(size)):
        tkA = createTk(sector, A)
        tkB = createTk(sector, B)
        # 判断是否有秘钥AB
        if tkA in KEYS_MAP and tkB in KEYS_MAP:
            # 有则跳过记录，我们只需要记录没有的
            continue
        # 判断是否有秘钥A，有秘钥A则肯定没有秘钥B
        elif tkA in KEYS_MAP:
            retMap[sector] = B
        # 反之，则没有秘钥A
        elif tkB in KEYS_MAP:
            retMap[sector] = A
        # 都缺失
        else:
            retMap[sector] = AB
    return retMap


def genKeyFile(uid, key_list):
    """
        生成秘钥映射表文件在本地
    """
    try:
        # 创建指定名称的秘钥文件
        file = appfiles.create_mf1_keys(uid)
        # 存放结果的集合
        ret = set()

        # 第一步，读取原本的秘钥文件，然后去重
        with open(file) as fd_read:
            lines = fd_read.readlines()

        # 去重
        for key in lines:
            ret.add(key.strip())
        for key in key_list:
            ret.add(key.strip())

        # 第二步，写回去
        if len(ret) > 0:
            ret = '\n'.join(ret).strip()
            print("将要保存的内容: \n", ret)
            with open(file, "w+") as fd_write:
                fd_write.writelines(ret)
            print("秘钥保存完成")

        # 第三步，判断当前是否是在保存到指定的UID的秘钥文件里面
        # 如果是的话，我们应当复制所有的秘钥到用户输入文件里面
        if uid != KEY_FILE_USER_NAME:
            # 迭代需要保存的秘钥的列表
            cache_user_keys = []
            for key in key_list:
                key = key.strip().upper()
                if key not in DEFAULT_KEYS:
                    # 如果这个秘钥不在默认秘钥队列里，并且这个秘钥不在
                    # 我们可以进行尝试添加
                    cache_user_keys.append(key)
            # 进行最终的秘钥缓存
            genKeyFile(KEY_FILE_USER_NAME, cache_user_keys)
    except Exception as e:
        print("写入秘钥文件异常: ", e)


def getSizeFromBigSize(size):
    """
        把大数字的内容容量转换为卡片简介的短数字容量
    :param size:
    :return:
    """
    if size <= 4: return size
    if size == mifare.SIZE_MINI:
        return 0
    if size == mifare.SIZE_1K:
        return 1
    if size == mifare.SIZE_2K:
        return 2
    if size == mifare.SIZE_4K:
        return 4


def read_keys_of_file(file):
    """
        读取秘钥文件，返回秘钥列表（去重）
    :param file:
    :return:
    """
    ret = []
    try:
        file = open(file, mode="r")
        lines = file.readlines()
        for line in lines:
            if re.match(r"[a-fA-F0-9]{12}", line) is not None:
                key = re.search(r"([a-fA-F0-9]{12})", line)
                if key is not None:
                    key = key.group(1)
                    ret.append(key)
    except Exception as e:
        print("read_keys_of_file: ", e)
    return ret


def append_keys_unique(files, key_list):
    """
        添加到秘钥列表中，以唯一值出现
    :return:
    """
    # 判断是否有文件
    if len(files) > 0:
        for file in files:
            # 读取所有的秘钥出来
            ks = read_keys_of_file(file)
            if len(ks) > 0:
                # 去重并且添加到列表中
                for key in ks:
                    key = key.strip()
                    if key.startswith("#"):
                        continue
                    if re.match(r"[A-Fa-f0-9]{12}", key):
                        keyU = key.upper()
                        keyL = key.lower()
                        if keyU not in key_list and keyL not in key_list:
                            key_list.append(key)


def count_down():
    """
        倒计时效果
    :return:
    """
    print("倒计时线程开始")
    global TIME_ACT_REMAIN
    while LABEL_RUN_COUNT_DOWN:
        while TIME_ACT_REMAIN > 0:
            TIME_ACT_REMAIN = TIME_ACT_REMAIN - 1
            callProgress(TIME_ACT_REMAIN)
            time.sleep(1)
        time.sleep(0.1)
    print("倒计时线程结束")


def callProgress(seconds=0):
    if progressListener is not None and callable(progressListener):
        global TIME_ACT_REMAIN
        # 计算百分比并且回调，此处不设置为100是因为要留着20给读卡时使用
        p = int(float(keyFound) / float(keyInTagMax) * 80)
        # 如果秒数差距过大，我们就需要进行过度效果的显示
        if seconds == 0 and TIME_ACT_REMAIN > 1:
            print("秒数差距过大，开始进行过渡效果")
            delay_time = 1 / TIME_ACT_REMAIN
            transition = TIME_ACT_REMAIN
            while transition > 0:
                transition = transition - 1
                progressListener({
                    "m1_keys": True,
                    "seconds": transition,
                    "action": RECOVERY_TYPE,
                    "keyIndex": keyFound,
                    "keyCountMax": keyInTagMax,
                    "progress": p,
                })
                time.sleep(delay_time)
            TIME_ACT_REMAIN = 0
        else:
            TIME_ACT_REMAIN = seconds
            progressListener({
                "m1_keys": True,
                "seconds": seconds,
                "action": RECOVERY_TYPE,
                "keyIndex": keyFound,
                "keyCountMax": keyInTagMax,
                "progress": p,
            })


def onNestedCall(lines: str):
    """
        处理nested执行时的一些动态的数据的更新
    :param lines:
    :return:
    """

    print("onNestedCall() -> ", lines)

    # 动态更新获取到的秘钥个数
    count_key_found = lines.count(r"found valid key")
    if count_key_found > 0:
        updateKeyFound(count_key_found + keyFound)

    # 截取剩余时间的提醒，如果存在！
    tmp_time_remain = -1
    seaObj = re.search(r".*worst case {2}([0-9\\.]+) seconds.*", lines)
    if seaObj is not None:
        gT = seaObj.group(1)
        if len(gT) > 0:
            tmp_time_remain = float(gT)

    # 是否有极速解密的过程触发
    if 'Fast staticnested decrypt' in lines:
        # 极速解密ST每个秘钥只需要三秒
        tmp_time_remain = 5

    global TIME_ACT_REMAIN, TIME_ST_ONEKEY_MAX, TIME_ST_ALLKEY_MAX
    if RECOVERY_TYPE is RECOVERY_STNE:
        if TIME_ACT_REMAIN == 0:  # 进行时间初始化
            if tmp_time_remain != -1:
                TIME_ST_ONEKEY_MAX = tmp_time_remain
                # 缓存一下ST的上限时间
                TIME_ST_ALLKEY_MAX = TIME_ACT_REMAIN = int((keyInTagMax - keyFound) * TIME_ST_ONEKEY_MAX)
                callProgress(TIME_ACT_REMAIN)
                print(f"更新了ST的上限时间: {TIME_ST_ONEKEY_MAX}")
        elif count_key_found > 0:  # 进行时间缩减跳跃
            # 减去当前已经用掉的时间！
            tmp_act_remain = TIME_ST_ALLKEY_MAX - (TIME_ST_ALLKEY_MAX - TIME_ACT_REMAIN)
            if tmp_act_remain > 0:
                TIME_ACT_REMAIN = tmp_act_remain
            print(f"还剩下{TIME_ACT_REMAIN}秒")
            print(f"ST的上限时间是{TIME_ST_ALLKEY_MAX}秒")
            print(f"当前发现了{count_key_found}个秘钥")
        elif TIME_ACT_REMAIN < tmp_time_remain:  # 进行时间修正！
            TIME_ST_ALLKEY_MAX = TIME_ACT_REMAIN = tmp_time_remain * (keyInTagMax - keyFound)
            print("ST时间自动进行修正成功！")

    elif RECOVERY_TYPE is RECOVERY_NEST:
        if TIME_ACT_REMAIN == 0:
            print("当前进入NESTED解密状态")
            callProgress((keyInTagMax - keyFound) * TIME_NESTED_ONE)
        # elif count_key_found > 0:  # 暂时不采纳Nested的跳跃式时间缩减意见
        #     TIME_ACT_REMAIN -= (TIME_NESTED_ONE * count_key_found)

    return


def darksideOneKey():
    """
        执行PRNG漏洞获取一个秘钥
    :return:
    """
    cmd = "hf mf darkside"
    updateRecovery(RECOVERY_DARK)
    callProgress(TIME_DARKSIDE_ONE)
    if executor.startPM3Task(cmd, TIME_DARKSIDE_ONE * 1000, rework_max=0) == -1:
        return {
            "return": -4
        }
    if executor.hasKeyword("found valid key"):
        return {
            "return": 1,
            "key": executor.getContentFromRegexG(r".*([a-fA-F0-9]{12}).*", 1)
        }
    if not executor.hasKeyword("no candidates found, trying again"):
        return {
            "return": -4
        }
    return {
        "return": -4
    }


def nestedAllKeys(infos, size):
    """执行嵌套验证漏洞指令进行所有的秘钥恢复"""
    key = getAnyKey()
    cmd = "hf mf {{loudong}} {size} {block} {type} {key}"
    block = mifare.sectorToBlock(key["sector"])
    cmd = cmd.format(size=getSizeFromBigSize(size), block=block, type=key["type"], key=key["key"])

    # 如果是静态随机数，则使用staticnested指令
    if infos["static"]:
        cmd = cmd.format(loudong="staticnested")
        updateRecovery(RECOVERY_STNE)
    else:
        cmd = cmd.format(loudong="nested")
        updateRecovery(RECOVERY_NEST)

    print("开始执行命令进行解密: ", cmd)

    if executor.startPM3Task(cmd, -1, onNestedCall) == -1:
        print("在一开始执行nested就出现了执行器异常的问题。")
        return -2

    re_exec = False

    # 判断是否有关键词引导使用对应的漏洞指令，如果有，我们就需要切换指令重新执行
    if executor.hasKeyword("Try use `hf mf staticnested`"):
        cmd = cmd.replace("nested", "staticnested")
        print("最终被执行的指令: ", cmd)
        updateRecovery(RECOVERY_STNE)
        re_exec = True

    elif executor.hasKeyword("Try use `hf mf nested`"):
        cmd = cmd.replace("staticnested", "nested")
        print("最终被执行的指令: ", cmd)
        updateRecovery(RECOVERY_NEST)
        re_exec = True

    if re_exec:  # 上面的执行结果出现了预料之中的问题，我们需要进行重启任务
        if executor.startPM3Task(cmd, -1, onNestedCall) == -1:
            return -2

    print("破解完成！")

    # 判断是否异常
    if executor.hasKeyword("Wrong key. Can't authenticate to block"):
        print("秘钥验证错误")
        return -2
    if executor.hasKeyword("Tag isn't vulnerable to Nested Attack"):
        print("没有嵌套验证漏洞")
        return -3
    # 判断是否被终止
    if executor.hasKeyword("button pressed. Aborted."):
        print("解密过程卡片被移除，自动停止")
        return -2
    # 再次解析秘钥
    if keysFromPrintParse(size) == 0:
        print("没有发现成功解析的秘钥（来自于秘钥表），可能出现了异常情况导致秘钥表没有被打印")
        return -2

    def call_nested_progress():
        callProgress((keyInTagMax - keyFound) * TIME_NESTED_ONE)

    # 更新秘钥计数
    updateKeyFound(len(KEYS_MAP))
    call_nested_progress()

    # 解析完成后判断是否有缺失的秘钥，如果有的话，我们就需要进行补充性的破解
    if not hasAllKeys(size):
        print("发现有遗漏的秘钥，将开始查漏补缺")
        # 获取缺失的秘钥组
        lost_map = getLostKeySector(size)
        # 开始迭代重试破解
        for kSector in lost_map:
            # 获取一个可用的秘钥信息
            known_key_map = getAnyKey()
            block = mifare.sectorToBlock(known_key_map["sector"])
            known_key_map["block"] = block
            # 建立目标组信息
            target_a = {
                "block": mifare.sectorToBlock(kSector),
                "type": A
            }
            target_b = {
                "block": mifare.sectorToBlock(kSector),
                "type": B
            }

            def rA():
                key_a = nestedOneKey(known_key_map, target_a, 10)
                if key_a == -1: return -1
                if key_a is not None:
                    putKey2Map(kSector, A, key_a)
                    updateKeyFound(keyFound + 1)
                    call_nested_progress()
                    return True
                else:
                    print("恢复单个秘钥失败: ", target_a)
                    return False

            def rB():
                key_b = nestedOneKey(known_key_map, target_b, 10)
                if key_b == -1:
                    return -1
                if key_b is not None:
                    putKey2Map(kSector, B, key_b)
                    updateKeyFound(keyFound + 1)
                    call_nested_progress()
                    return True
                else:
                    print("恢复单个秘钥失败: ", target_b)
                    return False

            # 缺失秘钥A
            if lost_map[kSector] == A:
                a = rA()
                # 判断是否执行出错
                if a == -1: return -2
                if not a: return -3

            # 缺失秘钥B
            if lost_map[kSector] == B:
                b = rB()
                if b == -1: return -2
                if not b: return -3

            # 缺失秘钥AB两个
            if lost_map[kSector] == AB:
                a = rA()
                b = rB()
                if a == -1 or b == -1: return -2
                if not a or not b: return -3

        # 查看是否所有的密码都存在，如果还没有，那就是程序的BUG了
        if not hasAllKeys(size):
            print("已经执行完查漏补缺，但是仍然发现缺失秘钥，请排查是否是软件BUG。")
            return -3
    # 全部秘钥都获取成功的话，我们返回1
    print("全部秘钥都获取成功！")
    return 1


def nestedOneKey(known, target, retryMax):
    """
        使用嵌套验证漏洞恢复一个秘钥
    :param known:
    :param target:
    :param retryMax:
    :return:
    """
    # 生成指令
    cmd = "hf mf nested o {knownBlock} {knownType} {knownKey} {targetBlock} {targetType}"
    cmd = cmd.format(
        knownBlock=known["block"],
        knownType=known["type"],
        knownKey=known["key"],
        targetBlock=target["block"],
        targetType=target["type"]
    )
    # 执行指令进行恢复!
    for count in range(retryMax):
        if executor.startPM3Task(cmd, 8888) != -1:
            if executor.hasKeyword("Try use `hf mf staticnested`"):
                return -3
            # elif executor.hasKeyword("Tag isn't vulnerable to Nested Attack"):
            #     continue
            # elif executor.hasKeyword("Wrong key. Can't authenticate to block:"):
            #     continue
            # elif executor.hasKeyword("No valid key found"):
            #     continue
            elif executor.hasKeyword("found valid key"):
                # 发现了有效的秘钥，我们需要截取返回!
                key = executor.getContentFromRegexG(r"found valid key.*([a-zA-Z0-9]{12}).*", 1)
                print("nestedOneKey() -> 秘钥恢复成功: ", key)
                return key
        else:
            return -1
    return None


def keysFromPrintParse(size):
    """
        从秘钥检测指令的输出解析秘钥
    :param size:
    :return:
    """
    count = 0

    if executor.hasKeyword("No keys found"):
        return count

    # | 000 | ffffffffffff   | 1 | ffffffffffff   | 1 |
    keys_regex = r"\|\s+Sec\s+\|\s+([0-9a-fA-F-]{12})\s+\|\s+(\d)\s+\|\s+([0-9a-fA-F-]{12})\s+\|\s+(\d)\s+\|"

    # 开始循环解析打印的秘钥表
    for index in range(0, mifare.getSectorCount(size)):
        keys_regex_tmp = keys_regex.replace("Sec", "{:0>3d}".format(index))
        # A
        key = executor.getContentFromRegexG(keys_regex_tmp, 1)
        res = executor.getContentFromRegexG(keys_regex_tmp, 2)
        if res == "1":
            key_a = key
        else:
            key_a = None
        # B
        key = executor.getContentFromRegexG(keys_regex_tmp, 3)
        res = executor.getContentFromRegexG(keys_regex_tmp, 4)
        if res == "1":
            key_b = key
        else:
            key_b = None
        # 提交到全局秘钥映射表中
        if key_a is not None and len(key_a) == 12:
            putKey2Map(index, A, key_a)
            count = count + 1
        print("获取{}扇区的秘钥A: {}".format(index, key_a))
        if key_b is not None and len(key_b) == 12:
            putKey2Map(index, B, key_b)
            count = count + 1
        print("获取{}扇区的秘钥B: {}".format(index, key_b))
    print("")
    print("秘钥解析完成")
    return count


def init_m1_key_file():
    """
        初始化M1卡的秘钥文件
    :return:
    """
    uid = "user"
    # 尝试创建秘钥文件
    files = appfiles.search_mf1_keys(uid)
    # print(files)
    # 判断大小，如果是空的，则写入
    for file in files:
        if os.path.getsize(file) > 0:
            print("用户秘钥文件不为空，不重新初始化")
            return

    content = \
        "# This is the default key library.\n" + \
        "#  You can add some known keys.\n" + \
        "# --- App will load this file.\n" + \
        "\n" + \
        "#      Use '#' to add comments. \n" + \
        "# if start with '#', App will ignore this line.\n" + \
        "\n" + \
        "FFFFFFFFFFFF"

    appfiles.save2any(content, appfiles.create_mf1_keys(uid))


def getKeyMax4Size(size):
    """
        从卡片大小中获取秘钥上限数
    :param size:
    :return:
    """
    if size == mifare.SIZE_MINI:
        return 10
    elif size == mifare.SIZE_1K:
        return 32
    elif size == mifare.SIZE_2K:
        return 64
    elif size == mifare.SIZE_4K:
        return 80
    else:
        print("传入的size异常，无法初始化上限值：", size)
    return -1


def is_keys_check_call(call):
    """
        判断是否是M1破解秘钥的回调
    :param call:
    :return:
    """
    return call is not None and isinstance(call, dict) and "m1_keys" in call


def list_split(items, n):
    """
        均匀分割数组
    :param items:
    :param n:
    :return:
    """
    return [items[i:i + n] for i in range(0, len(items), n)]


def fchks(infos, size, with_call=True):
    """
        秘钥检测
    :param with_call:
    :param infos:
    :param size:
    :return:
    """

    # 清空历史遗留的数据
    KEYS_MAP.clear()

    # 最终的秘钥列表
    key_list = list()

    # 每次都查一下用户密钥文件是否存在，不存在则创建一个例子文件
    init_m1_key_file()

    # 历史读取的秘钥文件列表
    cache_files = appfiles.search_mf1_keys(infos["uid"])
    # 用户自定义的秘钥文件列表
    user_files = appfiles.search_mf1_keys("user")

    # 读取并且添加秘钥到结果列表中
    append_keys_unique(cache_files, key_list)
    append_keys_unique(user_files, key_list)

    # 添加默认秘钥，避免出现默认秘钥缺失的情况
    for key in DEFAULT_KEYS:
        keyU = key.upper()
        keyL = key.lower()
        if keyU not in key_list and keyL not in key_list:
            key_list.append(key)

    # 创建临时秘钥文件
    tmp_keys_path_linux = "/tmp/.keys/"
    # 尝试创建基础临时目录
    commons.mkdirs_on_icopy(tmp_keys_path_linux)
    # 拼接秘钥文件路径
    tmp_keys_file = tmp_keys_path_linux + "mf_tmp_keys"
    dic_file = tmp_keys_file + ".dic"
    # 尝试删除旧的文件并且重新创建
    commons.recreate_on_icopy(dic_file)

    for key in list_split(key_list, 512):  # 使用平台命令执行器向临时秘钥文件追加数据
        key = '\\n'.join(key)
        # print("生成的命令数据: ", key)
        commons.append_str_on_icopy(key, dic_file)

    print("本次将被check的秘钥个数: ", len(key_list))

    if with_call:
        callProgress(int(len(key_list) * TIME_FHCK_ONE * mifare.getKeyCount(size) * 2 + 0.4))

    # 取出其中一个秘钥文件拼接到参数中
    cmd = "hf mf fchk {} {}".format(getSizeFromBigSize(size), tmp_keys_file)

    # 第一步是秘钥快速检测
    # 这里我们提高检测延时
    if executor.startPM3Task(cmd, 600000) != 1 or executor.hasKeyword(r"Can't select card \(ALL\)"):
        commons.delfile_on_icopy(dic_file)
        print("M1卡秘钥检测超时")
        return -1

    # 删除临时文件
    commons.delfile_on_icopy(dic_file)
    # 检测完毕之后，我们需要数据的解析以及进行秘钥表的填充!
    keysFromPrintParse(size)
    # 更新秘钥计数
    updateKeyFound(len(KEYS_MAP))

    if with_call:
        # 回調進度
        callProgress()

    return 1


def nested(size, infos):
    """
        利用nested漏洞破解秘钥
    :param size:
    :param infos:
    :return:
    """
    print("获取到了部分秘钥，需要去破解！！！")
    ret = nestedAllKeys(infos, size)
    if ret != 1:
        print("破解失败，需要用户手动选择接下来的操作")
        return ret
    else:
        print("全部的秘钥都获取成功，我们需要继续进行读取操作")
        genKeyFile(infos["uid"], KEYS_MAP.values())
        updateRecovery(RECOVERY_ALL)
        callProgress()
        return 1


def darkside():
    """
        利用darkside破解一个秘钥
    :return:
    """
    ret_map = darksideOneKey()
    if ret_map["return"] == -1:
        print("hf mf darkside指令执行超时")
        return -1
    elif ret_map["return"] == -4:
        print("hf mf darkside指令执行成功，但是没有获取到秘钥")
        return -4
    else:
        # 获取到了秘钥，我们接下来需要去获取全部的秘钥
        print("成功通过hf mf darkside指令获取到了一个秘钥")
        putKey2Map(0, A, ret_map["key"])
        # 更新一下密钥个数，我们需要回调告知用户已经成功破解到一个...
        updateKeyFound(len(KEYS_MAP))
        callProgress()
    return 1


def keys(size, infos, listener):
    """
        调用PM3进行Mifare Classic卡片的破解
    :param size:
    :param infos:
    :param listener:
    :return:
    """
    # 卡片不存在，直接返回-1提醒卡片未发现
    if not infos["found"]: return -1

    # 初始化秘钥数上限等数据
    updateKeyFound(0)
    updateRecovery(RECOVERY_FCHK)
    key_max = getKeyMax4Size(size)
    if key_max == -1:
        return key_max
    updateKeyMax(key_max)

    # 初始化一些变量
    global progressListener, TIME_ST_ONEKEY_MAX, LABEL_RUN_COUNT_DOWN, TIME_ACT_REMAIN, RECOVERY_TYPE
    progressListener = listener
    TIME_ST_ONEKEY_MAX = 0
    TIME_ACT_REMAIN = 0
    LABEL_RUN_COUNT_DOWN = True
    RECOVERY_TYPE = RECOVERY_FCHK

    # 启动一个默认的线程，进行画面更新
    thread = threading.Thread(target=count_down)
    thread.start()

    try:

        # 开始快速检测已知秘钥
        ret = fchks(infos, size)
        if ret == 1:
            genKeyFile(infos["uid"], KEYS_MAP.values())
        elif ret < 0:
            return ret

        # 判断是否已经获取到全部的秘钥
        if hasAllKeys(size):
            genKeyFile(infos["uid"], KEYS_MAP.values())
            updateKeyFound(len(KEYS_MAP))
            updateRecovery(RECOVERY_ALL)
            callProgress()
            return 1
        # 否则如果有任何一个秘钥
        elif len(KEYS_MAP) > 0:
            ret_nested = nested(size, infos)
            callProgress()
            return ret_nested
        else:
            # 一个秘钥都没有
            ret = darkside()
            if ret != 1:
                return ret
            ret_nested = nested(size, infos)
            callProgress()
            return ret_nested
    finally:
        # 关闭倒计时线程
        TIME_ACT_REMAIN = 0
        LABEL_RUN_COUNT_DOWN = False
        thread.join()

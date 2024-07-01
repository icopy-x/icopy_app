# -*- coding: UTF-8 -*-
import base64
import hashlib
import platform
import subprocess

from Crypto.Cipher import AES

import appfiles
import commons
import tagtypes
import executor
import re

import version

CMD_DETECT_NO_KEY = "lf t55xx detect"
CMD_DETECT_ON_KEY = CMD_DETECT_NO_KEY + " p FFFFFFFF"
CMD_DUMP_NO_KEY = "lf t55xx dump"
# 缓存T55XX的卡片的密钥
KEY_TEMP = None
# 缓存读取完成的数据的文件名
DUMP_TEMP = None

TIMEOUT = 10000

KEYWORD_CASE1 = "Could not detect modulation automatically"


def parser():
    if executor.hasKeyword(KEYWORD_CASE1):
        return {
            "found": True,
            "type": tagtypes.T55X7_ID,
            "chip": "T55xx/Unknown",
            "modulate": "--------",
            "b0": "--------",
            "known": False,
        }
    return {
        "found": True,
        "type": tagtypes.T55X7_ID,
        "chip": executor.getContentFromRegexG(r".*Chip Type.*:(.*)", 1).replace(" ", ""),
        "modulate": executor.getContentFromRegexG(r".*Modulation.*:(.*)", 1).replace("0x", "", 1).replace(" ", ""),
        "b0": parser_b0(),
        "key": executor.getContentFromRegexG("Password       : ([A-Fa-f0-9 ]+)", 1).replace(" ", ""),
        "known": True,
    }


def parser_b0():
    return executor.getContentFromRegexG(r".*Block0.*:(.*)", 1).replace("0x", "", 1).replace("0X", "", 1).replace(" ",
                                                                                                                  "")


def set_key(key):
    """
        设置T55XX将被使用的密钥
    :param key:
    :return:
    """
    global KEY_TEMP
    KEY_TEMP = key


def call_listener(listener, max_value, progress, state="read"):
    listener({
        "max": max_value,
        "progress": progress,
        "state": state
    })


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
            if re.match(r"[a-fA-F0-9]{8}", line) is not None:
                key = re.search(r"([a-fA-F0-9]{8})", line)
                if key is not None:
                    key = key.group(1)
                    ret.append(key)
    except Exception as e:
        print("read_keys_of_file: ", e)
    return ret


def append_keys_unique(ks, key_list):
    """
        添加到秘钥列表中，以唯一值出现
    :return:
    """
    if len(ks) > 0:
        # 去重并且添加到列表中
        for key in ks:
            key = key.strip()
            if key.startswith("#"):
                continue
            if re.match(r"[A-Fa-f0-9]{8}", key):
                keyU = key.upper()
                keyL = key.lower()
                if keyU not in key_list and keyL not in key_list:
                    key_list.append(key)


def append_keys_files_unique(files, key_list):
    """
        添加到秘钥列表中，以唯一值出现
    :return:
    """
    # 判断是否有文件
    if len(files) > 0:
        for file in files:
            # 读取所有的秘钥出来
            ks = read_keys_of_file(file)
            append_keys_unique(ks, key_list)


def list_split(items, n):
    """
        均匀分割数组
    :param items:
    :param n:
    :return:
    """
    return [items[i:i + n] for i in range(0, len(items), n)]


def chkT55xx(listener):
    # 执行命令时候的回调
    count = {"max": 0, "count": 0}

    # 内部实现的执行回调函数
    def lineInternal(line):
        print("T55xx秘钥轮询验证: ", line)
        # 解析总秘钥个数
        if count["max"] == 0:
            sea_obj = re.search(r"loaded ([\d]+) keys", line)
            if sea_obj is not None:
                max_count_str = sea_obj.group(1)
                if max_count_str is not None and max_count_str.isnumeric():
                    count["max"] = int(max_count_str)
        # 解析当前的进度
        c = len(re.findall(r"Testing [a-fA-F0-9]+", line))
        if c > 0:  # 有进度更新
            count["count"] += c
            # 回调
            # round((count["count"] / count["max"]) * 100)
            call_listener(listener, count["max"], count["count"], "checkkeys")

    # 在chk之前，我们应当合并秘钥，生成临时文件！
    # 最终的秘钥列表
    key_list = list()
    # 读取T5577的外部秘钥文件
    append_keys_files_unique(
        [
            appfiles.create_t5577_keys()
        ],
        key_list
    )
    # 然后进行内部秘钥合并
    # 添加默认秘钥，避免出现默认秘钥缺失的情况
    for key in DEFAULT_KEYS.split("\n"):
        # 去掉前后的空白字符
        key = key.strip().lower()
        # 判断是否是注释
        if key.startswith("#"):
            continue
        # 进行大小写兼容性适配
        key_exists = False
        for key2 in key_list:
            key2 = key2.strip().lower()
            if key2 == key:
                key_exists = True
        # 去重
        if not key_exists:
            key_list.append(key)

    # 创建临时秘钥文件
    tmp_keys_path_linux = "/tmp/.keys/"
    # 尝试创建基础临时目录
    commons.mkdirs_on_icopy(tmp_keys_path_linux)
    # 拼接秘钥文件路径
    tmp_keys_file = tmp_keys_path_linux + "t5577_tmp_keys"
    dic_file = tmp_keys_file + ".dic"
    # 尝试删除旧的文件并且重新创建
    commons.recreate_on_icopy(dic_file)

    for key in list_split(key_list, 8000):  # 使用平台命令执行器向临时秘钥文件追加数据
        key = '\\n'.join(key)
        # print("生成的命令数据: ", key)
        commons.append_str_on_icopy(key, dic_file)

    print("本次将被check的秘钥个数: ", len(key_list))

    cmd = f"lf t55xx chk f {tmp_keys_file}"

    # 开始执行命令
    if executor.startPM3Task(cmd, 180000, lineInternal) == -1:
        return -2

    # 如果命令执行完成，但是进度没有走到100，则手动执行到100
    if count["max"] != count["count"]:
        call_listener(listener, count["max"], count["max"])

    # 如果未发现秘钥
    if executor.hasKeyword("Check pwd failed"):
        return -7

    # 如果发现了秘钥
    if executor.hasKeyword("Found valid password:"):
        # 截取已知的秘钥
        key = executor.getContentFromRegexG(r"Found valid password: \[([ a-fA-F0-9]+)\]", 1)
        if len(key) == 0:
            return -2
        return key


def genKeyFile(keys):
    """
        生成新的秘钥文件
    :param keys:
    :return:
    """
    file = appfiles.create_t5577_keys()
    try:
        # 存放结果的集合
        ret = set()
        # 第一步，读取原本的秘钥文件，然后去重
        with open(file) as fd_read:
            lines = fd_read.readlines()

        # 去重
        for key in lines:
            ret.add(key.strip())
        for key in keys:
            ret.add(key.strip())

            # 第二步，写回去
        if len(ret) > 0:
            ret = '\n'.join(ret).strip()
            print("将要保存的内容:")
            print(ret)
            with open(file, "w+") as fd_write:
                fd_write.writelines(ret)
            print("秘钥保存完成")
    except Exception as e:
        print("写入秘钥文件异常: ", e)


def chkAndDumpT55xx(listener):
    """
        扫描和dump T55xx系列的卡片
    """

    ret = chkT55xx(listener)
    if isinstance(ret, str):
        return detectAndDumpT55xxByKey(listener, ret)
    return ret


def detectAndDumpT55xxByKey(listener, key):
    """
    侦测和导出t55xx的数据
    """
    set_key(key)
    # 先侦测是否是T55xx的正确秘钥
    ret = detectT55XX(key)
    listener({"new_info": parser()})
    if ret == 2:  # 当前的卡片是未加密可以直接dump
        return dumpT55XX(listener)
    elif ret == 3:  # 当前的卡片是加密的，需要带上秘钥进行dump
        return dumpT55XX(listener, key)
    elif ret == 4:
        return dumpT55XX(listener, key)
    return ret


def detectT55XX(key=None, cache_key=True):
    """
    侦测T55xx的数据
    """
    cmd = CMD_DETECT_NO_KEY
    if key is not None and isinstance(key, str):
        cmd += " p {}".format(key)
    for i in range(0, 2):
        # 开始执行命令
        if executor.startPM3Task(cmd, TIMEOUT) == -1:
            return -1
        # print("T5577 detect 的输出: ", executor.getPrintContent())
        # 开始判断侦测结果
        if executor.hasKeyword("Password       :"):  # 加密，但是发现了秘钥
            key = executor.getContentFromRegexG("Password       : ([A-Fa-f0-9 ]+)", 1)
            if cache_key:
                set_key(key)
            return 4
        # 不放卡也是这个输出
        # [!] Could not detect modulation automatically. Try setting it manually with 'lf t55xx config'
        if executor.hasKeyword(KEYWORD_CASE1):  # 加密，且没有秘钥，无法准确判断
            return 1
        if executor.hasKeyword("Password Set   : No"):  # 没有加密
            return 2
        if executor.hasKeyword("Password Set   : Yes"):  # 加密
            return 3
    # 超过三次后，直接返回-2表示侦测失败
    return -2


def readBlock(pwd_str, b_index, p_index=0):
    """
        读取对应页的块
    :param pwd_str:
    :param b_index:
    :param p_index:
    :return:
    """
    if p_index == 0:
        p_end = ""
    else:
        p_end = "1"
    if pwd_str is None:
        cmd = "lf t55xx read b {} {}".format(b_index, p_end)
    else:
        cmd = "lf t55xx read b {} p {} o {}".format(b_index, pwd_str, p_end)
    if executor.startPM3Task(cmd, TIMEOUT) == -1:
        return None
    regex = r"[0-9]{2} \| ([A-Fa-f0-9 ]+) \|"
    if len(regex) == 0:
        return None
    return executor.getContentFromRegexG(regex, 1)


def dumpT55XX(listener, key=None):
    """读取T55xx系列的卡片，以已知的秘钥来读取"""
    cmd = CMD_DUMP_NO_KEY
    if key is not None and isinstance(key, str):
        cmd += " p {} o".format(key)
        set_key(key)
    # 读取块信息，用于dump文件名称设置
    b0 = readBlock(key, 0)
    b1 = readBlock(key, 1)
    b2 = readBlock(key, 2)
    if b0 is None or b1 is None or b2 is None:
        return -2
    s_e = appfiles.isWindows()
    if s_e: appfiles.switch_linux()
    file = appfiles.create_t55xx(b0, b1, b2)
    global DUMP_TEMP
    DUMP_TEMP = file + ".bin"
    cmd = cmd + " f {}".format(file)
    # 将环境切换回来
    if s_e: appfiles.switch_windows()
    # 最大重试两次
    ret = -2
    listener({"state": "read"})
    for i in range(0, 2):
        # 没有密码，直接dump
        if executor.startPM3Task(cmd, TIMEOUT) == -1:
            ret = -2
            break
        # dump成功，回调并且返回
        if executor.hasKeyword("saved 12 blocks"):
            ret = 1
            break
    return ret


def dumpT55XX_Text(key=None):
    """
        以文本的形式返回T55XX的Dump
    :param key:
    :return:
    """
    ret_str = ""

    for p0_index in range(0, 8):
        failed = True

        # 在自动重试两次的情况下读取每个块
        for count in range(0, 2):
            block = readBlock(key, p0_index)
            if block is not None:
                ret_str += block
                failed = False
                break

        if failed:
            return None

    for p1_index in range(0, 4):
        failed = True

        # 在自动重试两次的情况下读取每个块
        for count in range(0, 2):
            block = readBlock(key, p1_index, 1)
            if block is not None:
                ret_str += block
                failed = False
                break

        if failed:
            return None

    return ret_str


def is_b0_lock(b0_data):
    b0_data = str(b0_data).replace("0x", "").replace("0X", "")
    if len(b0_data) != 8: raise Exception("传入的b0_data有误，不是4个字节的长度的数据。")
    b_ctrl_hex_str = b0_data[6:8]
    b_ctrl_hex_int = int(b_ctrl_hex_str, 16)
    bit_lock = (b_ctrl_hex_int & (1 << 4)) >> 4
    return bit_lock == 1


def switch_lock(b0_data, lock_enable):
    b0_data = str(b0_data).replace("0x", "").replace("0X", "")
    if len(b0_data) != 8: raise Exception("传入的b0_data有误，不是4个字节的长度的数据。")
    b_ctrl_hex_int = int(b0_data, 16)
    lock_enable = int(lock_enable)
    print("值: ", b_ctrl_hex_int)
    return hex(b_ctrl_hex_int | (lock_enable << 4)).replace("0x", "").replace("0X", "").rjust(8, "0").upper()


def getB0WithKey(key=None, from_detect=False):
    base_detect_cmd = "lf t55xx detect"
    if key is not None:
        base_detect_cmd += " p " + key
    if executor.startPM3Task(base_detect_cmd, 5000) != -1:
        if from_detect and executor.hasKeyword("Block0"):
            # Block0         : 0x603E1040
            return executor.getContentFromRegexG(r"Block0         : 0x([A-Fa-f0-9]+)", 1)
        else:
            base_dump_cmd = None

            if executor.hasKeyword("Password Set   : Yes"):
                base_dump_cmd = "lf t55xx read b 0"
                if key is not None:
                    base_dump_cmd += " p " + key + " o"

            if executor.hasKeyword("Password Set   : No"):
                base_dump_cmd = "lf t55xx read b 0"

            if base_dump_cmd is not None:
                if executor.startPM3Task(base_dump_cmd, 10000) != -1:
                    return executor.getContentFromRegexG(r" 00 \| ([A-Fa-f0-9]+) \|", 1)
    return -1


def getB0WithKeys(keys=None, from_detect=False):
    if isinstance(keys, list):
        for key in keys:
            b0 = getB0WithKey(key, from_detect)
            if b0 != -1:
                return b0
    else:
        return getB0WithKey(keys, from_detect)
    return -1


def wipe_t(key=None):
    """
        真正的清空卡实现
    :return:
    """
    cmd = "lf t55xx wipe"
    if key is not None: cmd += " p " + key
    if executor.startPM3Task(cmd, 5000) == -1:
        return False
    return detectT55XX(cache_key=False) == 2


def wipe1(listener):
    """
        高配版本
    :return:
    """
    tmp = "20206666"

    if wipe_t(tmp):  # 如果能直接使用我司的密钥清空卡片，则认为是可用的容器卡
        return True

    detect_ret = detectT55XX(tmp, False)
    if detect_ret < 0:
        print("侦测出现异常，异常码: ", detect_ret)
        return False
    if detect_ret == 2:  # 没有加密，直接成功
        print("没有加密，不需要清空")
        return True

    # 加密，但是秘钥不是我们提供的秘钥
    # 则我们需要尝试清空
    if detect_ret == 1 or detect_ret == 3:
        # 扫描秘钥
        key_ret = chkT55xx(listener)
        # 判断是否成功的获取秘钥
        if isinstance(key_ret, str):  # 成功的获取到了秘钥
            # 获取到秘钥之后，我们需要尝试进行秘钥清空
            print("清空非官方卡")
            return wipe_t(key_ret)
        else:  # 无法获取到秘钥，则我们直接返回wipe失败
            return False

    # 加密，秘钥是我们的，说明卡片是我们提供的
    # 我们可以直接使用我们的秘钥进行清空
    if detect_ret == 4:
        print("清卡官方卡")
        return wipe_t(tmp)

    return False


def wipe0(listener):
    """
        低配版本
    :return:
    """
    return wipe_t("20206666")


def wipe(listener):
    """
        1、对于我们来说，，wipe是必定成功的，否则无法进行下一步
        2、高配版本，要么wipe官方卡成功，要么其他的卡成功，要么失败
        3、低配版本，要么wipe官方卡成功，要么失败，没有更多的选择
    :return:
    """

    # 测试开始 <
    if platform.system() == "Windows":
        print("windows测试下，自动切换为高版本的函数")
        return wipe1(listener)
    # 测试结束 >

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
            "x": wipe0,  # 低权限使能
            "xr": wipe0,  # 低权限使能
            "zh": wipe1,  # 中文版本相当于XS版本去除了ICLASS，其他权限不变
            "xs": wipe1,  # XS版本权限全开
            "uk": wipe1,  # UK版本也是权限全开
            "xsc": wipe1,  # XSC版本也是权限全开
        }

        # 解密UID
        aes_obj = AES.new(
            ret.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        i = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")

        return maps[i[3]](listener)
    except Exception as e:
        print("无法通过验证，必须使用我司的卡片: ", e)
        return wipe0(listener)
    # 验证结束 >


def lock(setkey=True, b0=None, check_detect=True):
    """
        请实现T55XX的上锁功能
        1、T55XX的上锁，在某些卡片上不能被使用，比如indala的长卡号
        2、最好是先写完数据再上锁再verify
    :return:
    """
    if b0 is None:
        # 先判断当前的55XX容器卡是否是未加密的卡
        if detectT55XX(cache_key=False) != 2:
            print("警告！！！，lock() -> 没有侦测到空的55XX容器卡")  # ，依旧尝试封卡，但是结果无法预测。
            return False

        # 禁止使用readBlock读取出来的B0，
        # 在PSK的卡片上，readblock读出的结果
        # 是有问题的！！！！！！！！！！
        # 使用该数据会导致卡片损坏
        # b0 = readBlock(None, 0)     N
        # 使用detect出来的b0           Y
        b0 = parser_b0()
        if len(b0) == 0:
            print("B0解析错误，无法进行BO置换")
            return False

    # 根据参数，选择是否需要先写秘钥块
    # lf t55xx write b 7 d 20206666
    tmp = "20206666"
    if setkey:  # 如果需要设置密钥，则需要先写第七块
        if executor.startPM3Task(f"lf t55xx write b 7 d {tmp}", 5000) == -1:
            return False

    # 写入配置块
    if executor.startPM3Task("lf t55xx write b 0 d " + switch_lock(b0, True), 5000) == -1:
        return False

    if setkey and check_detect:  # 只有需要设置密钥的情况下才校验我司的密钥
        # 校验加密结果
        ret = detectT55XX(tmp, False) == 4
        print("封锁完成，结果: ", ret)
        return ret
    else:
        print("不需要封锁")
        return True


# 此处我们提供一个默认秘钥集
# 用于替代打包进安装包中的秘钥数据
DEFAULT_KEYS = """
# known cloners
# ref. http://www.proxmark.org/forum/viewtopic.php?id=2022
51243648
000D8787
19920427
65857569 //chinese "handheld RFID writer" blue cloner from circa 2013 (also sold by xfpga.com)
# ref. http://kazus.ru/forums/showpost.php?p=1045937&postcount=77
05D73B9F
# ref. http://www.proxmark.org/forum/viewtopic.php?=
89A69E60
# ref lock
314159E0
# ref. http://www.proxmark.org/forum/viewtopic.php?pid=28115#p28115
AA55BBBB
# ref. http://www.proxmark.org/forum/viewtopic.php?pid=33376#p33376
A5B4C3D2
# ref. http://www.proxmark.org/forum/viewtopic.php?pid=30379#p30379
1C0B5848
# ref. http://www.proxmark.org/forum/viewtopic.php?pid=35075#p35075
00434343
44B44CAE
88661858
# paxton bullit?
575F4F4B
#
50520901
# default PROX
50524F58
# Default pwd, simple:
00000000
11111111
22222222
33333333
44444444
55555555
66666666
77777777
88888888
99999999
AAAAAAAA
BBBBBBBB
CCCCCCCC
DDDDDDDD
EEEEEEEE
FFFFFFFF
a0a1a2a3
b0b1b2b3
aabbccdd
bbccddee
ccddeeff
50415353
00000001
00000002
0000000a
0000000b
01020304
02030405
03040506
04050607
05060708
06070809
0708090A
08090A0B
090A0B0C
0A0B0C0D
0B0C0D0E
0C0D0E0F
01234567
12345678
10000000
20000000
30000000
40000000
50000000
60000000
70000000
80000000
90000000
A0000000
B0000000
C0000000
D0000000
E0000000
F0000000
10101010
01010101
11223344
22334455
33445566
44556677
55667788
66778899
778899AA
8899AABB
99AABBCC
AABBCCDD
BBCCDDEE
CCDDEEFF
0CB7E7FC # rfidler?
FABADA11 # china?
# 20 most common len==8
87654321
12341234
69696969
12121212
12344321
1234ABCD
11112222
13131313
10041004
#
31415926 # pii
abcd1234
20002000
19721972
aa55aa55 # amiboo
55aa55aa # rev amiboo
4f271149 # seeds ul-ev1
07d7bb0b # seeds ul-ev1
9636ef8f # seeds ul-ev1
b5f44686 # seeds ul-ev1
9E3779B9 # TEA
C6EF3720 # TEA
7854794A # xbox tea constant :)
F1EA5EED # burtle
""".strip()

"""
    处理嗅探的过程的py实现
"""
import re

import executor

# trace len = 17976 bytes
PATTERN_HF_TRACE_LEN = r"trace len = (\d+)"
# Reading 42247 bytes from device memory
PATTERN_LF_TRACE_LEN = r"Reading (\d+) bytes from device memory"


def sniff14AStart():
    """
        嗅探14A
    :return:
    """
    executor.startPM3Task("hf 14a sniff", 8000, rework_max=0)


def sniff14BStart():
    """
        嗅探14A
    :return:
    """
    executor.startPM3Task("hf 14b sniff", 8000, rework_max=0)


def sniffIClassAStart():
    """
        嗅探14A
    :return:
    """
    executor.startPM3Task("hf iclass sniff", 8000, rework_max=0)


def sniffTopazStart():
    """
        嗅探14A
    :return:
    """
    executor.startPM3Task("hf topaz sniff", 8000, rework_max=0)


def sniff125KStart():
    """
        嗅探14A
    :return:
    """
    executor.startPM3Task("lf sniff", 8000, rework_max=0)


def sniffT5577Start():
    """
        嗅探T5577
    :return:
    """
    # 在嗅探开始前，我们应当进行初始化配置
    executor.startPM3Task("lf config a 0 t 20 s 10000", 5000)
    # 然后启动嗅探
    # 我们默认不超时，并且不允许自动重启任务
    executor.startPM3Task("lf t55xx sniff", -1, rework_max=0)


def parserLfTraceLen():
    """
        解析嗅探的数据的长度
    :return:
    """
    lenStr = executor.getContentFromRegexG(PATTERN_LF_TRACE_LEN, 1)
    if len(lenStr) > 0:
        return int(lenStr)
    else:
        return 0


def parserKeyForLine(line, regex):
    """
        解析秘钥从行中
    :param regex:
    :param line:
    :return:
    """
    sea_obj = re.search(regex, line)
    if sea_obj is None:
        return None
    return sea_obj.group(1)


def parserT5577OkKeyForLine(line):
    """
        解析秘钥从行中
    :param line:
    :return:
    """
    return parserKeyForLine(line, r"Default pwd write\s+\|\s+([A-Fa-f0-9]{8})\s\|")


def parserT5577LeadingKeyForLine(line):
    """
        解析秘钥从行中
    :param line:
    :return:
    """
    return parserKeyForLine(line, r"Leading [0-9a-zA-Z]* pwd write\s+\|\s+([A-Fa-f0-9]{8})\s\|")


def parserT5577WriteKeyForLine(line):
    """
        解析秘钥从行中
    :param line:
    :return:
    """
    return parserKeyForLine(line, r"Default write\s+\|\s+([A-Fa-f0-9]{8})\s\|")


def parserKeysForT5577(parser_fun):
    """
        解析嗅探到的所有的T5577的秘钥
    :return:
    """
    if executor.CONTENT_OUT_IN__TXT_CACHE is None:
        return []
    print("输出: ", executor.CONTENT_OUT_IN__TXT_CACHE)
    lines = executor.CONTENT_OUT_IN__TXT_CACHE.split("\n")
    if lines is not None and len(lines) > 0:
        key_ret = []
        for line in lines:
            key = parser_fun(line)
            if key is not None:
                key_ret.append(key)
        return key_ret

    return []


def parserHfTraceLen():
    """
        解析嗅探的数据的长度
    :return:
    """
    lenStr = executor.getContentFromRegexG(PATTERN_HF_TRACE_LEN, 1)
    if len(lenStr) > 0:
        return int(lenStr)
    else:
        return 0


def parserM1KeyForLine(line):
    """
        解析秘钥从行中
    :param line:
    :return:
    """
    regex = r"key\s+([A-Fa-f0-9]+)"
    sea_obj = re.search(regex, line)
    if sea_obj is None:
        return None
    return sea_obj.group(1)


def parserDataForSCA(line, src="Rdr", crc="ok", annotation=""):
    """
        解析数据，从指定的源，crc结果，和注释
    :param line:
    :param src:
    :param crc:
    :param annotation:
    :return:
    """
    # | Rdr |93  70  2a  60  3c  10  66  ed  dc                                       |  ok | SELECT_UID
    regex = r"\|\s*{}\s*\|\s*([a-fA-F0-9 !]+)\s*\|\s*{}\s*\|\s*{}".format(src, crc, annotation)
    sea_obj = re.search(regex, line)
    if sea_obj is None: return None
    return sea_obj.group(1).upper().replace(" ", "")


def parserUidForData(line):
    """
        尝试截取UID，从数据中
    :param line:
    :return:
    """
    line = str(line)
    if line is None:
        return None
    try:
        return line[4:12]
    except Exception as e:
        print(e)
    return None


def parserUidForKeyIndex(index, lines):
    """
        从秘钥所在的行的位置反查UID，逆序查询第一个出现的关键词
    :param index:
    :param lines:
    :return:
    """
    try:
        for index_uid in range(index - 1, -1, -1):  # 逆序查询
            line = lines[index_uid]  # 逆序取出数据行
            uid2 = parserDataForSCA(line, annotation="SELECT_UID-2")
            uid1 = parserDataForSCA(line, annotation="SELECT_UID")
            # 如果UID2的数据存在，则我们需要递归进行获取uid1
            if uid2 is not None:
                uid1 = parserUidForKeyIndex(index_uid - 1, lines)
                return uid1[2:] + parserUidForData(uid2)
            if uid1 is not None:
                return str(parserUidForData(uid1))
    except Exception as e:
        print(e)
    return None


def parserKeyForM1():
    """
        解析可能存在的MF密钥
    :return:
    """
    # last used key ffffffffffff
    # key ffffffffffff prng WEAK
    # 返回值例子  uid  秘钥集
    # ret_dict = {"uid": [], }
    ret_dict = {}
    # 按行检索
    if executor.CONTENT_OUT_IN__TXT_CACHE is None:
        return ret_dict
    content_lines = executor.CONTENT_OUT_IN__TXT_CACHE.split("\n")
    for line_index in range(len(content_lines)):
        content_line = content_lines[line_index]
        # 检查当前的行是否是秘钥行
        key = parserM1KeyForLine(content_line)
        if key is None:
            continue
        uid = parserUidForKeyIndex(line_index, content_lines)
        if uid is None:
            continue
        if uid not in ret_dict:
            ret_dict[uid] = []
        ret_dict[uid].append(key)
    return ret_dict

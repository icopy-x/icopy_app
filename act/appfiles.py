"""
    APP运行时需要用到的文件操作
"""
import platform
import os
import re

import commons
import tagtypes
import version

# 基础扩展目录
PATH_MS = ""

# 嗅探数据的保存目录
PATH_TRACE = ""

# 卡片数据的保存目录
PATH_DUMP = ""
PATH_DUMP_T55XX = ""
PATH_DUMP_HF14A = ""
PATH_DUMP_MFU = ""
PATH_DUMP_M1 = ""
PATH_DUMP_LEGIC = ""
PATH_DUMP_ICODE = ""
PATH_DUMP_FELICA = ""
PATH_DUMP_ICLASS = ""
PATH_DUMP_EM4X05 = ""
PATH_DUMP_EM410x = ""
PATH_DUMP_HID = ""
PATH_DUMP_INDALA = ""
PATH_DUMP_AWID = ""
PATH_DUMP_IOPROX = ""
PATH_DUMP_GPROXII = ""
PATH_DUMP_SECURAKEY = ""
PATH_DUMP_VIKING = ""
PATH_DUMP_PYRAMID = ""
PATH_DUMP_FDX = ""
PATH_DUMP_GALLAGHER = ""
PATH_DUMP_JABLOTRON = ""
PATH_DUMP_KERI = ""
PATH_DUMP_NEDAP = ""
PATH_DUMP_NORALSY = ""
PATH_DUMP_PAC = ""
PATH_DUMP_PARADOX = ""
PATH_DUMP_PRESCO = ""
PATH_DUMP_VISA2000 = ""
PATH_DUMP_NEXWATCH = ""

# 秘钥文件的保存目录
PATH_KEYS = ""
PATH_KEYS_M1 = ""
PATH_KEYS_T5577 = ""

# 日志文件
PATH_LOG_FILE = ""

sep = ""

# 某些dump特定的前缀名称
PREFIX_NAME_UL      = "M0-UL"
PREFIX_NAME_ULC     = "M0-UL-C"
PREFIX_NAME_UL_EV1  = "M0-UL-EV1"
PREFIX_NAME_NTAG213 = "NTAG213"
PREFIX_NAME_NTAG215 = "NTAG215"
PREFIX_NAME_NTAG216 = "NTAG216"


# dump目录中的文件夹名称
DIR_NAME_T55XX      = "t55xx"
DIR_NAME_HF14A      = "14443a"
DIR_NAME_MFU        = "mfu"
DIR_NAME_M1         = "mf1"
DIR_NAME_LEGIC      = "legic"
DIR_NAME_ICODE      = "icode"
DIR_NAME_FELICA     = "felica"
DIR_NAME_ICLASS     = "iclass"
DIR_NAME_EM4X05     = "em4x05"
DIR_NAME_EM410x     = "em410x"
DIR_NAME_HID        = "hid"
DIR_NAME_INDALA     = "indala"
DIR_NAME_AWID       = "awid"
DIR_NAME_IOPROX     = "ioprox"
DIR_NAME_GPROXII    = "gproxii"
DIR_NAME_SECURAKEY  = "securakey"
DIR_NAME_VIKING     = "viking"
DIR_NAME_PYRAMID    = "pyramid"
DIR_NAME_FDX        = "fdx"
DIR_NAME_GALLAGHER  = "gallagher"
DIR_NAME_JABLOTRON  = "jablotron"
DIR_NAME_KERI       = "keri"
DIR_NAME_NEDAP      = "nedap"
DIR_NAME_NORALSY    = "noralsy"
DIR_NAME_PAC        = "pac"
DIR_NAME_PARADOX    = "paradox"
DIR_NAME_PRESCO     = "presco"
DIR_NAME_VISA2000   = "visa2000"
DIR_NAME_NEXWATCH   = "nexwatch"

# dump到抽象类型的名称映射
DUMP_TYPE_MAP = {
    DIR_NAME_T55XX:     "T5577 ID",
    DIR_NAME_HF14A:     "ISO 14443A",
    DIR_NAME_MFU:       "Ultralight & NTAG",
    DIR_NAME_M1:        "Mifare Classic",
    DIR_NAME_LEGIC:     "Legic Mini 256",
    DIR_NAME_ICODE:     "15693 ICODE, STSA",
    DIR_NAME_FELICA:    "Felica",
    DIR_NAME_ICLASS:    "iClass",
    DIR_NAME_EM4X05:    "EM4X05 ID",
    DIR_NAME_EM410x:    "EM410x ID",
    DIR_NAME_HID:       "HID Prox ID",
    DIR_NAME_INDALA:    "Indala ID",
    DIR_NAME_AWID:      "AWID ID",
    DIR_NAME_IOPROX:    "IO Prox ID",
    DIR_NAME_GPROXII:   "GProx II ID",
    DIR_NAME_SECURAKEY: "Securakey ID",
    DIR_NAME_VIKING:    "Viking ID",
    DIR_NAME_PYRAMID:   "Pyramid ID",
    DIR_NAME_FDX:       "Animal ID(FDX)",
    DIR_NAME_GALLAGHER: "GALLAGHER ID",
    DIR_NAME_JABLOTRON: "Jablotron ID",
    DIR_NAME_KERI:      "KERI ID",
    DIR_NAME_NEDAP:     "NEDAP ID",
    DIR_NAME_NORALSY:   "Noralsy ID",
    DIR_NAME_PAC:       "PAC ID",
    DIR_NAME_PARADOX:   "Paradox ID",
    DIR_NAME_PRESCO:    "Presco ID",
    DIR_NAME_VISA2000:  "Visa2000 ID",
    DIR_NAME_NEXWATCH:  "NexWatch ID",
}


def switch_mode(system):
    global PATH_MS, PATH_TRACE, sep, PATH_DUMP, PATH_DUMP_T55XX, PATH_DUMP_ICODE, PATH_DUMP_ICLASS
    global PATH_DUMP_MFU, PATH_DUMP_M1, PATH_DUMP_LEGIC, PATH_DUMP_FELICA, PATH_DUMP_EM4X05
    global PATH_DUMP_EM410x, PATH_DUMP_HID, PATH_DUMP_INDALA, PATH_DUMP_AWID, PATH_DUMP_IOPROX
    global PATH_DUMP_GPROXII, PATH_DUMP_SECURAKEY, PATH_DUMP_VIKING, PATH_DUMP_PYRAMID, PATH_DUMP_FDX
    global PATH_DUMP_GALLAGHER, PATH_DUMP_JABLOTRON, PATH_DUMP_KERI, PATH_DUMP_NEDAP, PATH_DUMP_NORALSY
    global PATH_DUMP_PAC, PATH_DUMP_PARADOX, PATH_DUMP_PRESCO, PATH_DUMP_VISA2000, PATH_KEYS, PATH_KEYS_M1
    global PATH_DUMP_HF14A, PATH_DUMP_NEXWATCH
    global PATH_LOG_FILE, PATH_KEYS_T5577

    if system == 'Windows' or system == 'windows':
        PATH_MS = "wintest\\" + "upan\\"
        sep = "\\"
        os.path.sep = sep
    else:
        PATH_MS = commons.PATH_UPAN
        sep = "/"
        os.path.sep = sep

    # 保存嗅探的数据
    PATH_TRACE = PATH_MS + "trace"
    # 保存卡片数据
    PATH_DUMP = PATH_MS + "dump" + sep
    # 保存秘钥数据
    PATH_KEYS = PATH_MS + "keys" + sep

    PATH_DUMP_T55XX = PATH_DUMP + DIR_NAME_T55XX
    PATH_DUMP_HF14A = PATH_DUMP + DIR_NAME_HF14A
    PATH_DUMP_MFU = PATH_DUMP + DIR_NAME_MFU
    PATH_DUMP_M1 = PATH_DUMP + DIR_NAME_M1
    PATH_DUMP_LEGIC = PATH_DUMP + DIR_NAME_LEGIC
    PATH_DUMP_ICODE = PATH_DUMP + DIR_NAME_ICODE
    PATH_DUMP_FELICA = PATH_DUMP + DIR_NAME_FELICA
    PATH_DUMP_ICLASS = PATH_DUMP + DIR_NAME_ICLASS
    PATH_DUMP_EM4X05 = PATH_DUMP + DIR_NAME_EM4X05
    PATH_DUMP_EM410x = PATH_DUMP + DIR_NAME_EM410x
    PATH_DUMP_HID = PATH_DUMP + DIR_NAME_HID
    PATH_DUMP_INDALA = PATH_DUMP + DIR_NAME_INDALA
    PATH_DUMP_AWID = PATH_DUMP + DIR_NAME_AWID
    PATH_DUMP_IOPROX = PATH_DUMP + DIR_NAME_IOPROX
    PATH_DUMP_GPROXII = PATH_DUMP + DIR_NAME_GPROXII
    PATH_DUMP_SECURAKEY = PATH_DUMP + DIR_NAME_SECURAKEY
    PATH_DUMP_VIKING = PATH_DUMP + DIR_NAME_VIKING
    PATH_DUMP_PYRAMID = PATH_DUMP + DIR_NAME_PYRAMID
    PATH_DUMP_FDX = PATH_DUMP + DIR_NAME_FDX
    PATH_DUMP_GALLAGHER = PATH_DUMP + DIR_NAME_GALLAGHER
    PATH_DUMP_JABLOTRON = PATH_DUMP + DIR_NAME_JABLOTRON
    PATH_DUMP_KERI = PATH_DUMP + DIR_NAME_KERI
    PATH_DUMP_NEDAP = PATH_DUMP + DIR_NAME_NEDAP
    PATH_DUMP_NORALSY = PATH_DUMP + DIR_NAME_NORALSY
    PATH_DUMP_PAC = PATH_DUMP + DIR_NAME_PAC
    PATH_DUMP_PARADOX = PATH_DUMP + DIR_NAME_PARADOX
    PATH_DUMP_PRESCO = PATH_DUMP + DIR_NAME_PRESCO
    PATH_DUMP_VISA2000 = PATH_DUMP + DIR_NAME_VISA2000
    PATH_DUMP_NEXWATCH = PATH_DUMP + DIR_NAME_NEXWATCH

    PATH_KEYS_M1 = PATH_KEYS + DIR_NAME_M1
    PATH_KEYS_T5577 = PATH_KEYS + DIR_NAME_T55XX

    # 保存日志信息
    PATH_LOG_FILE = PATH_MS + "app.log"


# 默认切换一下当前的环境变量
switch_mode(platform.system())


def switch_linux():
    """
        切换到linux环境
    :return:
    """
    switch_mode("linux")


def switch_windows():
    """
        切换到windows环境
    :return:
    """
    switch_mode("windows")


def switch_current():
    """
        切换到当前的环境
    :return:
    """
    switch_mode(platform.system())


def isWindows():
    system = platform.system()
    return system == 'Windows' or system == 'windows'


def get_num(name):
    """
        从文件名里获取规范定义的索引
        比如 XXX_XXX-XXX_1.json
        其中， _1 是必须存在的元素
    :return: 如果有索引信息，返回索引值，否则，返回 0
    """
    obj = re.search(r".*_(\d+)\.?", name)
    if obj is None:
        return 0
    return int(obj.group(1))


def delIfHaveSep(s):
    s = str(s)
    if s.endswith(sep):
        return s[0:len(s) - 1]
    return s


def get_max_num(path, name, suffix):
    """
        从某个文件所在的文件夹或者直接从某个文件夹中获取列表，
        然后进行排列获取最大的序号
    :param suffix:
    :param name:
    :param path:
    :return:
    """
    if os.path.isfile(path):
        path = os.path.dirname(path)
    ls = os.listdir(path)
    nums = []
    for l in ls:
        if l.startswith(name) and l.endswith(suffix):
            file_name = delIfHaveSep(path) + sep + l
            nums.append(get_num(file_name))
    if len(nums) == 0:
        return 0
    return max(nums)


def mkdirs(path):
    """
        创建文件夹
    :param path:
    :return:
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    # 我们应当自动创建在U盘目录下的文件夹
    # 如果当前需要创建的文件夹是在linux下
    if path.startswith(commons.PATH_UPAN):
        # print("将会自动在ICopy下创建该目录: ", path)
        commons.mkdirs_on_icopy(path)


def mkfile(file):
    """
        创建文件
    :param file:
    :return:
    """
    if os.path.exists(file):
        # 文件已经存在的情况下我们可以不创建文件。
        return
    # 获取根路径
    path = os.path.dirname(file)
    mkdirs(path)
    name = os.path.basename(file)
    name = replace_char_on_name(name)
    file = os.path.join(
        path,
        name
    )
    try:
        with open(file, "w"):
            pass
    except Exception as e:
        print("mkfile: " + str(e))


def create_file(name, path, suffix):
    """
    :param path: 文件所在的路径
    :param suffix:  文件后缀
    :param name: 文件名或者文件夹名
    :return:
    """
    mkdirs(path)
    max_num = get_max_num(path, name, suffix)
    if suffix is not None and len(suffix) > 0:
        suffix = "." + suffix
    else:
        suffix = ""
    f = name + "_" + str(int(max_num) + 1) + suffix
    f = path + sep + f
    return f


def to_bytes(bytes_or_str):
    if isinstance(bytes_or_str, str):
        value = bytes_or_str.encode('utf-8')
    else:
        value = bytes_or_str
    return value  # Instance of bytes


def replace_char_on_name(name):
    """
        替换一些被禁止出现在文件名里面的符号
    :param name:
    :return:
    """
    if platform.system() == "Windows":
        # \  /  :  *  ?  "  <  >  |
        chars = {
            '\\': '-',
            '/': '-',
            ':': '=',
            '*': '@',
            '?': '#',
            '"': '\'',
            '<': '[',
            '>': ']',
            '|': '_or_',
        }
    else:
        chars = {
            '/': '-',
            ' ': '_',
            '(': '[',
            ')': ']',
            ':': '=',
        }

    for char in chars.keys():
        if name.count(char) > 0:
            print("警告，文件名不规范，将会自动修正，字符: ", char)
            name = name.replace(char, chars[char])
    return name


def save2any(str_or_bytes, file, append=False):
    """
        保存文件到任意目录
    :param append:
    :param str_or_bytes:
    :param file:
    :return:
    """
    # 自动更换被限定的文件名字符
    path = os.path.dirname(file)
    name = os.path.basename(file)
    name = replace_char_on_name(name)
    file = os.path.join(
        path,
        name
    )
    print("保存的文件: ", file)
    # 转换为字节
    try:
        bytess = to_bytes(str_or_bytes)
        mkfile(file)
        # 打开并写入
        if append:
            mode = "ab"
        else:
            mode = "wb"
        with open(file, mode) as fd:
            fd.write(bytess)
            fd.flush()
        return True
    except Exception as e:
        print(e)
        return False


def create_default(prefix, name, path):
    f = create_file(prefix + "_" + str(name).replace(" ", ""), path, "")
    print("生成的文件: ", f)
    return f


def create_txt(prefix, name, path):
    f = create_file(prefix + "_" + str(name).replace(" ", ""), path, "txt")
    print("生成的文件: ", f)
    return f


def create_trace(typ, suffix="txt"):
    """
        创建一个trace文件在trace文件夹并且进行返回文件的路径
    :return:
    """
    f = create_file(typ, PATH_TRACE, suffix)
    print("生成的文件: ", f)
    return f


FILE_PREFIX_EM410X = "EM410x-ID"
FILE_PREFIX_HIDPROX = "HID-Prox-ID"
FILE_PREFIX_INDALA = "Indala-ID"
FILE_PREFIX_AWID = "AWID-ID"
FILE_PREFIX_IOPROX = "IO-Prox-ID"
FILE_PREFIX_GPROXII = "G-ProxII-ID"
FILE_PREFIX_SECURAKEY = "Securakey-ID"
FILE_PREFIX_VIKING = "VIKING-ID"
FILE_PREFIX_PYRAMID = "Pyramid-ID"
FILE_PREFIX_FDX = "FDX-ID"
FILE_PREFIX_GALLAGHER = "GALLAGHER-ID"
FILE_PREFIX_JABLOTRON = "Jablotron-ID"
FILE_PREFIX_KERI = "KERI-ID"
FILE_PREFIX_NEDAP = "NEDAP-ID"
FILE_PREFIX_NORALSY = "Noralsy-ID"
FILE_PREFIX_PAC = "PAC-ID"
FILE_PREFIX_PARADOX = "Paradox-ID"
FILE_PREFIX_PRESCO = "Presco-ID"
FILE_PREFIX_VISA2000 = "Visa2000-ID"
FILE_PREFIX_NEXWATCH = "NexWatch-ID"
FILE_PREFIX_T55XX = "T55xx"
FILE_PREFIX_LEGIC = "Legic"
FILE_PREFIX_ICODE = "ICODE"
FILE_PREFIX_FELICA = "FeliCa"
FILE_PREFIX_ICLASS = "Iclass"
FILE_PREFIX_EM4X05 = "EM4305"


def create_t55xx(b0, b1, b2):
    name = "{}_{}_{}".format(b0, b1, b2)
    return create_default(FILE_PREFIX_T55XX, name, PATH_DUMP_T55XX)


def create_m1(name, suffix):
    """
        创建M1的文件名
    :param name:
    :param suffix:
    :return:
    """
    name = "M1-" + name
    return create_file(name, PATH_DUMP_M1, suffix)


def create_mfu(prefix, name):
    return create_default(prefix, name, PATH_DUMP_MFU)


def create_legic(name):
    return create_default(FILE_PREFIX_LEGIC, name, PATH_DUMP_LEGIC)


def create_icode(name):
    return create_default(FILE_PREFIX_ICODE, name, PATH_DUMP_ICODE)


def create_felica(name):
    f = create_file(FILE_PREFIX_FELICA + "_" + name, PATH_DUMP_FELICA, "txt")
    print("生成的文件: ", f)
    return f


def create_iclass(typ, name):
    prefix = FILE_PREFIX_ICLASS + "-" + typ
    return create_default(prefix, name, PATH_DUMP_ICLASS)


def create_em4x05(name):
    return create_default(FILE_PREFIX_EM4X05, name, PATH_DUMP_EM4X05)


def create_em410x(name):
    return create_txt(FILE_PREFIX_EM410X, name, PATH_DUMP_EM410x)


def create_hid(name):
    return create_txt(FILE_PREFIX_HIDPROX, name, PATH_DUMP_HID)


def create_indala(name):
    return create_txt(FILE_PREFIX_INDALA, name, PATH_DUMP_INDALA)


def create_awid(name):
    return create_txt(FILE_PREFIX_AWID, name, PATH_DUMP_AWID)


def create_ioprox(name):
    return create_txt(FILE_PREFIX_IOPROX, name, PATH_DUMP_IOPROX)


def create_gproxii(name):
    return create_txt(FILE_PREFIX_GPROXII, name, PATH_DUMP_GPROXII)


def create_securakey(name):
    return create_txt(FILE_PREFIX_SECURAKEY, name, PATH_DUMP_SECURAKEY)


def create_viking(name):
    return create_txt(FILE_PREFIX_VIKING, name, PATH_DUMP_VIKING)


def create_pyramid(name):
    return create_txt(FILE_PREFIX_PYRAMID, name, PATH_DUMP_PYRAMID)


def create_fdx(name):
    return create_txt(FILE_PREFIX_FDX, name, PATH_DUMP_FDX)


def create_gallagher(name):
    return create_txt(FILE_PREFIX_GALLAGHER, name, PATH_DUMP_GALLAGHER)


def create_jablotron(name):
    return create_txt(FILE_PREFIX_JABLOTRON, name, PATH_DUMP_JABLOTRON)


def create_keri(name):
    return create_txt(FILE_PREFIX_KERI, name, PATH_DUMP_KERI)


def create_nedap(name):
    return create_txt(FILE_PREFIX_NEDAP, name, PATH_DUMP_NEDAP)


def create_noralsy(name):
    return create_txt(FILE_PREFIX_NORALSY, name, PATH_DUMP_NORALSY)


def create_pac(name):
    return create_txt(FILE_PREFIX_PAC, name, PATH_DUMP_PAC)


def create_paradox(name):
    return create_txt(FILE_PREFIX_PARADOX, name, PATH_DUMP_PARADOX)


def create_presco(name):
    return create_txt(FILE_PREFIX_PRESCO, name, PATH_DUMP_PRESCO)


def create_visa2000(name):
    return create_txt(FILE_PREFIX_VISA2000, name, PATH_DUMP_VISA2000)


def create_nexwatch(name):
    return create_txt(FILE_PREFIX_NEXWATCH, name, PATH_DUMP_NEXWATCH)


CREATE_NORMAL_ID = {
    tagtypes.EM410X_ID: create_em410x,
    tagtypes.HID_PROX_ID: create_hid,
    tagtypes.INDALA_ID: create_indala,
    tagtypes.AWID_ID: create_awid,
    tagtypes.IO_PROX_ID: create_ioprox,
    tagtypes.GPROX_II_ID: create_gproxii,
    tagtypes.SECURAKEY_ID: create_securakey,
    tagtypes.VIKING_ID: create_viking,
    tagtypes.PYRAMID_ID: create_pyramid,
    tagtypes.FDXB_ID: create_fdx,
    tagtypes.GALLAGHER_ID: create_gallagher,
    tagtypes.JABLOTRON_ID: create_jablotron,
    tagtypes.KERI_ID: create_keri,
    tagtypes.NEDAP_ID: create_nedap,
    tagtypes.NORALSY_ID: create_noralsy,
    tagtypes.PAC_ID: create_pac,
    tagtypes.PARADOX_ID: create_paradox,
    tagtypes.PRESCO_ID: create_presco,
    tagtypes.VISA2000_ID: create_visa2000,
    tagtypes.NEXWATCH_ID: create_nexwatch,
}


def search_mf1_dump(uid):
    """
        搜索相同的ID的DUMP文件，并且返回一个结果表
    :param uid:
    :return:
    """
    # 此处我们兼容两种UID卡号
    uid = "_" + uid.lower() + "_"
    # 默认转换列表中的所有文件名为小写
    ls = [s.lower() for s in os.listdir(PATH_DUMP_M1) if isinstance(s, str)]
    files = []
    for l in ls:
        # 仅仅搜索EML文件，方便进行字符串搜索
        # 此处我们应当忽略大小写敏感
        if l.find(uid) != -1 and l.endswith("eml"):
            file_name = delIfHaveSep(PATH_DUMP_M1) + sep + l
            files.append(file_name)
    return files


def create_mf1_keys(uid):
    """
        创建指定UID的MF卡的秘钥文件
    :param uid:
    :return:
    """
    file = PATH_KEYS_M1 + sep + "mf_" + uid.lower() + "_key.dic"
    mkfile(file)
    return file


def search_mf1_keys(uid):
    """
        搜索相同的ID的秘钥文件，并且返回一个结果表
    :param uid:
    :return:
    """
    try:
        uid = "_" + uid.lower() + "_"
        ls = [s.lower() for s in os.listdir(PATH_KEYS_M1) if isinstance(s, str)]
        files = []
        for l in ls:
            # 仅仅搜索dic文件，方便进行字符串搜索
            if l.find(uid) != -1 and l.endswith("dic"):
                file_name = delIfHaveSep(PATH_KEYS_M1) + sep + l
                files.append(file_name)
                print("搜索到秘钥文件: ", file_name)
        return files
    except Exception as e:
        print(e)
        return []


def create_t5577_keys():
    """
        创建T5577的秘钥文件
    :return:
    """
    file = PATH_KEYS_T5577 + sep + "t5577_key.dic"
    mkfile(file)
    return file


def create_14443a(name):
    return create_txt("14A", name, PATH_DUMP_HF14A)


def log_to_file(log_msg):
    """
        打印日志到记录文件中！
    :param log_msg: 将被加密保存的日志消息
    :return:
    """

    def split_text(text, length):
        text_list = []  # 存放结果的列表
        if len(text) < length:
            return [text]
        index = 0
        while index < len(text):
            text_list.append(
                text[index: index + length]
            )
            index = index + length
        return text_list

    try:
        mkdirs(os.path.dirname(PATH_LOG_FILE))
        with open(PATH_LOG_FILE, mode="a") as fd:
            fd.write("************************** New Trace **************************\n")
            fd.write(f"-- Type : {version.getTYP()}\n")
            fd.write(f"--  HW  : {version.getHW()}\n")
            fd.write(f"-- HMI  : {version.getHMI()}\n")
            fd.write(f"--  OS  : {version.getOS()}\n")
            fd.write(f"--  PM  : {version.getPM()}\n")
            fd.write(f"--  SN  : {version.getSN()}\n")
            fd.write("--:\n")
            # 此处进行字符串切割，避免过长的字符串出现在一行上
            if log_msg is not None and len(log_msg) > 0:
                msgs = split_text(log_msg, 88)
                if len(msgs) > 0:
                    for msg in msgs:
                        fd.write(msg + "\n")
            else:
                fd.write("No Exception Message\n")
            fd.write("\n\n")
    except Exception as e:
        print("保存日志异常: ", e)


def get_card_list():
    """
        获取当前读卡历史的卡包列表
        注意，此函数返回两个列表，
        第一个列表是目录名称，
        第二个列表是类型名称，
    :return:
    """
    try:
        dir_list_raw = os.listdir(PATH_DUMP)
    except Exception as e:
        print(e)
        dir_list_raw = []

    dir_list_ret = []
    typ_list_ret = []

    for dir_name in dir_list_raw:
        # 判断我们是否支持此文件夹到卡片dump类型的映射
        if dir_name in DUMP_TYPE_MAP:
            dir_list_ret.append(dir_name)
            typ_list_ret.append(DUMP_TYPE_MAP[dir_name])

    return dir_list_ret, typ_list_ret


def read_text(file):
    """
        读取文件中的文本内容
    :param file: 将被读取的文件的路径
    :return:
    """
    try:
        with open(file, mode="r") as fd:
            return fd.read()
    except Exception as e:
        print(e)
        return ""

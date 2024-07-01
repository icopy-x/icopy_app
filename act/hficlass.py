# -*- coding: UTF-8 -*-
import base64
import hashlib
import os
import platform
import re
import subprocess

from Crypto.Cipher import AES

import commons
import executor
import tagtypes
import version

# 定义一下ICLASS标签的秘钥
# KEY_LEGACY_DEFAULT = "AFA785A7DAB33378"
# KEY_ICLASS_NIKOLA = "2020666666668888"

# 动态生成的基于AES加密的秘钥组
# 此处什么也不用定义，让生成器生成
KEYS_ICLASS_NIKOLA = ""

# 测试开始 <
if platform.system() == "Windows":
    # 我们直接使用配置脚本里面的秘钥内容
    # 但是要引入库
    # 因此我们根据工程的定位找到相应的库文件
    import sys
    sys.path.append("../../icopy_utils/ipk_pack_center")

    import icopy_iclass

    KEYS_ICLASS_NIKOLA = icopy_iclass.KEYS
# 测试结束 >


def search_se_dev_reader():
    """
        寻找iclassse的专属读头
    :return:
    """
    dev_path = "/dev"

    if platform.system() == "Windows":
        # print("Windows下暂时不支持寻找iclassse的读头")
        return None

    try:
        devs = os.listdir(dev_path)
        if len(devs) == 0:
            return None

        # 开始过滤无关的设备
        tty_usb_list = []
        for dev in devs:
            if dev.startswith("ttyUSB"):
                tty_usb_list.append(dev)

        import serial

        # 我们现在过滤出来了一大堆的USB串口设备
        # 现在我们需要进行查询，查询哪个才是SE读头
        for dev in tty_usb_list:
            try:
                dev_ret = os.path.join(dev_path, dev)
                with serial.Serial(dev_ret, timeout=1) as ser:
                    ser.write(b"Who\r\n")
                    resp = ser.readline()
                    print("设备应答: ", resp)
                    if b"ISE" in resp:
                        return dev_ret
            except Exception as e:
                print(e)
                continue

    except Exception as e:
        print(e)
        return None

    return None


def search_se_tag_reader(dev, rd=True):
    """
        搜索SE的卡片信息并且返回

        $A_CARD_START$
        wiedata#:11100101100110111001000001
        Bit#:26
        FC#:203
        ID#:14112
        Hex#:2007966e41
        Blk7#:0000000007966e41
        Bits#:00000010000000000111100101100110111001000001
        $A_CARD_STOP$

    :return:
    """

    if platform.system() == "Windows":
        print("Windows下暂时不支持操作iclassse的读头")
        # return None

    try:
        buf = None

        import serial
        with serial.Serial(dev, timeout=1) as ser:
            start_read = True

            # 此处确保第一次启动读卡的时候可以发送启动指令
            if rd:
                # 启动读卡
                ser.write(b"RD\r\n")
                resp = ser.readline()
                print("设备应答: ", resp)
                if b"OK" in resp or b"??" in resp:
                    start_read = True
                else:
                    start_read = False

            # 启动读卡监听之后，我们进行读卡数据监听
            if start_read:
                buf = bytearray()
                # 然后进行等待
                while True:
                    line = ser.readline()
                    if b"$A_CARD_START$" in line:
                        buf = line
                        continue

                    if line is None or len(line) == 0:
                        break

                    buf += line

                    if b"$A_CARD_STOP$" in line:
                        break

        if buf is None or len(buf) == 0:
            print("没有发现有效地数据")
        else:
            buf = buf.decode(errors="ignore")
            print("读取到数据: ", buf)
            # 进行数据处理，生成dict
            tag = {
                # 类型也要有
                "type": tagtypes.ICLASS_SE,

                # 韦根
                "wiedata": re.search(r"wiedata#:([0-1]+)", buf).group(1),
                # 韦根的长度
                "bitlen": re.search(r"Bit#:([0-9]+)", buf).group(1),

                # FC
                "fc": re.search(r"FC#:([0-9]+)", buf).group(1),
                # CN
                "id": re.search(r"ID#:([0-9]+)", buf).group(1),

                # 卡号的ID吧
                "hex": re.search(r"Hex#:([0-9a-fA-F]+)", buf).group(1),
                # 第七块该用的数据
                "blck7": re.search(r"Blk7#:([0-9a-fA-F]+)", buf).group(1),
                # 原始比特流
                "bits": re.search(r"Bits#:([0-1]+)", buf).group(1),

                "found": True,
            }
            # 把比特流长度转为int之后
            # 判断长度是否复合SE卡片的标准长度
            # 目前已知的长度是26 ...
            bit_len_int = int(tag['bitlen'])
            if not (26 <= bit_len_int <= 37):
                print("长度不符合规范：", bit_len_int)
                return None  # 长度不正确，我们认为不可能是SE卡片

            return tag

    except Exception as e:
        print(e)
        return None


def readTagBlock(typ, block, key):
    """
        读取指定的块
    :param typ:
    :param block:
    :param key:
    :return:
    """
    # hf iclass rdbl b 1 k 0011223344556677
    # AFA785A7DAB33378
    cmd = "hf iclass rdbl b {} k {}".format(
        "{:02x}".format(block),
        key
    )

    if typ == tagtypes.ICLASS_ELITE:
        cmd += " e"

    if executor.startPM3Task(cmd, 8888) == -1:
        return ""
    # block 01 : 12 FF FF FF 7F 1F FF 3C
    data = executor.getContentFromRegexG(r" : ([a-fA-F0-9 ]+)", 1)
    data = data.upper().replace(" ", "").replace("0x", "").replace("0X", "")
    if len(data) > 0:
        return data

    return ""


def checkKey(typ, key):
    """
        检测一个秘钥是否正确
    :param typ:
    :param key:
    :return:
    """
    return len(readTagBlock(typ, 1, key)) != 0


def chkKeys_1(key_device, dic_file):
    """
        初始化步骤，解密秘钥并且生成文件
    :return:
    """

    # 解密UID
    aes_obj = AES.new(
        key_device.encode("utf-8"),
        AES.MODE_CFB,
        "VB1v2qvOinVNIlv2".encode("utf-8"),
    )

    # 全部解密
    tmp_key_list_str = aes_obj.decrypt(
        base64.b64decode(KEYS_ICLASS_NIKOLA)
    ).decode("utf-8")

    # 我们是通过命令行进行追加的，所以需要进行换行符的替换
    tmp_key_list_str = tmp_key_list_str.replace("\n", "\\n")
    # 最后，我们将内容写入到文件
    commons.append_str_on_icopy(tmp_key_list_str, dic_file)


def chkKeys_2(infos, file, suffix=".dic"):
    """
        验证步骤，根据秘钥文件进行读取验证
    :return:
    """
    # 开始验证
    chk_cmd = f"hf iclass chk f {file}"
    if infos["type"] == tagtypes.ICLASS_ELITE:
        chk_cmd += " e"

    ret = None
    timeout = 88888
    if executor.startPM3Task(chk_cmd, timeout) == 1:
        if executor.hasKeyword("Found valid key"):
            key = executor.getContentFromRegexG("Found valid key (.*)", 1).replace(" ", "")
            ret = tuple((infos["type"], key))

    # 操作完成后，我们一定要删除秘钥文件，以免被截留
    commons.delfile_on_icopy(file + suffix)
    return ret


def chkKeys(infos):
    """
        检测卡片的默认秘钥
    :param infos:
    :return:
    """

    # 先检测是否是LEGACY
    if checkKey(tagtypes.ICLASS_LEGACY, "AFA785A7DAB33378"):
        print("发现了默认出厂的L卡")
        return tuple((tagtypes.ICLASS_LEGACY, "AFA785A7DAB33378"))

    # 然后检测是否是我司出厂的L卡
    if checkKey(tagtypes.ICLASS_LEGACY, "2020666666668888"):
        print("发现了我司出厂的L卡")
        return tuple((tagtypes.ICLASS_LEGACY, "2020666666668888"))

    # 然后检测是否是我司出厂的新L卡
    if checkKey(tagtypes.ICLASS_LEGACY, "6666202066668888"):
        print("发现了我司出厂的L卡")
        return tuple((tagtypes.ICLASS_LEGACY, "6666202066668888"))

    # 然后检测是否是我司出厂的E卡
    if checkKey(tagtypes.ICLASS_ELITE, "2020666666668888"):
        print("发现了我司出厂的E卡")
        return tuple((tagtypes.ICLASS_ELITE, "2020666666668888"))

    # 无论如何，先生成秘钥文件
    tmp_keys_path_linux = "/tmp/.keys/"
    # 秘钥文件，不带后缀名
    tmp_keys_file = tmp_keys_path_linux + "iclass_tmp_keys"
    # 秘钥文件，带后缀名
    dic_file = tmp_keys_file + ".dic"
    # 生成临时文件
    commons.mkdirs_on_icopy(tmp_keys_path_linux)
    commons.recreate_on_icopy(dic_file)

    # 测试开始 <
    if platform.system() == "Windows":
        # 往里头写秘钥内容
        tmp_keys_list_str = KEYS_ICLASS_NIKOLA.replace("\n", "\\n")
        commons.append_str_on_icopy(tmp_keys_list_str, dic_file)
        # 然后直接返回chk结果，用于调试
        return chkKeys_2(infos, tmp_keys_file)
    # 测试结束 >

    # 此处我们需要进行实时解密IClass的秘钥
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
        key_device = ""  # 这个是秘钥，
        while count < len(r):
            tmp = format(int(r[count], 16) + int(r[count + 1], 16), "x")
            key_device += tmp[0]
            count += 2
        # 这里我们不做判断，只去映射
        maps = {
            "x": chkKeys,  # 不支持这个权限，但是又被破解者搬上去了的话，我们这里直接递归卡死
            "xr": chkKeys,  # 同样是递归卡死
            "zh": chkKeys,  # 中文版本不支持ICLASS，这没什么好说的，再次卡死
            "xs": chkKeys_1,  # XS版本是支持iClass的
            "uk": chkKeys_1,  # UK版本是支持iClass的
            "xsc": chkKeys_1,  # XSC版本是支持iClass的
        }
        # 解密UID
        aes_obj = AES.new(
            key_device.encode("utf-8"),
            AES.MODE_CFB,
            "VB1v2qvOinVNIlv2".encode("utf-8"),
        )
        # 全部解密
        destr = aes_obj.decrypt(base64.b64decode(version.UID)).decode("utf-8").split(",")
        # 映射结果
        maps[destr[3]](key_device, dic_file)
    except Exception as e:
        print("无法通过验证，禁止使用IClass的验证过程", e)
        return None
    # 验证结束 >

    return chkKeys_2(infos, tmp_keys_file)


def chk_type():
    # 先检测是否是L卡
    islegacy = checkKey(tagtypes.ICLASS_LEGACY, "AFA785A7DAB33378")
    if islegacy:
        return tuple((tagtypes.ICLASS_LEGACY, "AFA785A7DAB33378"))
    else:  # 然后检测是否是E卡
        ret = chkKeys({"type": tagtypes.ICLASS_ELITE})
        if ret is not None:
            return ret
    return -1


def parser():
    ret = chk_type()

    if ret == -1:
        key = None
        # 如果检测不到类型的话，默认是加密的未知密钥的elite
        typ = tagtypes.ICLASS_ELITE
    else:
        key = ret[1]
        typ = ret[0]

    if executor.startPM3Task("hf iclass info", 8888) == -1:
        return {"found": False}

    d = {
        "found": True, "type": typ, "key": key,
        "csn": executor.getContentFromRegexG(r"CSN:*\s([A-Fa-f0-9 ]+)", 1).replace(" ", ""),
    }

    # 进行一些信息截取
    print("搜索到的信息: ", d)
    return d

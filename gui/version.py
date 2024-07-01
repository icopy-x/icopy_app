"""
    提供一些版本信息
"""
import re

import executor
import hmi_driver

# SN是跟随机器，但是不属于机器，只属于固件包的
# 我们依赖这个空的序列号，出厂固件必须是空的序列号
SERIAL_NUMBER = None  # 需要动态生成串号
# 软件版本的字符串
VERSION_STR = "1.0.90"

# 硬件版本号，是实时生成的
HARDWARE_VER = "1.0"
# PM3的固件版本号，暂时是写死的
PM3_VER = "1.0.2"
# 版本号的起始标签
PM3_VER_TAG = "NIKOLA: v"
# 当前的APP依赖的PM3固件的版本号
PM3_VER_APP = f"{PM3_VER_TAG}3.1"
# 版本类型
# 注意，此版本类型仅供显示，不参与逻辑判断
TYP = "ICopy-XS"

# UID号，根据所有的信息拼接加密而成
# 根据设备信息拼接成的
# 分别是：
# 1、H3的CPU SN
# 2、PM3的FLASH ID
# 3、STM32的ID
# 4、当前的版本类型
# 加解密秘钥由CPU进行MD5三次生成16位的秘钥之后获得
# 例子: (CPU_ID, PM3_ID, STM32_ID, TYP)
# 其中，版本信息是以下例子之一: (x, xr, xs)
UID = "Unknown"

# HMI固件版本号为1.0，
# 1.0的版本非常老，是不支持RTC的
HMI_VER_1 = 1.0

# 硬件版本，这个是最老的硬件版本
HW_VER_15 = "1.5"


# TODO 临时测试
# def test():
#     # 小绿的测试信息
#     global SERIAL_NUMBER, HARDWARE_VER, UID
#     SERIAL_NUMBER = "00230001"
#     HARDWARE_VER = "1.5"
#     UID = "ENEpTccTe9DQeiyhSNlj/mJkZdk3ck+mjI5O1xisZ+In6AlW9yB95IX7uIRXf14BMcoi6FonvqKCTWgI8zhGD1uCYgovTr4NfPeWusk="
#
#
# # 测试条件生成
# test()


def getSN():
    """
        获取串号
    :return:
    """
    return SERIAL_NUMBER


def getHW():
    """
        获取硬件版本号
    :return:
    """
    return HARDWARE_VER


def getOS():
    """
        获取中控版本号
    :return:
    """
    return VERSION_STR


def getPM():
    """
        获取PM3的固件版本号
    :return:
    """
    try:
        return str(getPM3_Dynamic())
    except Exception as e:
        print("getPM", e)
    return PM3_VER


def getHMI():
    """
        获取屏幕控制程序的版本
    :return:
    """
    # 我们可以直接对接API，直接从STM32下位机中
    # 读取相关的版本信息
    try:
        return str(getHMI_Dynamic())
    except Exception as e:
        print("getHMI", e)
    return "1.0.2"


def getTYP():
    """
        获取当前的设备的版本类型
    :return:
    """
    return TYP


def getHMI_Dynamic(getflashver=False):
    """
        获取动态的HMI版本号，从固件中读取
        @:param getflashver 是否获取flash的版本信息
    :return:
    """
    try:
        # 非常重要，此处我们判断当前的下位机固件版本
        mcu_fw_version = hmi_driver.readhmiversion()
        if mcu_fw_version is None:
            raise Exception("固件版本号获取失败")

        mcu_fw_version = mcu_fw_version.decode()

        fw_version = mcu_fw_version.split(".")
        if len(fw_version) != 4:
            raise Exception("固件版本号不符合解析规则")

        if not getflashver:
            fw_version = float(f'{fw_version[0]}.{fw_version[1]}')
        else:
            fw_version = float(f'{fw_version[2]}.{fw_version[3]}')

        print("下位机固件版本: ", fw_version)
    except Exception as e:
        print("获取版本信息失败: ", e)
        fw_version = 0.0

    return fw_version


def current_limit(limit_enable):
    """
        降低充电电流，如果支持
        此功能是跟版本相关的，因此暂时放进version.py中
    :return:
    """
    # print("类型: ", type(version.getHW()), "值: ", version.getHW())
    if getHW() == HW_VER_15:
        print("旧的硬件不支持降电流")
        return

    # 啊，我们可以降低充电电流吗？
    # 降低充电电流功能仅仅在下位机固件版本 1.0 以上，而且不包括 1.0 的固件中才被支持
    if getHMI_Dynamic() > HMI_VER_1:

        # 如果启用限制，则使用最小充电电流
        if limit_enable:
            print("请求降低充电电流中")
            hmi_driver.current_min()
        else:  # 否则启用最大充电电流
            print("请求提升充电电流中")
            hmi_driver.current_max()

    else:
        print("固件版本过低，可能没有充电电流限制的API，跳过充电电流限制")
        return

    return


def is_rtc_support():
    """
        当前设备的固件是否支持RTC
        此功能是跟版本相关的，因此暂时放进version.py中
    :return:
    """
    return getHMI_Dynamic() > HMI_VER_1


def is_fw_update_support():
    """
        当前的硬件是否支持更新固件
            由于历史原因，1.5 版本不支持更新固件
            所以：
                当硬件版本等于 1.5 时，固件版本必须大于 1.0，才支持更新，否则不支持！
                当硬件版本大于 1.5 时，固件版本可以随便，因为，没有锁flash的问题。
    :return:
    """
    try:
        if getHW() == HW_VER_15:

            # 此处实现最终的逻辑，
            # 只有大于 1.0 的固件版本才可以进行更新
            if getHMI_Dynamic() > HMI_VER_1:
                return True

            # 不然的话不支持
            return False

        else:  # 不用说，当硬件版本号大于 1.5 ，更新永远可用
            return True

    except Exception as e:
        print(e)
        return False


def is_pm3_fw_same():
    """
        当前的中控程序要求的PM3客户端和固件的版本信息
            是否一致，如果不一致，就可以更新固件
    :return:
    """
    if executor.startPM3Task("hw ver", 6888, rework_max=1) == -1:
        # PM3的命令执行器出现了毛病
        # 我们不允许接下来的更新
        return False

    # """
    # [ ARM ]
    #   bootrom: RRG/Iceman/master/release (git)
    #        os: RRG/Iceman/master/release (git)
    #    NIKOLA: v3.0
    #   compiled with GCC 6.3.1 20170620
    # """

    hw_ver_content = executor.getPrintContent()
    print("PM3的版本信息输出是: ", hw_ver_content)

    return PM3_VER_APP in hw_ver_content


def getPM3_Dynamic():
    """
        获取详细的PM3的版本名称
    :return:
    """
    try:
        if executor.startPM3Task("hw ver", 6888, rework_max=1) == -1:
            # PM3的命令执行器出现了毛病
            # 我们无法获取版本码
            return "Unknown"

        # 获取到信息后，我们需要解析，将其获取出来
        hw_ver_content = executor.getPrintContent()
        if PM3_VER_TAG in hw_ver_content:
            # 发现了符合我们的预期的版本管理信息
            # 此时我们需要截取出来尾部的版本码数字信息
            ret = re.search(PM3_VER_TAG + r"(\d+\.\d+)", hw_ver_content)
            if ret is None:
                return PM3_VER
            else:
                return ret.group(1)

    except Exception as e:
        print(e)
        return PM3_VER

    # 1.0永远是最旧的版本启动码
    return PM3_VER

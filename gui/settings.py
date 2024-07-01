"""
    设置的保存与获取
"""
import config


def setVolume(value):
    """
        设置音量
        档位有 0 - 1 - 2 - 3 四个档位
        分别代表 关闭 - 低 - 中 - 高
    :param value:
    :return:
    """
    config.setKeyValue("volume", value)


def getVolume():
    """
        获取音量
        档位有 0 - 1 - 2 - 3 四个档位
        分别代表 关闭 - 低 - 中 - 高
    :return:
    """
    return int(config.getValue("volume", 1))


def setBacklight(value):
    """
        设置背光
        档位有 0 - 1 - 2  三个档位
        分别代表 低 - 中 - 高
    :return:
    """
    config.setKeyValue("backlight", value)


def getBacklight():
    """
        获取背光
        档位有 0 - 1 - 2  三个档位
        分别代表 低 - 中 - 高
    :return:
    """
    return int(config.getValue("backlight", 2))


def setSleepTime(value):
    """
        设置休眠的时间
    :param value:
    :return:
    """
    config.setKeyValue("sleep_time", value)


def getSleepTime():
    """
        获取休眠的时间
    :return:
    """
    return int(config.getValue("sleep_time", 1))


def fromLevelGetVolume(level):
    if level == 0:
        return 0
    if level == 1:
        return 20
    if level == 2:
        return 50
    if level == 3:
        return 100
    return 50


def fromLevelGetBacklight(level):
    if level == 0:
        return 20
    if level == 1:
        return 50
    if level == 2:
        return 100
    return 100


def fromLevelGetSleepTime(level):
    if level == 0:
        return -1
    elif level == 1:
        return 15
    elif level == 2:
        return 30
    elif level == 3:
        return 60
    elif level == 4:
        return 120
    elif level == 5:
        return 300
    elif level == 6:
        return 600

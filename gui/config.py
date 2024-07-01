"""
    配置基础操作
"""
import configparser
import os

__FILE = "data"

DEFAULT_SETTINGS = {
    # 初始化默认的值
    'backlight': '2',
    'volume': '2',
}


def getConf():
    """获取需要的配置信息"""
    if not os.path.exists(__FILE):
        try:
            os.mkdir(__FILE)
        except Exception as e:
            print(e)
    config = configparser.ConfigParser()
    if len(config.read("data/conf.ini")) > 0:
        return config
    else:
        config["DEFAULT"] = DEFAULT_SETTINGS
        setConf(config)
        return config


def setConf(conf):
    if conf is None: return
    try:
        with open('data/conf.ini', 'w') as configfile:
            conf.write(configfile)  # 将对象写入文件
            configfile.close()
    except Exception as e:
        print(e)
    return


def setKeyValue(k, v):
    """
        设置键值对进行保存
    :param k: 键
    :param v: 值
    :return:
    """
    conf = getConf()
    conf["DEFAULT"][k] = str(v)
    setConf(conf)


def getValue(key, default):
    """
        获取一个对应键的值，如果不存在这个键则返回一个默认值
    :param key:
    :param default:
    :return:
    """
    conf = getConf()
    dc = conf["DEFAULT"]
    if key in dc:
        return dc[key]
    setKeyValue(key, default)
    return default

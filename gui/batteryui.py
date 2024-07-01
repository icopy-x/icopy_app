"""
    控制电池电量的刷新显示
"""
from concurrent.futures import ThreadPoolExecutor

import threading

import audio
import hmi_driver

__BATTERY_BAR = list()
__EVENT = threading.Event()
__QUEUE = ThreadPoolExecutor(max_workers=1)
__UPDATING = False

# 缓存电池电量
__BATTERY_VALUE = 0
__CHARGING_STATE = 0

__BATTERY_RUN = False
__BATTERY_UPDATE = True


def register(battery_bar):
    """
        注册一个电池电量条的对象
    :param battery_bar:
    :return:
    """
    if __BATTERY_BAR.count(battery_bar) >= 1:
        return
    __BATTERY_BAR.append(battery_bar)
    battery_bar.setBattery(__BATTERY_VALUE)
    battery_bar.setCharging(__CHARGING_STATE)
    # 通知刷新
    __EVENT.set()


def unregister(battery_bar):
    """
        解注册电量条更新对象
    :param battery_bar:
    :return:
    """
    __BATTERY_BAR.remove(battery_bar)
    __EVENT.set()


def __update_views(battery, charging):
    global __CHARGING_STATE, __BATTERY_VALUE
    __BATTERY_VALUE = battery
    __CHARGING_STATE = charging

    # print("当前电量值：", __BATTERY_VALUE, " 是否在充电：", __CHARGING_STATE)
    # print("当前的UI队列长度: ", len(__BATTERY_BAR))
    for battery_bar in __BATTERY_BAR:
        if battery_bar.isDestroy():  # 判断电量条是否已经销毁
            __BATTERY_BAR.remove(battery_bar)
            continue
        # 刷新UI
        battery_bar.setCharging(charging)
        battery_bar.setBattery(battery)


def __run__():
    """
        运行时，轮询电量
    :return:
    """
    global __UPDATING

    while __BATTERY_RUN:
        # 每10秒轮询一次
        __EVENT.wait(10)
        __EVENT.clear()

        if not __BATTERY_UPDATE:
            continue

        __UPDATING = True

        # print("\n正在自动更新电池电量...")
        # 获取电量
        battery = hmi_driver.readbatpercent()
        # 获取充电状态
        charging = hmi_driver.requestChargeState()
        charging = True if charging == 1 or charging == 3 else False
        __update_views(battery, charging)
        # print("\n自动更新电池完成...")

        __UPDATING = False


def notifyCharging(is_charging):
    """
        通知充电状态的改变与刷新电池电量
    :param is_charging:
    :return:
    """

    # 播放充电音效
    if is_charging: audio.playChargingAudio()

    if __UPDATING:
        print("其他线程更新中，忽略此次notifyCharging操作")
        return

    def run():
        # 获取电量
        print("\n**************************************")
        battery = hmi_driver.readbatpercent()
        __update_views(battery, is_charging)
        print("收到通知，在notifyCharging里面更新成功。")
        print("**************************************\n")

    __QUEUE.submit(run)


def start():
    """
        开启电池状态轮询
    :return:
    """
    global __BATTERY_RUN, __BATTERY_UPDATE
    if __BATTERY_RUN:
        if not __BATTERY_UPDATE:
            __BATTERY_UPDATE = True
        return
    __BATTERY_RUN = True
    t = threading.Thread(target=__run__)
    t.start()
    return t


def pause():
    """
        顾名思义，暂停电量的请求
    :return:
    """
    __EVENT.set()
    global __BATTERY_UPDATE
    __BATTERY_UPDATE = False

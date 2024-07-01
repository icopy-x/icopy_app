import threading
import traceback

import keymap

from tkinter import Canvas

from serpool import send_msg

# 将activity入栈保存
_ACTIVITY_STACK = []
# 基础画布对象
window = None


class LifeCycle(object):
    """
        Activity的生命周期

        当一个Activity被初始化完成后会
        1、onCreate
        2、onData -> 如果有非None数据
        3、onResume

        当一个Activity被另一个Activity覆盖时会
        1、onPause

        当一个Activity被结束时
        1、onDestroy
        .....................
        2、onData -> 如果此Activity需要向上一层Activity返回数据时
        3、onResume -> 如果其上一层的栈中有Activity时
    """

    def __init__(self):
        self._life_created = False
        self._life_destroyed = False
        self._life_resumed = False
        self._life_paused = False

        # 使用同步锁来保护生命周期状态的准确性
        self._life_lock = threading.RLock()

    def _set_life_in_lock(self, attr, value):
        """
            在同步锁中更新属性值
        :param attr:
        :param value:
        :return:
        """
        with self._life_lock:
            setattr(self, f"_life_{attr}", value)

    @property
    def created(self):
        """
            已经执行完创建
        :return:
        """
        with self._life_lock:
            return self._life_created

    @created.setter
    def created(self, value):
        self._set_life_in_lock("created", value)

    @property
    def destroyed(self):
        """
            已经执行完销毁
        :return:
        """
        with self._life_lock:
            return self._life_destroyed

    @destroyed.setter
    def destroyed(self, value):
        self._set_life_in_lock("destroyed", value)

    @property
    def resumed(self):
        """
            已经执行完恢复运行
        :return:
        """
        with self._life_lock:
            return self._life_resumed

    @resumed.setter
    def resumed(self, value):
        self._set_life_in_lock("resumed", value)

    @property
    def paused(self):
        """
            已经执行完暂停
        :return:
        """
        with self._life_lock:
            return self._life_paused

    @paused.setter
    def paused(self, value):
        self._set_life_in_lock("paused", value)


class Activity(LifeCycle):
    """
        最最基础的Activity
        只用来定义行为，不参与任何交互和UI的实现
    """

    def __init__(self, canvas: Canvas):
        super().__init__()
        self._canvas = canvas
        self.onActivity()

    def onActivity(self):
        """
            Activity的基础框架绘制
        :return:
        """
        pass

    def onCreate(self):
        """
            在创建时调用，可以在此处初始化UI
        :return:
        """
        pass

    def onPause(self):
        """
            在活动暂停时的
        :return:
        """
        pass

    def onResume(self):
        """
            在活动运行时
        :return:
        """
        pass

    def onDestroy(self):
        """
            在活动销毁时，可以回收相关的资源
        :return:
        """
        pass

    def callKeyEvent(self, event):
        """
            提供一个由外部调用的事件分发回调函数
        :param event:
        :return:
        """
        pass

    def onKeyEvent(self, event):
        """
            按键时间发生时
        :param event:
        :return:
        """
        pass

    def onData(self, bundle):
        """
            在数据进行activity之间的传输时
        :param bundle:
        :return:
        """
        pass

    def finish(self, bundle=None):
        """
            结束自身
        :param bundle: 任务结束时是否需要传输数据到上一层级的栈对象
        :return:
        """
        if self.destroyed:
            return
        finish_activity(self, bundle)

    def start(self, activity, bundle=None):
        """
            开始一个新的activity，覆盖当前的activity
            当前的activity将会被入栈
        :param activity:
        :param bundle: 是否需要传递数据到新的activity
        :return:
        """
        if self.destroyed or self.paused:
            print("警告，你在休眠或者销毁的ACT中开启了新的页面。")
        start_activity(activity, bundle)

    def getCanvas(self) -> Canvas:
        return self._canvas

    def onActExcept(self, exception):
        """
            在活动时出现异常的话我们需要进行处理！
        :param exception:
        :return:
        """
        pass

    def startBGTask(self, run):
        if self.destroyed or self.paused:
            print("警告，你在休眠或者销毁的ACT中开启了后台任务。")

        # 我们需要再套一层，用于处理异常！
        def catch_run():
            try:
                run()
            except Exception:
                self.onActExcept(traceback.format_exc())

        threading.Thread(target=catch_run).start()

    def callServer(self, name, bundle):
        """
            传递消息到指定的服务中
        :param name:
        :param bundle:
        :return:
        """
        send_msg(
            name,
            {
                "activity": self,
                "bundle": bundle,
            }
        )

    @staticmethod
    def getManifest():
        """
            获取信息清单
                                                           名称          图标
            例子: infos 信息元组，桌面显示的时候使用 tuple(("Scan Tag", images.load("2.png")))

            整体返回字典，其中index控制activity在主页面的位置
            index == -1 的时候，始终让当前activity在列表的最后面

            return {
                "index" : 0,
                "infos" : tuple(("Scan Tag", images.load("2.png"))),
            }
        :return:
        """
        return None


def get_activity_pck(index):
    pck = _ACTIVITY_STACK[index]
    canvas: Canvas = pck["canvas"]
    active: Activity = pck["act"]
    return canvas, active


def start_activity(clz, bundle=None):
    """
        压栈开启一个新的act
    :param bundle: 传入的数据
    :param clz: act类
    :return:
    """
    # 立刻解注册按键事件
    keymap.key.unbind()
    if len(_ACTIVITY_STACK) > 0:
        old_canvas, prev_act = get_activity_pck(len(_ACTIVITY_STACK) - 1)
        prev_act.onPause()
        prev_act.paused = True
    else:
        old_canvas = None
    # 创建新的视图容器，承载在基础画布上
    canvas = Canvas(window, width=240, height=240, bd=0, highlightthickness=0, bg="white")
    canvas.grid()
    # 创建新的activity并且压栈
    new_act: Activity = clz(canvas)
    new_act.onCreate()
    new_act.created = True
    # 隐藏旧的视图，如果不为空
    if old_canvas is not None:
        old_canvas.grid_remove()
    # 如果数据不为空，则传入数据进行处理
    if bundle is not None:
        new_act.onData(bundle)
    new_act.onResume()
    new_act.resumed = True
    # 缓存到全局域中
    _ACTIVITY_STACK.append({
        "canvas": canvas,
        "act": new_act
    })
    # 最后注册按键事件
    keymap.key.bind(new_act.callKeyEvent)
    return


def finish_activity(act, bundle=None):
    """
        结束一个活动，并且回传数据
    :param act:
    :param bundle:
    :return:
    """
    # 立刻解注册按键事件
    keymap.key.unbind()
    prv_act_index = -1
    for index in range(1, len(_ACTIVITY_STACK)):
        canvas, a = get_activity_pck(index)
        if a == act:
            # 活动匹配，结束此活动
            act.onDestroy()
            act.destroyed = True
            # 销毁视图
            canvas.destroy()
            prv_act_index = index - 1
            # 将自己从活动列表中移除
            _ACTIVITY_STACK.remove(_ACTIVITY_STACK[index])
            del act, canvas
            break
    # 显示上一个act并且判断是否需要向他的上一个栈活动传递数据
    if prv_act_index != -1:
        canvas, a = get_activity_pck(prv_act_index)
        # 视图恢复显示
        canvas.grid()
        if bundle is not None:
            # 数据传递
            a.onData(bundle)
        a.onResume()
        a.resumed = True
        keymap.key.bind(a.callKeyEvent)
    return

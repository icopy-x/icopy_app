import threading

from tkinter import font, Canvas

import resources
import actstack
import audio
import batteryui
import widget


class BaseActivity(actstack.Activity):
    """
        基础活动定义
    """

    def unique_id(self, tags):
        return "ID:{}-{}".format(id(self), tags)

    def __init__(self, canvas: Canvas):
        self._battery_bar = None
        self._is_title_inited = False
        self._is_button_inited = False
        self._is_busy = False

        self._lock_busy = threading.Lock()

        self.tags_title = self.unique_id("title")
        self.tags_btn_bg = self.unique_id("btnBg")
        self.tags_btn_left = self.unique_id("btnLeft")
        self.tags_btn_right = self.unique_id("btnRight")

        # 最终调用顶层的Activity初始化函数进行初始化
        super().__init__(canvas)

    def onActivity(self):
        """
            基础框架绘制
        :return:
        """
        # 先创建基础布局
        # 1、标题栏是永远存在的，因此必须绘制标题栏的底色优先
        if not self._is_title_inited:
            self._is_title_inited = True
            self._canvas.create_rectangle(0, 0, 240, 40, fill="#7C829A", width=0, outline="")
            self._canvas.create_text((0, 0), text="", font=resources.get_font(18), fill="white", tags=self.tags_title)
        # 2、关于电池电量，电池电量也是恒久存在的，伴随着中控程序的整个生命周期
        self._battery_bar = widget.BatteryBar(self.getCanvas(), (208, 15), 22, 12, 100)
        # 提交注册电池电量条对象
        batteryui.register(self._battery_bar)

    def onPause(self):
        """
            在活动暂停时的
        :return:
        """
        if self._battery_bar is not None:
            self._battery_bar.hide()

    def onResume(self):
        """
            在活动运行时
        :return:
        """
        if self._battery_bar is not None:
            self._battery_bar.show()

    def onDestroy(self):
        """
            在活动销毁时，可以回收相关的资源
        :return:
        """
        if self._battery_bar is not None:
            batteryui.unregister(self._battery_bar)
            self._battery_bar.destroy()
            self._battery_bar = None

    def callKeyEvent(self, event):
        """
            提供一个由外部调用的事件分发回调函数
        :param event:
        :return:
        """
        event_ret = self.onKeyEvent(event)

        if not self.resumed:  # 视图不可见时确保不要响应按钮事件
            print("事件处理完成后，此活动非可视化运行状态，不接受后续操作。")
            return

        if event_ret is None:
            pass  # 在事件不确认操作时，我们不需要做出任何操作
        elif event_ret is True:
            # 在事件确认被消费的时候，我们需要进行
            # 1、常规音频播放
            audio.playKeyEnable()
            # 2、待添加
            pass
        elif event_ret is False:
            # 在事件确认不被消费的时候，我们需要进行
            # 1、按钮禁用音播放
            audio.playKeyDisable()
            # 2、待添加
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

    def setTitle(self, title: str, xy=(120, 20), space_cat=(False, True)):
        """
            初始化一般的标题
        :param space_cat: 是否自动裁剪空格，
                            第一个参数表示裁剪左边空格，
                            第二个参数表示裁剪右边空格，
                            注意：默认只裁剪右边空格！
        :param xy: 坐标
        :param title: 标题文字
        :return:
        """
        if (space_cat is not None and len(space_cat) == 2
                and (isinstance(space_cat, list) or isinstance(space_cat, tuple))):
            if space_cat[0]:  # 裁剪左边的空格
                title = title.lstrip()
            if space_cat[1]:  # 裁剪右边的空格
                title = title.rstrip()
        # 绘制标题栏的控件
        self._canvas.itemconfig(self.tags_title, text=title)
        self._canvas.coords(self.tags_title, xy)
        return self._canvas

    def _setbusy(self, busy):
        """
            设置当前任务状态
        :return:
        """
        with self._lock_busy:
            self._is_busy = busy

    def setbusy(self):
        """
            设置当前任务繁忙状态
        :return:
        """
        self._setbusy(True)

    def setidle(self):
        """
            设置当前空闲状态
        :return:
        """
        self._setbusy(False)

    def isbusy(self):
        """
            当前是否是繁忙状态
        :return:
        """
        with self._lock_busy:
            return self._is_busy

    @staticmethod
    def _getBtnFontAndY():
        f = font.Font(font=resources.get_font(16))
        height = f.metrics("linespace")
        # print("字符高度: ", height)
        y = int(222 + height / 2)
        return f, y

    def _setupButtonBg(self):
        if not self._is_button_inited:
            # 初始化背景面板
            bg = self._canvas.create_rectangle(0, 200, 240, 240, fill="#222222", tags=self.tags_btn_bg, width=0,
                                               outline="")
            self._canvas.lower(bg)
            self._is_button_inited = True
        else:
            self._canvas.itemconfig(self.tags_btn_bg, state="normal")

    def setLeftButton(self, text, color="white"):
        self._setupButtonBg()
        w = self._canvas.find_withtag(self.tags_btn_left)
        if len(w) > 0:
            self._canvas.itemconfig(w, text=text, fill=color, state="normal")
        else:
            f, y = self._getBtnFontAndY()
            self._canvas.create_text((15, y), text=text, fill=color, font=f, tags=self.tags_btn_left,
                                     justify='left',
                                     anchor="sw")
        return self._canvas

    def setRightButton(self, text, color="white"):
        self._setupButtonBg()
        w = self._canvas.find_withtag(self.tags_btn_right)
        if len(w) > 0:
            self._canvas.itemconfig(w, text=text, fill=color, state="normal")
        else:
            f, y = self._getBtnFontAndY()
            self._canvas.create_text((225, y), text=text, fill=color, font=f, tags=self.tags_btn_right,
                                     justify='right',
                                     anchor="se")
        return self._canvas

    def dismissButton(self, left=True, right=True):
        """
            隐藏按钮
        :param left: 隐藏左按钮
        :param right: 隐藏右按钮
        :return:
        """
        if left:
            # 删除左边的按钮的文字
            self._canvas.itemconfig(self.tags_btn_left, state="hidden")
        else:
            self._canvas.itemconfig(self.tags_btn_left, state="normal")

        if right:
            # 删除右边的按钮的文字
            self._canvas.itemconfig(self.tags_btn_right, state="hidden")
        else:
            self._canvas.itemconfig(self.tags_btn_right, state="normal")

        if left and right:
            # 删除按钮的背景色
            self._canvas.itemconfig(self.tags_btn_bg, state="hidden")
        else:
            self._canvas.itemconfig(self.tags_btn_bg, state="normal")

        return self._canvas

    def disableButton(self, left=True, right=True, color="grey", color_normal="white"):
        if left:
            # 删除左边的按钮的文字
            self._canvas.itemconfig(self.tags_btn_left, fill=color)
        else:
            self._canvas.itemconfig(self.tags_btn_left, fill=color_normal)
        if right:
            # 删除右边的按钮的文字
            self._canvas.itemconfig(self.tags_btn_right, fill=color)
        else:
            self._canvas.itemconfig(self.tags_btn_right, fill=color_normal)
        return self._canvas

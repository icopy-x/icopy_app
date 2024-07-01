"""
    维护一系列的控件
"""
from tkinter import font

import images
import threading
import time

import resources


def createTag(obj, tag):
    return str(id(obj)) + ":" + tag


class ListView:
    """
        列表视图，需要提供的
        1、有源数据（必须）
        2、图标（可选）
    """

    def __init__(self, parent, xy, items=None, text_size=13):
        self._parent = parent
        # 列表的xy坐标
        self._listview_xy_on_parent = xy
        self._listview_item_width = 240
        self._listview_item_height = 40
        self._listview_item_text_size = text_size
        # 被绘制的项目
        self._listview_items = items
        # 显示的项目上线个数
        self._listview_max_display_item = 5
        # 绘制的项目开始位置
        self._listview_start_item = 0
        # 绘制的项目的结束位置
        self._listview_end_item = self._listview_max_display_item + self._listview_start_item
        # 当前选中的项目
        self._listview_selection = 0
        # 自增的行计数
        self._listview_row_position = 0
        # 当前在第几页
        self._listview_current_page = 0
        # 分页处理
        self._listview_pages_list = []
        # 页面切换的回调
        self._listview_on_page_change_call = None
        # 选项切换的回调
        self._listview_on_selection_change_call = None
        # 整页切换使能
        self._listview_page_mode = False
        # 选择的背景是否初始化
        self._listview_is_select_bg_inited = False
        # 选择的背景绘制对象
        self._listview_select_bg = None
        # 当前绘制过程的索引数
        self._listview_draw_index = 0
        # 最后绘制的y轴
        self._listview_draw_lasty = self._listview_xy_on_parent[1]
        # 文本距离小图标的距离！
        self.listview_str_margin_left = 50

        # 缓存字符串绘制的控件的组
        self._listview_item_group = []

        self.isShowingLabel = True
        self.tags_text = createTag(self, "text")
        self.tags_icon = createTag(self, "icon")
        self.tags_bg = createTag(self, "bg")

        self.setItems(items)

    def getPageCount(self):
        """
            获得页面的分页总数
        :return: 分页总数
        """
        return len(self._listview_pages_list)

    def getPagePosition(self):
        """
            获取当前的页面位置
        :return:
        """
        return self._listview_current_page

    def getSelection(self, in_ui=False):
        """
            获得当前选中的项的位置，在当前页的列表中或者在总列表中
        :return:
        """
        # print("getSelection: ", self._listview_selection)
        if in_ui:
            return self.getItemIndexInPage(self._listview_selection, self.getPagePosition())
        return self._listview_selection

    def setItemWidth(self, width):
        """
            设置每个项目占用的宽度
        :param width: 占用ListView容器的宽度
        :return:
        """
        self._listview_item_width = width
        return self

    def setItemHeight(self, height):
        """
            设置每个项目占用的高度
        :param height: 占用ListView容器的高度
        :return:
        """
        self._listview_item_height = height
        return self

    def _item_clear_reset(self):
        for w in self._listview_item_group:
            if isinstance(w, tuple):
                # 是元组，说明是图标文本复合体
                icon_w = w[0]
                text_w = w[1]
                # 进行隐藏
                self._parent.delete(icon_w)
                self._parent.delete(text_w)
            else:
                # 直接就是文本控件对象
                self._parent.delete(w)
        self._listview_draw_lasty = self._listview_xy_on_parent[1]
        self._listview_draw_index = 0
        self._listview_current_page = 0
        self._listview_selection = 0
        self._listview_item_group.clear()

    def _item_to_page_(self, item_size):
        """
            项目分页，根据指定的项目数进行分页
        :param item_size:
        :return:
        """
        # 初始化分页信息
        count = int(item_size / self._listview_max_display_item)
        if item_size % self._listview_max_display_item > 0:
            count = count + 1
            end_count = item_size % self._listview_max_display_item
        else:
            end_count = self._listview_max_display_item
        self._listview_pages_list.clear()
        self._listview_pages_list = list(range(count))
        for p in range(count):
            # 分割页
            start = p * self._listview_max_display_item
            if count == p + 1:
                # 最后一页
                end = start + end_count
            else:
                # 普通页
                end = (p + 1) * self._listview_max_display_item
            pd = {"start": start, "end": end}
            self._listview_pages_list[p] = pd

    def setItems(self, items, autoShow=True):
        """
            设置被绘制的项目数组
        :param autoShow:  是否自动显示并且更新视图
        :param items: 可以是纯文本(str)数组，
                        也可以是（图标 , 文本）（元组），
                        也可以是可执行的函数（绘制view的实现）
        :return:
        """
        if items is None:
            return self
        self._listview_items = items
        # 重新设置项目后，就认为需要重新绘制
        self._item_clear_reset()
        # 我们还需要进行分配每个页面
        self._item_to_page_(len(self._listview_items))
        self._updateViews()
        if autoShow:
            self.show()
        else:
            # 默认回调一次
            if self._listview_on_page_change_call is not None:
                self._listview_on_page_change_call(len(self._listview_pages_list), self._listview_current_page)
        return self

    def _getStartByPage(self, page):
        return self._listview_pages_list[page]["start"]

    def _getEndByPage(self, page):
        return self._listview_pages_list[page]["end"]

    def _getStartAndEndByPage(self, page):
        return self._getStartByPage(page), self._getEndByPage(page)

    def getItemCountOnPage(self, page):
        """
            获取当前页的子项目数
        :param page:
        :return:
        """
        start, end = self._getStartAndEndByPage(page)
        return end - start

    def isItemPositionInPage(self, pos, page):
        """
            某个选项坐标是否在某一页
        :return:
        """
        start, end = self._getStartAndEndByPage(page)
        # print(list(range(start, end)))
        return pos in list(range(start, end))

    def getItemIndexInPage(self, item_index, page):
        """
            根据当前的项目索引，获取其在某一页的正确位置
            比如，总共有两页，每页5个项目时，第9个item_index是第二页的第五个，
            也就是第04个。
        :param page:
        :param item_index:
        :return:
        """
        start, end = self._getStartAndEndByPage(page)
        # print(list(range(start, end)))
        return list(range(start, end)).index(item_index)

    def getPagePositionFromItem(self, item_pos):
        for page in range(len(self._listview_pages_list)):
            if self.isItemPositionInPage(item_pos, page):
                return page

    def setDisplayItemMax(self, maxItem):
        """
            设置可以显示的项目的上限
        :param maxItem: 一页显示的项目的上限
        :return:
        """
        self._listview_max_display_item = maxItem
        self._listview_end_item = self._listview_max_display_item + self._listview_start_item
        return self.setItems(self._listview_items)

    def _call_page_listener(self):
        if self._listview_on_page_change_call is not None and self.isShowing():
            self._listview_on_page_change_call(len(self._listview_pages_list), self._listview_current_page)

    def setOnPageChangeCall(self, call):
        """
            设置页面改变的回调
        :param call: 一个回调函数，例子：call(page_max, current_page)
        :return:
        """
        self._listview_on_page_change_call = call
        # 在显示的情况下默认回调一次
        self._call_page_listener()
        return self

    def setOnSelectionChangeCall(self, call):
        """
            设置选项改变的回调
        :param call: 一个回调函数，例子：call(page, selection)
        :return:
        """
        self._listview_on_selection_change_call = call

    def drawStr(self, title, base_y, str_x, str_y, state="hidden"):
        self._listview_row_position = self._listview_row_position + 1
        # 绘制文字
        canvas = self._parent
        # 字体
        w = canvas.create_text(
            str_x,
            str_y,
            text=title,
            font=resources.get_font(self._listview_item_text_size),
            tags=self.tags_text,
            justify="left",
            anchor="w",
            state=state
        )
        # 缓存当前的字符串控件到组中
        self._listview_item_group.append(w)
        return base_y + self._listview_item_height

    def drawMulti(self, item, base_y, str_x, state="hidden"):
        canvas = self._parent
        # 绘制图标
        w = canvas.create_image(str_x + 35, self._get_str_center_y(base_y), image=item[1][0], disabledimage=item[1][1],
                                tags=self.tags_icon, anchor="e", state=state)
        # 绘制文本
        y = self.drawStr(item[0], base_y, str_x + self.listview_str_margin_left, self._get_str_center_y(base_y))
        # 取出文本对象
        last_draw_w_index = len(self._listview_item_group) - 1
        text_w = self._listview_item_group[last_draw_w_index]
        # 合并为元组缓存到组中
        self._listview_item_group[last_draw_w_index] = (w, text_w)
        # print("需要绘制字符图像复合体")
        return y

    def _get_str_center_y(self, base_y):
        # 计算居中的Y
        return base_y + (self._listview_item_height / 2)

    def _hidden_all_group(self):
        for w in self._listview_item_group:
            if isinstance(w, tuple):
                # 是元组，说明是图标文本复合体
                icon_w = w[0]
                text_w = w[1]
                # 进行隐藏
                self._parent.itemconfig(icon_w, state="hidden")
                self._parent.itemconfig(text_w, state="hidden")
            else:
                # 直接就是文本控件对象
                self._parent.itemconfig(w, state="hidden")

    def _show_for_position(self, start, end):
        for w in self._listview_item_group[start:end]:
            if isinstance(w, tuple):
                # 是元组，说明是图标文本复合体
                icon_w = w[0]
                text_w = w[1]
                # 进行显示
                self._parent.itemconfig(icon_w, state="normal")
                self._parent.itemconfig(text_w, state="normal")
            else:
                # 直接就是文本控件对象
                self._parent.itemconfig(w, state="normal")

    def _show_current_page(self, show=True):
        """
            显示当前页面
        :param show:
        :return:
        """
        if show:
            start, end = self._getStartAndEndByPage(self.getPagePosition())
            self._show_for_position(start, end)
            self._call_page_listener()
        else:
            self._hidden_all_group()

    def addItem(self, item, state="hidden", update_lasty=True):
        """
            添加和绘制一个项目
        :param update_lasty:  是否更新最后的Y坐标
        :param state: 控件状态，为normal时显示控件，为hidden时隐藏控件
        :param item: 要添加绘制的项目
        :return:
        """
        if self._listview_items is None:
            self._listview_items = list()
        if item not in self._listview_items:  # 避免出现单独添加项目的时候，项目列表缺失此单独绘制的项目的问题
            self._listview_items.append(item)
        self._item_to_page_(len(self._listview_items))
        # 根据指定的xy进行定位绘制
        x = self._listview_xy_on_parent[0]
        y = self._listview_draw_lasty
        # print("绘制: ", item, "绘制的坐标: x=", x, "y=", y)
        # 超过缓存组的数目，进行绘制
        if isinstance(item, str):
            # print("需要绘制单字符串")
            # 只需要绘制str
            y = self.drawStr(item, y, x + 19, self._get_str_center_y(y), state)
            self._listview_draw_index = self._listview_draw_index + 1
        elif isinstance(item, tuple):
            y = self.drawMulti(item, y, x, state)
            self._listview_draw_index = self._listview_draw_index + 1
        else:
            print("出现了不支持绘制的数据：", item)
            return
        if self._listview_draw_index == self._listview_max_display_item:
            # 判断到超过上限显示的项目数，我们需要将Y重新归位
            if update_lasty:
                y = self._listview_xy_on_parent[1]
                # print("y坐标被重置")
            self._listview_draw_index = 0
        if update_lasty:
            # 我们需要缓存y坐标，下次绘制用得上
            self._listview_draw_lasty = y

    def _draw_all_items(self):
        """
            预先绘制所有的项目，并且保存
        :return:
        """
        if len(self._listview_item_group) == 0:
            # 取出坐标，进行计算绘制
            for page_pos in range(len(self._listview_pages_list)):
                start, end = self._getStartAndEndByPage(page_pos)
                for item in self._listview_items[start:end]:
                    self.addItem(item)
        return

    def _updateViews(self, select=True, select_pos=0):
        """
            更新视图，绘制视图在父布局上
        :return:
        """

        if self._listview_items is None or len(self._listview_items) == 0:
            print("没有发现有效项目")
            return self

        # 绘制列表的行归零
        self._listview_row_position = 0

        # 尝试绘制所有的项目
        self._draw_all_items()

        # 然后隐藏所有绘制的控件
        self._hidden_all_group()

        # 取出并且绘制UI
        start, end = self._getStartAndEndByPage(self._listview_current_page)
        self._show_for_position(start, end)

        # 高亮选中项目
        if select:
            self.selection(select_pos)

        return self

    def setTitleColor(self, widget, color):
        if self._parent is None or widget is None: return
        # 重新配置绘制时的参数
        self._parent.itemconfig(widget, fill=color)

    def setImageColor(self, widget, active):
        if self._parent is None or widget is None: return
        # 重新配置图像的颜色
        # if False:
        #     state = "disabled"
        # else:
        #     state = "normal"
        state = "normal"
        self._parent.itemconfig(widget, state=state)

    def setUI(self, p, textColor, imgActive):
        item = self._listview_item_group[p]
        if isinstance(item, tuple):
            text_w = item[1]
            self.setTitleColor(text_w, textColor)
            icon_w = item[0]
            self.setImageColor(icon_w, imgActive)
        else:
            self.setTitleColor(item, textColor)

    def setupSelectBG(self, x, y, position):
        """
            初始化选择的背景
        :return:
        """
        if self._listview_is_select_bg_inited: return
        self._listview_is_select_bg_inited = True
        canvas = self._parent
        if self._listview_select_bg is None:
            self._listview_select_bg = canvas.create_rectangle(x, y + position * self._listview_item_height,
                                                               x + self._listview_item_width,
                                                               y + position * self._listview_item_height + self._listview_item_height,
                                                               fill="#EEEEEE", width=0, tags=self.tags_bg)

    def selection(self, position=0):
        """
            设置选择的项目（将被反色高亮）
        :param position:
        :return:
        """
        if not self.isShowing() or self._listview_page_mode:
            return

        # 自动切换到项目所属的页
        current_page = self.getPagePositionFromItem(position)

        if self._listview_current_page != current_page:
            self.goto_page(current_page)
            self.selection(position)
            return

        x = self._listview_xy_on_parent[0]
        y = self._listview_xy_on_parent[1]

        page_position = self.getItemIndexInPage(position, current_page)

        # 先尝试初始化选择的背景
        self.setupSelectBG(x, y, page_position)

        # 移动矩形
        self._parent.coords(self._listview_select_bg, x, y + page_position * self._listview_item_height,
                            x + self._listview_item_width,
                            y + page_position * self._listview_item_height + self._listview_item_height)

        # 降低海拔
        self._parent.lower(self._listview_select_bg)

        # 记录现在的选中项
        self._listview_selection = position

        return self

    def goto_page(self, page, select=False, select_pos=0):
        """
            前往某一页
        :param select_pos:
        :param select:
        :param page:
        :return:
        """
        self._listview_current_page = page
        self._updateViews(select, select_pos)

        if self._listview_on_page_change_call is not None: self._listview_on_page_change_call(
            len(self._listview_pages_list),
            self._listview_current_page)

        if select and self._listview_on_selection_change_call is not None:
            self._listview_on_selection_change_call(self._listview_current_page, self.getSelection())

    def goto_first_page(self):
        """
            前往第一页
        :return:
        """
        self.goto_page(0)

    def goto_last_page(self):
        """
            前往最后一页
        :return:
        """
        self.goto_page(len(self._listview_pages_list) - 1)

    def isShowing(self):
        return self.isShowingLabel

    def _setState(self, state):
        canvas = self._parent
        if len(self._listview_pages_list) <= self._listview_current_page: return
        start, end = self._getStartAndEndByPage(self._listview_current_page)
        for w in self._listview_item_group[start:end]:
            if isinstance(w, tuple):
                # 是元组，说明是图标文本复合体
                icon_w = w[0]
                text_w = w[1]
                # 进行隐藏
                self._parent.itemconfig(icon_w, state=state)
                self._parent.itemconfig(text_w, state=state)
            else:
                # 直接就是文本控件对象
                self._parent.itemconfig(w, state=state)

        # 尝试隐藏高亮背景
        bg_w = canvas.find_withtag(self.tags_bg)
        for bw in bg_w:
            canvas.itemconfig(bw, state=state)

    def show(self):
        """
            显示列表
        :return:
        """
        if self.isShowing():
            return
        self._setState("normal")
        self.isShowingLabel = True
        # 回调一下当前的进度
        # 在显示的情况下默认回调一次
        if self._listview_on_page_change_call is not None:
            self._listview_on_page_change_call(len(self._listview_pages_list), self._listview_current_page)

    def hide(self):
        """
            隐藏列表
        :return:
        """
        if not self.isShowing():
            return
        self._setState("hidden")
        self.isShowingLabel = False

    def prev(self, loop=False, prevPage=False):
        """
            向上滚动
        :param prevPage: 是否是直接翻到前一页
        :param loop: 到达顶部后是否滚动
        :return:
        """
        if not self.isShowing():
            return
        if prevPage or self._listview_page_mode:
            prev_page = self._listview_current_page - 1
            if prev_page < 0:
                prev_page = len(self._listview_pages_list) - 1
            start = self._getStartByPage(prev_page)
            self.goto_page(prev_page, True, start)
            return
        prevItemPos = self._listview_selection - 1
        # 已经在当前页的最顶部了
        if prevItemPos == -1:  # 已经到了页头
            prev_page = self._listview_current_page - 1
            if prev_page < 0:  # 已经到尽头，判断是否可以循环，如果可以则回到最后一页
                if loop:
                    prev_page = len(self._listview_pages_list) - 1
                else:
                    return self
            # 无论如何，回到上一页都要选择上一页的最后一项
            start, end = self._getStartAndEndByPage(prev_page)
            self.goto_page(prev_page, True, end - 1)
        else:
            # 直接进行选择
            self.selection(prevItemPos)
            self._listview_selection = prevItemPos
            # 回调切换事件
            if self._listview_on_selection_change_call is not None:
                self._listview_on_selection_change_call(self._listview_current_page, self.getSelection())
        return self

    def next(self, loop=False, nextPage=False):
        """
            向下滚动，到达底部后是否滚动
        :param nextPage:
        :param loop:
        :return:
        """
        if not self.isShowing():
            return

        if nextPage or self._listview_page_mode:
            next_page = self._listview_current_page + 1
            if len(self._listview_pages_list) - 1 < next_page:
                next_page = 0
            start = self._getStartByPage(next_page)
            self.goto_page(next_page, True, start)
            return

        next_item_pos = self._listview_selection + 1
        start, end = self._getStartAndEndByPage(self._listview_current_page)
        # 已经在最底部了，不能再移动了，判断是否有下一页
        if next_item_pos >= end:
            next_page = self._listview_current_page + 1
            if len(self._listview_pages_list) - 1 < next_page:  # 已经到尽头，可以循环，回到第一页的头部
                if loop:
                    next_page = 0
                    next_item_pos = 0
                else:
                    return self
            self.goto_page(next_page, True, next_item_pos)
        else:
            # 直接进行选择
            self.selection(next_item_pos)
            self._listview_selection = next_item_pos
            # 回调切换事件
            if self._listview_on_selection_change_call is not None:
                self._listview_on_selection_change_call(self._listview_current_page, self.getSelection())
        return self

    def setPageModeEnable(self, enable):
        """
            设置整页切换使能，整页切换模式下，ListView的项目高亮不可用，
            进行项目选择移动时，进行整页切换
        :param enable:
        :return:
        """
        self._listview_page_mode = enable
        # 取消高亮，暂时不需要
        # self.setUI(self._selection, "black", False)
        if enable:
            self._parent.itemconfig(self._listview_select_bg, state="hidden")
        else:
            self._parent.itemconfig(self._listview_select_bg, state="normal")


class PageIndicator:
    """
        页面指示器
    """

    def __init__(self, base_parent, top_tag):
        """
            初始化一个页面指示器对象
        :param base_parent: 基础画布，所有的内容都将在此处绘制
        :param top_tag: 顶部指示器的锚点位置的相对画布对象的标签
        """

        self.maxValue = 0
        self.currentValue = 0
        # 页面循环使能
        self.lE = False
        # 底部使能
        self.bE = False
        # 顶部指示器是否已经初始化
        self.top_inited = False
        # 底部指示器是否已经初始化
        self.bottom_inited = False
        # 默认的底部指示器xy
        self.bottom_pi_xy = (120, 220)

        self.base_parent = base_parent
        self.top_tag = top_tag
        # 初始化视图标签
        self.tags_top = createTag(self, "top")
        self.tags_bottom_up = createTag(self, "bottom_up")
        self.tags_bottom_down = createTag(self, "bottom_down")
        self.tags_bottom_multi = createTag(self, "bottom_multi")
        # 默认只显示顶部的文本指示器
        self.setTopIndicatorEnable(True)
        self.label_showing = True

    def setupBottomIndicator(self):
        """
            初始化一下底部的图标指示器
        :return: 
        """
        if self.bottom_inited: return
        self.bottom_inited = True
        # 绘制底部的所有的指示器
        # 并且初始化状态为隐藏状
        # 先加载资源
        img_up = images.loadTk("up.png")
        img_down = images.loadTk("down.png")
        img_multi = images.loadTk("up_down.png")

        canvas = self.base_parent
        # 然后绘制图标
        canvas.create_image(self.bottom_pi_xy, image=img_up, state="hidden", tags=self.tags_bottom_up)
        canvas.create_image(self.bottom_pi_xy, image=img_down, state="hidden", tags=self.tags_bottom_down)
        canvas.create_image(self.bottom_pi_xy, image=img_multi, state="hidden", tags=self.tags_bottom_multi)

    def setBottomIndicatorEnable(self, enable):
        """
            负责启用/禁用底部的图标指示器，并且绘制
        :param enable:
        :return:
        """
        if self.maxValue == 1: return
        self.bE = enable
        self.setupBottomIndicator()
        if enable:
            # 可用，根据当前的进度开启对应的
            self._reDrawBottomIndicator()
        else:
            # 不可用，隐藏所有的
            self.base_parent.itemconfig(self.tags_bottom_up, state="hidden")
            self.base_parent.itemconfig(self.tags_bottom_down, state="hidden")
            self.base_parent.itemconfig(self.tags_bottom_multi, state="hidden")
        return self

    def _reDrawBottomIndicator(self):
        if not self.bE: return
        # 绘制底部的图标
        # 绘制有几种情况
        # 1、在可以循环时，无论在第几页，都显示上下键
        # 2、在不可以循环时（假设有三页）：
        #   a. 第一页时，显示向下图标
        #   b. 第二页时，显示向上和向下图标
        #   c. 第三页是，也就是最后一页时，显示向上图标
        self.base_parent.itemconfig(self.tags_bottom_up, state="hidden")
        self.base_parent.itemconfig(self.tags_bottom_down, state="hidden")
        self.base_parent.itemconfig(self.tags_bottom_multi, state="hidden")
        if self.lE:
            self.base_parent.itemconfig(self.tags_bottom_multi, state="normal")
        else:
            if self.currentValue == 0:
                self.base_parent.itemconfig(self.tags_bottom_down, state="normal")
            elif self.currentValue == self.maxValue - 1:
                self.base_parent.itemconfig(self.tags_bottom_up, state="normal")
            else:
                self.base_parent.itemconfig(self.tags_bottom_multi, state="normal")
        return

    def _get_relative_xy(self):
        # 先获取顶部的标题栏的控件，计算坐标
        widget_title = self.base_parent.find_withtag(self.top_tag)
        if len(widget_title) > 0:
            widget_title = widget_title[0]
        else:
            widget_title = None
        if widget_title is None:
            xy = (170, 18)
        else:
            xy = list(self.base_parent.bbox(widget_title))
            xy[0] = xy[2] + 6  # 偏移6个像素再绘制指示器
            xy = xy[0:2]
        return xy

    def _setupTopIndicator(self):
        if self.top_inited: return
        self.top_inited = True
        # 获取相对于标题栏的xy
        xy = self._get_relative_xy()
        self.base_parent.create_text(xy, text="", font=resources.get_font(11), fill="white", tags=self.tags_top, anchor="nw"
                                     , justify="left")

    def setTopIndicatorEnable(self, enable):
        """
            负责启用/禁用顶部的文字指示器，并且绘制
        :param enable:
        :return:
        """
        # 先尝试初始化顶部的指示器
        self._setupTopIndicator()
        if enable:
            # 进行文本更改和移动
            self.base_parent.itemconfig(self.tags_top, text="", state="normal")
            # 开始绘制
            xy = self._get_relative_xy()
            # 进行画布对象移动
            self.base_parent.coords(self.tags_top, xy[0], xy[1])
        else:
            self.base_parent.itemconfig(self.tags_top, state="hidden")
        return self

    def _reDrawTopIndicator(self):
        self.setTopIndicatorEnable(False)
        self.setTopIndicatorEnable(True)

    def setTopIndicatorValue(self, value):
        self.setTopIndicatorEnable(True)
        self.currentValue = value
        self.base_parent.itemconfig(self.tags_top, text="{}/{}".format(value, self.maxValue))
        return self

    def setTopIndicatorMax(self, value):
        self.setTopIndicatorEnable(True)
        self.maxValue = value
        self.base_parent.itemconfig(self.tags_top, text="{}/{}".format(self.currentValue, value))
        return self

    def update(self, page_max, current_page):
        # 如果只有一页，则不进行显示底部的标志
        if page_max == 1:
            self.setBottomIndicatorEnable(False)
        elif self.bE:
            self._reDrawBottomIndicator()

        self._reDrawTopIndicator()
        self.setTopIndicatorMax(page_max)
        self.setTopIndicatorValue(current_page + 1)

    def setLoop(self, enable):
        """
            设置是否支持翻页，如果支持翻页，那么在下限与上限的时候都显示上下翻页的图标
        :param enable:
        :return:
        """
        self.lE = enable
        return self

    def _setStatus(self, enable):
        if enable:
            status = "normal"
        else:
            status = "hidden"
        self.base_parent.itemconfig(self.tags_top, state=status)
        xy = self._get_relative_xy()
        self.base_parent.coords(self.tags_top, xy[0], xy[1])
        if self.bE: self._reDrawBottomIndicator()

    def show(self):
        """
            显示所有存在的视图
        :return:
        """
        self._setStatus(True)
        self.label_showing = True

    def hide(self):
        """
            隐藏所有存在的视图
        :return:
        """
        self._setStatus(False)
        self.label_showing = False

    def showing(self):
        """
            当前是否在显示
        :return:
        """
        return self.label_showing


class ProgressBar:
    """
        进度条
    """

    def __init__(self, canvas, xy, width=200, height=20, max_v=100):
        self.needupdate = 1
        self.aimwidth = 0
        self.currentwidth = 0
        self.lastdraw = 0
        self.step = 1
        self.selfupdate_enable = 0

        if self.selfupdate_enable == 1:
            self.selfupdate = 1
        else:
            self.selfupdate = 0

        self.progress = 0
        self.running = False
        self.lock = threading.RLock()

        self.width = width
        self.height = height
        self.max = max_v
        self.value = width / max_v
        self.canvas = canvas
        self.xy = xy
        # 绘制底色
        x = xy[0]
        y = xy[1]

        self.tags_bg = createTag(self, "bg")
        self.tags_pb = createTag(self, "pb")

        self.canvas.create_rectangle(x, y, x + width, y + height, fill="#eeeeee", outline="", width=0,
                                     tags=self.tags_bg)
        self.canvas.create_rectangle(x, y, x, y + height, fill="#1C6AEB", width=0, outline="",
                                     tags=self.tags_pb)

        # threading.Thread(target=self._intdraw).start()

    def _intdraw(self):
        # 循环绘制进度条，该部分运行于子线程
        with self.lock:
            self.running = True
            self.currentwidth = 0
        w = self.canvas.find_withtag(self.tags_pb)
        x = self.xy[0]
        y = self.xy[1]
        while True:
            if self.needupdate == 1:
                # print("db" + str(self.aimwidth) + "," + str(self.currentwidth))
                if self.aimwidth == self.currentwidth:
                    # 进度条达到目标值
                    self.needupdate = 0
                    if self.selfupdate_enable == 1:
                        self.selfupdate = 1  # 开启自动增长
                    else:
                        self.selfupdate = 0  # 关闭自动增长
                    # 关闭刷新
                    if self.lastdraw == 1:
                        # 最后一次绘制，结束后就退出
                        # print("最后一次绘制，退出")
                        with self.lock:
                            self.lastdraw = 0
                            self.running = False
                        return
                    # 如果不是最后一次绘制则意味着本周期不应绘制，跳过
                    time.sleep(0.005)
                    continue
                if self.aimwidth > self.currentwidth:
                    if self.aimwidth - self.currentwidth < self.step:
                        self.currentwidth += self.aimwidth - self.currentwidth
                    else:
                        self.currentwidth += self.step
                elif self.aimwidth < self.currentwidth:
                    if self.aimwidth - self.currentwidth > - self.step:
                        self.currentwidth -= - self.aimwidth + self.currentwidth
                    else:
                        self.currentwidth -= self.step
                # 开始绘制进度条体
                if self.needupdate == 1:
                    # print("当前绘制" + str(self.currentwidth))
                    self.canvas.coords(w, x, y, x + self.currentwidth, y + self.height)
            else:
                if self.selfupdate == 1:
                    # 衡速自增
                    self.currentwidth += 0.1
                    if self.currentwidth > self.width:
                        self.currentwidth = self.width
                        self.selfupdate = 0  # 关闭自增
                    # 开始绘制进度条体
                    # print("当前自增绘制" + str(self.currentwidth))
                    self.canvas.coords(w, x, y, x + self.currentwidth, y + self.height)
                    time.sleep(0.05)
            time.sleep(0.004)

    def _draw(self, width):
        # print("设置值" + str(width))
        with self.lock:
            self.aimwidth = width
            self.needupdate = 1

    def setMax(self, maxValue):
        with self.lock:
            self.max = maxValue
            self.value = self.width / maxValue

    def getMax(self):
        return self.max

    def setMessage(self, msg):
        """
            在进度条的上方绘制文本信息
        :param msg:
        :return:
        """
        # 取出坐标
        x = self.xy[0]
        y = self.xy[1]

        # 绘制
        w = self.canvas.find_withtag(createTag(self, "msg"))
        if len(w) > 0:
            self.canvas.itemconfig(w, text=msg)
        else:
            x = x + self.width / 2
            self.canvas.create_text(x, y - 2, text=msg, width=self.width, font=resources.get_font(12), fill="#1C6AEB",
                                    tags=createTag(self, "msg"), justify="left", anchor="s")

    def _isShowing(self):
        bg = self.canvas.find_withtag(createTag(self, "bg"))
        if len(bg) > 0:
            state = self.canvas.itemcget(bg, "state")
            return state != "hidden"
        else:
            return False

    def _setState(self, state):
        self.canvas.itemconfig(createTag(self, "bg"), state=state)
        self.canvas.itemconfig(createTag(self, "pb"), state=state)
        self.canvas.itemconfig(createTag(self, "msg"), state=state)

    def show(self):
        if not self._isShowing():
            self._setState("normal")

        if self.running:
            return

        with self.lock:
            self.needupdate = 1
            self.aimwidth = 0

        # print("重启线程")
        threading.Thread(target=self._intdraw).start()

    def hide(self, wait_finish=False):
        if wait_finish and self.progress != self.max:
            self.setProgress(self.max)

        if self.progress > 0 and self.progress != self.max:
            print("Hide的时候进度条未走完！")
            self.setProgress(self.max)

        with self.lock:
            self.needupdate = 0
            self.selfupdate = 0
            self.currentwidth = 0
            self.progress = 0

        self.canvas.coords(self.tags_pb, 0, 0, 0, 0)
        self._setState("hidden")

    def setProgress(self, progress, autoShow=True):
        if progress > self.max:
            print("传入的值超过max: ", self.max)
            return
        if progress < 0:
            print("传入的值小于0")
            return
        if self.lastdraw == 1:
            print("当前在进行最后一次绘制，跳过此次进度更新的操作。")
            return

            # 判断是否需要自动显示
        if autoShow: self.show()

        with self.lock:
            self.progress = progress
            if progress == self.max:
                self.lastdraw = 1  # 设置最后一次扫描

        # 绘制最新的宽度值
        self._draw(progress * self.value)
        # 堵塞等待绘制完成
        while self.lastdraw == 1:
            time.sleep(0.2)
            # print("正在等待绘制完成!")

    def getProgress(self):
        """
            得到当前的进度值
        :return:
        """
        return self.progress

    def increment(self):
        """
            进度自增
        :return:
        """
        value = self.progress + 1
        if value > self.max:
            print("超过max的进度值: ", value)
            return
        self.setProgress(value)

    def decrement(self):
        """
            进度自减
        :return:
        """
        value = self.progress - 1
        if value == 0:
            print("进度值为零，不绘制。")
            return
        self.setProgress(value)


class Toast:
    """
        土司弹框，自动在程序的中间创建一个土司弹框
    """

    MASK_FULL = "mask_full"
    MASK_TOP_CENTER = "mask_top_center"
    MASK_CENTER = "mask_center"

    def __init__(self, canvas):
        self._canvas = canvas
        self._isShow = False
        self.tags_mask_layer = createTag(self, "mask_layer")
        self.tags_text = createTag(self, "text")
        self.tags_icon = createTag(self, "icon")
        self.tags_text_bg = createTag(self, "text_bg")
        self._lock = threading.RLock()

    def _showMask(self, enable, mode=MASK_TOP_CENTER):
        w = self._canvas.find_withtag(self.tags_mask_layer)
        if enable:
            # 初始化背景图
            xy = (0, 0)
            height = 240
            if mode == self.MASK_TOP_CENTER:
                height = 200
            if mode == self.MASK_CENTER:
                height = 160
                xy = (0, 40)
            mask_layer = images.makeTransparentImage(240, height, "#000000", 128)

            # 开始创建控件
            if len(w) > 0:
                self._canvas.itemconfig(w, state="normal", image=mask_layer)
                try:
                    self._canvas.coords(xy)
                except Exception as e:
                    print(e)
            else:
                w = self._canvas.create_image(xy, image=mask_layer, tags=self.tags_mask_layer, anchor="nw")
        else:
            self._canvas.itemconfig(self.tags_mask_layer, state="hidden")
        return w

    def show(self, text, icon=None, mask=True, mode=MASK_TOP_CENTER):
        """
            显示视图
        :return:
        """
        # 先尝试取消显示
        self.cancel(mask_layer=False)
        m = self._showMask(mask, mode)
        # 绘制文本
        if icon is not None:
            x = 132
        else:
            x = 120
        t = self._canvas.create_text(x, 120, text=text, font=resources.get_font(16), width=200, fill="white",
                                     # n, ne, e, se, s, sw, w, nw, or center
                                     tags=self.tags_text, justify="center", anchor="center")
        # 获得矩形区域的坐标
        xy = self._canvas.bbox(t)
        xy = list(xy)
        # 对xy坐标进行增加和减少，用于绘制边框
        xy[0] = xy[0] - 10
        # 如果没有图标，则不需要添加额外的边框宽度
        if icon is not None:
            xy[0] = xy[0] - 38
        xy[1] = xy[1] - 10
        xy[2] = xy[2] + 10
        xy[3] = xy[3] + 10
        # 然后画一个矩形，用于承载文本信息
        mask_bg = images.makeTransparentImage(xy[2] - xy[0], xy[3] - xy[1], "#25262D", 118)
        i = self._canvas.create_image(120, 120, image=mask_bg, tags=self.tags_text_bg)
        # 提高海拔
        self._canvas.lift(m)
        self._canvas.lift(i)
        self._canvas.lift(t)
        # 获得文字所在的坐标
        xy = self._canvas.bbox(i)
        # 绘制小图标，如果有
        if icon is not None:
            w = self._canvas.create_image(xy[0] + 18, 120, image=icon, tags=self.tags_icon)
            self._canvas.lift(w)

        with self._lock:
            self._isShow = True

    def cancel(self, icon=True, text=True, textbg=True, mask_layer=True):
        """
            取消创建，销毁视图
        :return:
        """
        try:
            if text:
                self._canvas.delete(self.tags_text)
            if icon:
                self._canvas.delete(self.tags_text_bg)
            if textbg:
                self._canvas.delete(self.tags_icon)
            if mask_layer:
                self._canvas.itemconfig(self.tags_mask_layer, state="hidden")
        except Exception as e:
            print("Exception on widget.Toast.cancel(): ", e)
        with self._lock:
            self._isShow = False

    def isShow(self):
        return self._isShow


class BatteryBar:
    """
        电池电量进度条
    """

    def __init__(self, canvas, xy, width, height, value):
        """
            初始化一个电池电量的进度标志
        :param xy: 放置的xy坐标
        :param width: 绘制外框占用的像素宽
        :param height: 绘制外框占用的像素高
        :param value: 初始化内框电池电量余量的值，百分比
        """
        self.tags_external = createTag(self, "external")
        self.tags_contact = createTag(self, "contact")
        self.tags_internal = createTag(self, "internal")

        self.canvas = canvas
        self.xy = xy
        self.width = width
        self.height = height
        self.value = value
        self.charging = False
        self.charging_run_state = False
        self.is_showing = True
        self.is_destroy = False

        self.external_inited = False
        self._draw_init_label = False

        self.lock = threading.Lock()
        self.event = threading.Event()

        # 预先绘制外框
        self._draw_init()

    def _draw_init(self):
        if self._draw_init_label:
            return
        self._draw_init_label = True
        # 先绘制大的外宽
        x1 = self.xy[0]
        y1 = self.xy[1]
        x2 = x1 + self.width
        y2 = y1 + self.height
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="white", width=2, tags=self.tags_external)
        # 然后绘制小小的电池正极触点
        s_height = self.height * 0.3
        x1 = x2
        y1 = y1 + (self.height - s_height) / 2
        x2 = x2 + self.height * 0.2
        y2 = y1 + s_height
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="white", fill="white", tags=self.tags_contact)
        # 最后绘制一个内部的电量图标
        self.canvas.create_rectangle((0, 0, 0, 0), outline="", fill="white", width=0, tags=self.tags_internal)

    def _draw_internal(self, value):
        # 获取全部可以绘制的宽度
        width = (value / 100) * (self.width - 4)

        try:
            xy_external = self.canvas.coords(self.tags_external)
            xy_external = list(xy_external)

            # x1
            xy_external[0] = xy_external[0] + 2
            # x2
            xy_external[2] = xy_external[0] + width
            # y1
            xy_external[1] = xy_external[1] + 2
            # y2
            xy_external[3] = xy_external[3] - 2

            self.canvas.coords(self.tags_internal,
                               xy_external[0], xy_external[1],
                               xy_external[2], xy_external[3])
            if self.charging:
                self.canvas.itemconfig(self.tags_internal, fill="#00FF00")
            else:
                if self.value <= 8:
                    self.canvas.itemconfig(self.tags_internal, fill="red")
                else:
                    self.canvas.itemconfig(self.tags_internal, fill="white")
        except:
            if self.charging:
                self.charging = False
            return -1

        return 1

    def setBattery(self, value):
        """
            设置电池电量的百分比
        :param value:
        :return:
        """
        if value > 100:
            value = 100
        if value < 0:
            value = 0
        with self.lock: self.value = value
        if not self.charging:  # 充电的时候不需要绘制
            self._draw_internal(value)

    def _charging_run(self):
        self.charging_run_state = True
        print("进入充电状态")
        while self.charging:
            if not self.is_showing:
                if self.is_destroy:
                    break
                print("隐藏状态，不更新")
                self.event.wait()
                self.event.clear()
                continue

            min_v = self.value
            max_v = 100
            if min_v >= max_v:
                if self._draw_internal(max_v) == -1:
                    print("出现异常，退出绘制")
                    break
            else:
                need_break = False
                for v in range(min_v, max_v):
                    if not self.charging:
                        need_break = True
                        break

                    if not self.is_showing:
                        if self.is_destroy:
                            need_break = True
                            break
                        print("隐藏状态，不更新")
                        self.event.wait()
                        self.event.clear()

                    if self._draw_internal(v) == -1:
                        need_break = True
                        break

                    # print("自动更新电池电量值: ", v)
                    time.sleep(50 * 0.05 / (100 - min_v))
                if need_break:
                    print("出现异常，退出绘制")
                    break
            time.sleep(0.1)
        self.charging_run_state = False
        print("退出充电状态")

    def setCharging(self, enable):
        if enable:
            if self.charging:
                # print("已经在充电，不必多次开启")
                return
            # 开启一个子线程，进行UI更新，提示充电中
            self.charging = True
            threading.Thread(target=self._charging_run).start()
        else:
            self.charging = False
            # if self.charging_run_state:  # 判断子线程是否在运行
            #     while self.charging_run_state: time.sleep(0.1)
            try:
                self.canvas.itemconfig(self.tags_internal, fill="white")
            except:
                pass

    def _set_state(self, state):
        self.canvas.itemconfig(self.tags_external, state=state)
        self.canvas.itemconfig(self.tags_contact, state=state)
        self.canvas.itemconfig(self.tags_internal, state=state)

    def show(self):
        self._set_state("normal")
        self.is_showing = True
        self.event.set()

    def hide(self):
        self._set_state("hidden")
        self.is_showing = False

    def destroy(self):
        self.canvas.delete(self.tags_external)
        self.canvas.delete(self.tags_contact)
        self.canvas.delete(self.tags_internal)
        self.charging = False
        self.is_destroy = True

    def isShowing(self):
        """
            当前的电量条是否在显示
        :return:
        """
        return self.is_showing

    def isDestroy(self):
        """
            当前的电量条是否已经销毁
        :return:
        """
        return self.is_destroy


class InputMethods:
    """
        输入法
    """

    # 模式可用字符
    _mode_1_str = "0123456789"
    _mode_2_str = "0123456789ABCDEF"

    def __init__(self, canvas, xy, h, infont=None, defdata="", bakcolor="#ffffff", datacolor="#000000",
                 highlightcolor="#cccccc",
                 mode=2, usefill=False, highlight_feature=True):
        # 区域左上角座标 xy
        # 底色区域高度 h
        # 字体数据 font
        # 默认数据 defdata,默认为空,传入宽度决定了目标值宽度
        # 底色 bakcolor
        # 字符颜色 datacolor
        # 高亮颜色 highlightcolor
        # 输入类型 mode 1为数字 2为hex
        # 底层画板
        self._canvas = canvas
        # 座标
        self._item_xy = xy
        # 尺寸
        self._item_width = 0
        self._item_height = h
        # 字体
        if infont is None:
            infont = font.Font(font=resources.get_font(12))
        self._item_font = infont
        # 区域底色
        self._item_bakcolor = bakcolor
        # 字符颜色
        self._item_datacolor = datacolor
        # 字符选中后高亮背景颜色
        self._item_highlightcolor = highlightcolor
        # 数据寄存器
        self._datas = [""]
        # 边缘留白宽度
        self._leave_margin_blank = 6
        self._leave_margin_blank_h = 2  # 这个参数只用来生成底色反色区域
        # 当前是否显示出来
        self._isshown = 1
        # 当前选中的字
        self._input_method_selection = 0
        # 当前是否启用选中
        self._hasfocus = 0
        # 该输入框是否支持高亮
        self._highlight_feature = highlight_feature

        # 输入法类型(的字符列表)
        if mode == 1:
            self._input_mode_str = self._mode_1_str
        elif mode == 2:
            self._input_mode_str = self._mode_2_str
        if usefill: self._input_mode_str += "-"

        self.tags_hl = createTag(self, "input_mask_hl")
        self.tags_text = createTag(self, "input_text")
        self.tags_bg = createTag(self, "input_mask_bak")

        # 文本尺寸
        self._word_h = self._item_font.metrics("linespace")
        self._word_w = self._item_font.measure("0")

        # 高亮背景色
        if self._highlight_feature:
            self.mask_hl = images.makeTransparentImage(self._word_w,  # 宽度加上两个白边
                                                       self._item_height - 2 * self._leave_margin_blank_h,  # 高度减去两个白边
                                                       self._item_highlightcolor, 255)
            self.mask_nohl = images.makeTransparentImage(self._word_w,  # 一个字符宽度
                                                         h - 2 * self._leave_margin_blank_h,  # 高度减去两个白边
                                                         self._item_bakcolor, 255)
        self._intdraw_bg()
        self._intdraw_word()
        self.setdata(defdata)
        self.resetselection()

    # 查询当前输入法框占用了多少宽度,方便得到某些座标
    def getitemwidth(self):
        return self._item_width

    # 查询当前输入法框占用了多少高度,方便得到某些座标
    def getitemheight(self):
        return self._item_height

    # 查找当前高亮位的数据的下一个字符，作为返回值
    def _findnextword(self):
        currentword = self._datas[self._input_method_selection]
        currentint = self._input_mode_str.find(currentword)
        # print("当前高亮位字符为：", currentword, "位置为：", currentint)
        nextint = currentint + 1
        if nextint > (len(self._input_mode_str) - 1):
            nextint = 0
        nextword = self._input_mode_str[nextint]
        # print("下一个字符为：", nextword, "位置为：", nextint)
        return nextword

    # 查找当前高亮位的数据的上一个字符，作为返回值
    def _findlastword(self):
        currentword = self._datas[self._input_method_selection]
        currentint = self._input_mode_str.find(currentword)
        # print("当前高亮位字符为：", currentword, "位置为：", currentint)
        nextint = currentint - 1
        if nextint < 0:
            nextint = (len(self._input_mode_str) - 1)
        nextword = self._input_mode_str[nextint]
        # print("上一个字符为：", nextword, "位置为：", nextint)
        return nextword

    # 当前高亮项目向上切换一位
    def upword(self):
        self._datas[self._input_method_selection] = self._findnextword()
        self._intdraw_flush()

    # 当前高亮项目向下切换一位
    def downword(self):
        self._datas[self._input_method_selection] = self._findlastword()
        self._intdraw_flush()

    # 高亮下一个项目
    def nextitem(self):
        self._input_method_selection += 1
        if self._input_method_selection > len(self._datas) - 1:
            self._input_method_selection = 0
        self._intdraw_flush()

    # 高亮上一个项目
    def lastitem(self):
        self._input_method_selection -= 1
        if self._input_method_selection < 0:
            self._input_method_selection = len(self._datas) - 1
        self._intdraw_flush()

    # 读取所有数据
    def getdata(self):
        datatemp = ""
        for i in range(len(self._datas)):
            datatemp += self._datas[i]
        return datatemp

    # 设置字符的长度和内容
    # 1.如果只传入数据，则数据将设置为目标区域，长度将设置为传入数据长度，
    # 2.如果传入数据和长度，则数据将会设置到目标区域
    # 同时需要传入对齐方式，按照对齐方式放置数据。
    # 此时字符长度取决于传入的数据和长度中较大的那个
    # 3.如果只传入长度，那么目标区域将会设置为全“-”号，长度按照参数。
    def setdata(self, defdata="", length=0, alignment="right"):
        if length == 0:  # 长度为空
            if defdata == "":
                self._datas = ["-"]
            else:
                self._datas.clear()
                for word in defdata:
                    self._datas.append(word)
        else:  # 长度不为空
            if defdata == "":  # 数据为空，按照长度来设置数据
                self._datas.clear()
                for i in range(length):
                    self._datas.append("-")
            else:  # 数据不为空，按照数据和长度来设置数据
                if len(defdata) > length:  # 传入数据大于长度，数据错误，不操作
                    print("输入法设置数据长度大于设置长度！")
                else:
                    if alignment == "right":  # 右对齐模式
                        self._datas.clear()
                        # 先添加足够的空位
                        for i in range(length - len(defdata)):
                            self._datas.append("0")
                        # 添加数据
                        for word in defdata:
                            self._datas.append(word)
                    elif alignment == "left":  # 左对齐模式
                        self._datas.clear()
                        # 先添加数据
                        for word in defdata:
                            self._datas.append(word)
                        # 添加足够的空位
                        for i in range(length - len(defdata)):
                            self._datas.append("0")
        self._intdraw_flush()

    # 设置反选位置到第一个字符
    def resetselection(self):
        self._input_method_selection = 0
        self._intdraw_flush()

    # 循环隐藏显示
    def rollshowhide(self):
        if self._isshown == 1:
            self._isshown = 0
        else:
            self._isshown = 1
        self._setstate()

    # 设置显示
    def show(self):
        if self._isshown == 1:
            return
        self._isshown = 1
        self._setstate()

    # 设置不显示
    def hide(self):
        if self._isshown == 0:
            return
        self._isshown = 0
        self._setstate()

    # 查询是否显示，返回显示状态（1显示0隐藏）
    def isshowing(self):
        return self._isshown

    # 循环焦点
    def rollfocus(self):
        if self._hasfocus == 1:
            self._hasfocus = 0
        else:
            self._hasfocus = 1
        self._intdraw_flush()

    # 设置焦点，开始反显
    def setfocus(self):
        self._hasfocus = 1
        self._intdraw_flush()

    # 关闭焦点，不再反显
    def unsetfocus(self):
        self._hasfocus = 0
        self._intdraw_flush()
        print("unsetfocus 取消焦点成功")

    # 查询是否拥有焦点
    def isfocuing(self):
        return self._hasfocus

    # 设置状态，隐藏和显示
    def _setstate(self):
        if self._isshown == 1:
            state = "normal"
            # print("显示")
        elif self._isshown == 0:
            state = "hidden"
            # print("隐藏")
        else:
            state = "normal"
        # 尝试隐藏文本
        textw = self._canvas.find_withtag(self.tags_text)
        for tw in textw:
            self._canvas.itemconfig(tw, state=state)
            # print("操作文本", tw)
        # 尝试隐藏背景
        imgw = self._canvas.find_withtag(self.tags_bg)
        for iw in imgw:
            self._canvas.itemconfig(iw, state=state)
            # print("操作背景", iw)
        # 尝试隐藏高亮背景
        if self._hasfocus == 1:
            if self._highlight_feature:
                bgw = self._canvas.find_withtag(self.tags_hl)
                for bw in bgw:
                    self._canvas.itemconfig(bw, state=state)
                    print("操作高亮", bw, "state: ", state)

    # 背景绘制（为了保证顺序，首先绘制一个高亮区域，但是完全透明）
    def _intdraw_bg(self):
        all_word_w = self._item_font.measure(str(self.getdata()))
        # 画一个背景区域
        self._item_width = self._leave_margin_blank * 2 + all_word_w  # 宽度加上两个白边
        mask_bak = images.makeTransparentImage(self._item_width,
                                               self._item_height,  # 高度
                                               self._item_bakcolor, 255)
        self._canvas.create_image(self._item_xy,
                                  image=mask_bak,
                                  anchor="nw",
                                  tags=self.tags_bg)

        # 画一个透明的高亮区域
        if self._highlight_feature:
            mask_hl_temp = images.makeTransparentImage(self._word_w,
                                                       self._word_h,
                                                       self._item_bakcolor, 0)
            self._canvas.create_image(0, 0,
                                     image=mask_hl_temp,
                                     anchor="w",
                                     tags=self.tags_hl)

    # 字符绘制
    def _intdraw_word(self):
        # 绘制文本
        # 文本x位置为考虑了边缘留白之后的位置
        textx = int(self._item_xy[0] + self._leave_margin_blank)
        # 文本y位置为中心位置（w点对齐）
        texty = int((self._item_xy[1] * 2 + self._item_height) / 2)  # - 2
        # print("texty", texty)
        # print("_word_h", self._word_h)
        # 创建文本
        self._canvas.create_text(textx, texty,
                                 text=self.getdata(),
                                 font=self._item_font,
                                 fill=self._item_datacolor,
                                 tags=self.tags_text,
                                 anchor="w")

    # 动态绘制 包括反显和选择变化，焦点变化，装饰符号等
    def _intdraw_flush(self):
        hl = None
        if self._highlight_feature:
            hl = self._canvas.find_withtag(self.tags_hl)
        bg = self._canvas.find_withtag(self.tags_bg)
        txt = self._canvas.find_withtag(self.tags_text)

        if self._hasfocus == 1:  # 按照是否选中控制是否显示高亮区域
            if self._isshown == 1:  # 不显示的时候也不可以高亮
                # 高亮区域x位置为考虑了边缘留白之后的位置
                if self._highlight_feature:
                    self._canvas.itemconfig(hl, state="normal")  # 显示高亮图像
                hlx = int(self._item_xy[0] + self._leave_margin_blank)
                hlx += self._input_method_selection * self._word_w
                # 高亮区域y位置为中心位置（w点对齐）
                hly = int((self._item_xy[1] * 2 + self._item_height) / 2)  # - 2
                # 按照高亮位控制显示高亮块
                if self._highlight_feature:
                    self._canvas.itemconfig(hl, image=self.mask_hl)  # 显示高亮图像
                    self._canvas.coords(hl, hlx, hly)  # 高亮图像按照选择位置刷新
        else:  # 没有选中
            if self._highlight_feature:
                self._canvas.itemconfig(hl, state="hidden")  # 隐藏高亮图像
        # 刷新文字
        all_word_w = self._item_font.measure(str(self.getdata()))
        mask_bak = images.makeTransparentImage(self._leave_margin_blank * 2 + all_word_w,  # 宽度加上两个白边
                                               self._item_height,  # 高度减去两个白边
                                               self._item_bakcolor, 255)
        self._canvas.itemconfig(bg, image=mask_bak)
        self._canvas.itemconfig(txt, text=self.getdata())


class CheckedListView(ListView):
    """
        可以被选择的列表
        需要的传入item为[文本]
    """

    def __init__(self, parent, xy, items=None, text_size=13):
        self._check_pos = -1
        self.have_draw = False
        self.tags_chk1 = createTag(self, "checkbox")
        self.tags_chk2 = createTag(self, "checkbox2")
        super().__init__(parent, xy, items, text_size)

    def _updateViews(self, select=True, select_pos=0):
        # 调用父类的方法完成文本的绘制
        super()._updateViews(select, select_pos)
        # 取出坐标，进行计算绘制
        y = self._listview_xy_on_parent[1]
        # 迭代项目，绘制图标
        canvas = self._parent
        # 删除所有的矩形边框
        canvas.delete(self.tags_chk1)

        page_pos = self.getPagePosition()
        for index in range(self.getItemCountOnPage(page_pos)):
            # 绘制带灰色边框的透明矩形   x           y
            canvas.create_rectangle(200, y + 20 - 10,
                                    # x1          y1
                                    220, y + 20 + 10,
                                    outline="grey",
                                    width=2, tags=self.tags_chk1)
            y = y + self._listview_item_height

        self.check(self.getCheckPosition())
        self.auto_show_chk()

    def auto_show_chk(self):
        """
            自动显示和隐藏选择高亮
        :return:
        """
        page_pos = self.getPagePosition()
        chk_pos = self.getCheckPosition()
        # 判断当前选中的项目是否在当前页，是的话才选中
        if self.isItemPositionInPage(chk_pos, page_pos):
            self._parent.itemconfig(self.tags_chk2, state="normal")
            # print("选中项在当前页")
        else:
            self._parent.itemconfig(self.tags_chk2, state="hidden")
            # print("选中项不在当前页")

    def check(self, position):
        """
            选中某个项目，高亮其
        :param position:
        :return:
        """

        if position == -1:
            # print("选中的位置不合法，自动跳过操作。")
            return

        # print("当前需要选中的项: ", position)
        page_position = self.getPagePosition()
        equal_selection = self.isItemPositionInPage(position, page_position)

        if not equal_selection:
            # print("不在同一页")
            # 缓存check的位置
            self._check_pos = position
            return

        if position == self._check_pos and equal_selection and self.have_draw:
            # 已经选中过，为了避免浪费资源，不允许重复选中
            # print("已经选中过了")
            self.auto_show_chk()
            return

        # 取出项目所在页的正确位置
        position_4_page = self.getItemIndexInPage(position, page_position)

        canvas = self._parent
        bgW = canvas.find_withtag(self.tags_chk1)
        # print("UI项目数:", len(bgW))
        # 高亮新选中的边框
        if len(bgW) > position_4_page:
            # 取消高亮所有的边框
            for bg in bgW: canvas.itemconfig(bg, outline="grey")
            # 取出该位置的对应背景控件
            bgW = bgW[position_4_page]
            # 进行边框高亮
            canvas.itemconfig(bgW, outline="#1C6AEB")
            # 删除可能存在的矩形内饰
            canvas.delete(self.tags_chk2)
            # 进行内饰绘制的坐标计算
            xy = canvas.coords(bgW)
            # 外边框的XY +- 填充的宽度 = 内部的矩形的xy坐标
            xy[0] = xy[0] + 5
            xy[1] = xy[1] + 5
            xy[2] = xy[2] - 5
            xy[3] = xy[3] - 5
            # 绘制内饰
            canvas.create_rectangle(xy, tags=self.tags_chk2, fill="#1C6AEB", outline="", width=0)
            # 缓存check的位置
            self._check_pos = position
            # 标记当前的绘制状态
            self.have_draw = True
        return

    def getCheckPosition(self):
        """
            获取当前的选中的位置
        :return:
        """
        return self._check_pos


class BigTextListView(ListView):
    """
        超长文本列表，超长文本分页列表
    """

    def __init__(self, parent, xy, items=None, text_size=13):
        # 不能调用带有items的父类对象，以取消首次初始化的绘制
        # 以达到只初始化变量的效果
        super().__init__(parent, xy)
        self.setItemHeight(160)
        self.setItemWidth(240)
        self.setDisplayItemMax(1)
        # 初始化完成后，再手动调用item的初始化与绘制
        self.text_size = text_size
        self.setPageModeEnable(True)
        self.setItems(items)

    def drawStr(self, title, base_y, str_x, str_y, state="hidden"):
        self._listview_row_position = self._listview_row_position + 1
        # 绘制文字
        canvas = self._parent
        # 字体
        w = canvas.create_text(str_x, str_y, text=title, font=resources.get_font(self.text_size), tags=self.tags_text,
                               justify="left", width=230, anchor="w", state=state)
        # 缓存当前的字符串控件到组中
        self._listview_item_group.append(w)
        return base_y + self._listview_item_height

    def selection(self, position=0):
        if not self.isShowing():
            return
        # 记录现在的选中项
        self._listview_selection = position


class InputMethodList(ListView):
    """
        输入法列表封装
    """

    def __init__(self, parent, xy):
        super().__init__(parent, xy)
        self.input_method_height = 40
        self.setDisplayItemMax(4)
        self._input_method_count_max = 255
        self.setItemHeight(self.input_method_height)
        self.input_method_list = dict()
        self.create_new_mode = False
        self.tags_new_method_btn = createTag(self, "new_method_btn")

    def set_input_method_height(self, height):
        """
            设置输入法的高度
        :param height:
        :return:
        """
        self.input_method_height = height

    def set_input_method_max(self, max_count):
        """
            设置输入法创建的上限个数
        :param max_count:
        :return:
        """
        self._input_method_count_max = max_count

    def add_method(self, title, focus=False):
        """
            添加一个输入法
        :return:
        """
        if focus and len(self.input_method_list) > 0:
            last_method = self.input_method_list[len(self.input_method_list) - 1]
            last_method.unsetfocus()
        method = self._draw_input_method(title)
        if focus: method.setfocus()
        self._setup_method_new()
        self._focus_new_item(False)
        self.create_new_mode = False
        # 自动翻到最后一页
        self.goto_last_page()
        start, end = self._getStartAndEndByPage(self.getPagePosition())
        # 自动选中最后一项
        self.selection(end - start - 1)
        # print("当前选中项: ", self.getSelection())
        return

    def update_focus(self):
        """
            更新焦点
        :return:
        """
        self.focus_exit()

        pos = self.getSelection()
        if pos in self.input_method_list:
            self.input_method_list[pos].setfocus()

    def has_focus(self):
        """
            是否有输入法有焦点
        :return:
        """
        for method in self.input_method_list.values():
            if method.isfocuing():
                return True
        return False

    def focus_exit(self):
        """
            退出焦点获取
        :return:
        """
        method = self._get_focus_method()

        if method is not None:
            method.unsetfocus()

    def add_method_if_new(self, title):
        """
            创建一个新的输入法项目，如果当前的光标在创新项目上
        :return:
        """
        if self.create_new_mode and len(self.input_method_list) <= self._input_method_count_max:
            self.add_method(title)
            return True
        return False

    def get_input_method_count(self):
        """
            返回输入法的个数
        :return:
        """
        return len(self.input_method_list)

    def selection(self, position=0):
        super(InputMethodList, self).selection(position)
        self._show_current_page()

    def next(self, loop=False, nextPage=False):
        if self.has_focus():
            self.down()
            print("发现焦点，将进行下操作")
            return

        if not nextPage:
            self._act_item_and_selection("next")

        if not self.create_new_mode:
            # print("当前不是创新项模式，直接响应事件！")
            super(InputMethodList, self).next(loop, nextPage)

    def prev(self, loop=False, prevPage=False):
        if self.has_focus():
            self.up()
            return

        if not self.create_new_mode:
            # print("当前不是创新项模式，直接响应事件！")
            super(InputMethodList, self).prev(loop, prevPage)

        self._act_item_and_selection("prev")

    def down(self):
        if self.create_new_mode: return
        method = self._get_focus_method()
        if method is not None and method.isfocuing():
            method.downword()

    def up(self):
        if self.create_new_mode: return
        method = self._get_focus_method()
        if method is not None and method.isfocuing():
            method.upword()

    def right(self):
        if self.create_new_mode:
            return
        method = self._get_focus_method()
        if method is not None and method.isfocuing():
            method.nextitem()
            return
        if self.getPageCount() > 1:
            self.next(True, True)

    def left(self):
        if self.create_new_mode:
            return
        method = self._get_focus_method()
        if method is not None and method.isfocuing():
            method.lastitem()
            return
        if self.getPageCount() > 1:
            self.prev(True, True)

    def get_all_input_text(self):
        """
            获取所有的输入组的文本输入
        :return:
        """
        text_list = list()
        for im in self.input_method_list.values():
            text_list.append(im.getdata())
        return text_list

    def _draw_input_method(self, title):
        """
            绘制输入法
        :return:
        """
        self.addItem(title, state="normal", update_lasty=False)
        # 创建一个输入法
        method = InputMethods(self._parent, (88, self._listview_draw_lasty), self.input_method_height,
                              defdata="FFFFFFFFFFFF")
        self.input_method_list[len(self._listview_items) - 1] = method
        # print("下一次绘制索引: ", self.draw_index)
        if self._listview_draw_index == 0:
            self._listview_draw_lasty = self._listview_xy_on_parent[1]
            # print("_draw_input_method -> Y坐标被重置")
        else:
            self._listview_draw_lasty = self._listview_draw_lasty + self.input_method_height

        self._updateViews()

        return method

    def _setup_method_new(self):
        """
            设置输入法的创建按钮
        :return:
        """
        canvas = self._parent
        x = 120
        y = self._listview_draw_lasty + self.input_method_height / 2
        w = canvas.find_withtag(self.tags_new_method_btn)
        if len(w) > 0:
            canvas.coords(w, x, y)
        else:
            img_focus = images.loadTk("new_blue.png")
            img_unfocus = images.loadTk("new_grey.png")
            canvas.create_image(x, y, image=img_focus, tags=self.tags_new_method_btn, activeimage=img_focus,
                                disabledimage=img_unfocus, state="disabled")

        if self._listview_draw_index == 0:
            self._set_focus_state(False)
            # print("页面已满，自动隐藏添加按钮")
        else:
            self._set_focus_state(True)

    def _set_focus_state(self, enable):
        """
            设置创新按钮的视图是否启用
        :param enable:
        :return:
        """

        if enable:
            state = "disabled"
        else:
            state = "hidden"

        self._parent.itemconfig(self.tags_new_method_btn, state=state)

    def _show_for_position(self, start, end):
        super(InputMethodList, self)._show_for_position(start, end)
        for i in range(start, end):
            if i in self.input_method_list:
                self.input_method_list[i].show()

    def _hidden_all_group(self):
        super(InputMethodList, self)._hidden_all_group()
        for w in self.input_method_list.values():
            w.hide()

    def _get_focus_method(self):
        for method in self.input_method_list.values():
            if method.isfocuing():
                return method

    def _show_current_page(self, show=True):
        """
            重写显示当前页的函数，在显示当前页时判断当前页的项目数
        :param show:
        :return:
        """
        super(InputMethodList, self)._show_current_page(show)
        start, end = self._getStartAndEndByPage(self.getPagePosition())
        item_size = end - start
        if item_size == self._listview_max_display_item:
            self._set_focus_state(False)
        else:
            self._set_focus_state(True)

    def _focus_new_item(self, focus):
        """
            为创新项提供焦点
        :return:
        """
        canvas = self._parent
        if focus:
            state = "normal"
            canvas.itemconfig(self._listview_select_bg, state="hidden")
        else:
            state = "disabled"
            canvas.itemconfig(self._listview_select_bg, state="normal")

        if canvas.itemcget(self.tags_new_method_btn, "state") != "hidden":
            canvas.itemconfig(self.tags_new_method_btn, state=state)

    def _goto_create_mode(self, action):
        # 判断下一项是否是创新项
        if self.create_new_mode:
            print("当前已经是创新项模式")
            return False
        selection = self.getSelection()
        if selection == len(self._listview_items) - 1 and (action == "next" or action == "prev"):
            self.create_new_mode = True
            # 光标移动到创新项上
            self._focus_new_item(True)
            self.create_new_mode = True
            return True
        else:
            self._focus_new_item(False)
            self.create_new_mode = False
            return False

    def _act_item_and_selection(self, act):
        if self._goto_create_mode(act):
            # print("进入创新项成功")
            # 如果当前是创新项状态，但是刚好不翻页，那我们就要翻页并且显示创新项按钮
            if len(self._listview_items) % self._listview_max_display_item == 0:
                self._hidden_all_group()
                self._set_focus_state(True)
                self._focus_new_item(True)
            else:
                self._show_current_page()
                self._focus_new_item(True)
            return

        if self.create_new_mode:
            self.create_new_mode = False
            self._focus_new_item(False)
            self._show_current_page()

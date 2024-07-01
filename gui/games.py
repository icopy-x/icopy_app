"""
    这是一个存放游戏的地方
"""
import random
import threading
import time

import resources
import widget


class Game:
    """
        游戏基础定义
    """

    def unique_id(self, tags):
        return str(tags) + ":" + str(id(self))

    def start(self):
        """
            开始游戏
        :return:
        """
        pass

    def pause(self):
        """
            暂停游戏
        :return:
        """
        pass

    def stop(self):
        """
            停止游戏
        :return:
        """
        pass


class GreedySnake(Game):
    """
        贪吃蛇实现
        1、蛇头是导向点，控制方向移动
        2、蛇身是追随蛇头的，每次移动都是蛇节继承上一节的位置，然后释放蛇尾
    """
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"

    def __init__(self, canvas, block_size=10, default_len=3, default_xy=(28, 129), default_border=(4, 40, 240, 240),
                 default_direction=UP):
        # 画布
        self.canvas = canvas
        # 绘制的方块大小
        self.block_size = block_size
        # 边界
        self.border = default_border
        self.len = default_len
        self.xy = default_xy
        self.block_size = block_size
        self.default_direction = default_direction

        # 初始的蛇身数列
        self.snake_body = []

        self.tags_snake_body = self.unique_id("snake_body")
        self.tags_snake_food = self.unique_id("snake_food")
        # 默认方向是上
        self._direction = default_direction
        # 事件驱动
        self.event = threading.Event()
        # 控制运行
        self.run = False
        # 控制暂停
        self.pausing = False
        # 是否有食物存在
        self.has_food = False
        # 食物的坐标
        self.food_xy = ()

        # 存放所有的蛇头可能走过的坐标
        self.block_route = []
        self.init_route_map()

        # 提示框
        self.toast = widget.Toast(self.canvas)
        self.show_pre_toast()

    def init_route_map(self):
        """
            初始化路径映射
            在不超出边界的限制下，生成每个蛇头可以经过的轨迹
        :return:
        """
        # 先取出边界
        x1 = self.border[0]

        x2 = self.border[2]
        y2 = self.border[3]

        isXHead = True

        # 然后在边界内生成坐标集
        while x1 < x2:
            if isXHead:
                x1 += 1
                isXHead = False
            else:
                x1 += self.block_size + 1

            y1 = self.border[1]
            isYHead = True

            while y1 < y2:
                if isYHead:  # 头部需要先绘制一根定长的分割线
                    y1 += 1
                    isYHead = False
                else:
                    y1 += self.block_size + 1

                if x1 + self.block_size + 1 < x2 and y1 + self.block_size + 1 < y2:  # 进行缓存
                    # print("测试坐标系: ", (x1, y1))
                    self.block_route.append((x1 + 1, y1))
                else:  # 已经越界，我们直接结束接下来的操作
                    break

    def create_body(self, x, y):
        """
            给定的xy绘制方块
        :return:
        """
        self.canvas.create_rectangle(x, y, x + self.block_size, y + self.block_size,
                                     fill="#1C6AEB", outline="", tags=self.tags_snake_body)

    def food(self):
        """
            生成一个食物，在没办法生成的时候，游戏结束
            玩家获胜
        :return:
        """
        if self.has_food: return

        # 在一定坐标范围内生成食物
        empty_xys = list(set(self.block_route).difference(set(self.snake_body)))
        if len(empty_xys) <= 1:
            self.run = False
            self.event.set()
            self.toast.show(resources.get_str("you_win"))
            return

        self.has_food = True

        # print("两个数列的差集: ", empty_xys)

        # 随机一个坐标
        index = random.randint(0, len(empty_xys))
        # print("随机到的索引: ", index)
        self.food_xy = empty_xys[index]
        # 绘制食物
        self.canvas.create_rectangle(self.food_xy[0], self.food_xy[1], self.food_xy[0] + self.block_size,
                                     self.food_xy[1] + self.block_size,
                                     fill="green", outline="", tags=self.tags_snake_food)
        # print("随机到的坐标: ", self.food_xy)

    def eat(self):
        """
            吃到一个道具，头部增长一格
        :return:
        """
        if self.snake_body[0] == self.food_xy:
            self.moving(eat=True)
            self.canvas.delete(self.tags_snake_food)
            self.has_food = False

    def die(self, force_die=False):
        """
            检测死亡
        :return:
        """
        header_xy = self.snake_body[0]

        x1_out = header_xy[0] < self.border[0]
        y1_out = header_xy[1] < self.border[1]

        x2_out = header_xy[0] + self.block_size > self.border[2]
        y2_out = header_xy[1] + self.block_size > self.border[3]

        # 边界检测
        if x1_out or y1_out or x2_out or y2_out or force_die:
            self.run = False
            self.event.set()
            self.canvas.delete(self.tags_snake_food)
            self.toast.show(resources.get_str("game_over"))

    def moving(self, eat=False):
        """
            根据当前的方向进行移动
        :return:
        """
        # 删除旧的，重新绘制
        self.canvas.delete(self.tags_snake_body)

        # 拿到蛇头的位置
        header_xy = self.snake_body[0]

        # 1、先移动蛇头
        if self._direction == self.UP:
            header_new = (header_xy[0], header_xy[1] - self.block_size - 1)
        elif self._direction == self.DOWN:
            header_new = (header_xy[0], header_xy[1] + self.block_size + 1)
        elif self._direction == self.LEFT:
            header_new = (header_xy[0] - self.block_size - 1, header_xy[1])
        elif self._direction == self.RIGHT:
            header_new = (header_xy[0] + self.block_size + 1, header_xy[1])
        else:
            raise Exception("不被处理的移动方向：" + self._direction)

        # 啃食自己检测
        if header_new in self.snake_body:
            self.die(force_die=True)
            return

        self.snake_body.insert(0, header_new)

        # print("蛇头的位置: ", header_new)

        if not eat:  # 如果没有迟到，则删除一格尾部
            # 2、删除蛇尾的一格
            self.snake_body.pop()

        # 3、绘制蛇身
        for body in self.snake_body: self.create_body(body[0], body[1])

        # 死亡检测
        self.die()

    def direction(self, d):
        """
            设置方向
        :return:
        """
        self._direction = d
        self.event.set()

    def draw_thread(self):
        """
            绘制线程
        :return:
        """
        self.snake_body.clear()

        x = self.xy[0]
        y = self.xy[1]
        for count in range(self.len):
            y += self.block_size + 1
            self.snake_body.append((x, y))

        # 先绘制初始化的蛇身
        for body in self.snake_body:
            x = body[0]
            y = body[1]
            self.create_body(x, y)

        while self.run:
            # 根据移动的方向，进行蛇头移动,然后蛇身追随
            if self.pausing:
                time.sleep(0.1)
                continue
            self.food()
            self.moving()
            self.eat()
            self.event.wait(0.6)
            self.event.clear()

        return

    def show_pre_toast(self):
        self.toast.show(resources.get_str("game_tips"), mode=widget.Toast.MASK_FULL)

    def start(self):
        """
            开始贪吃蛇游戏的基础画面
        :return:
        """
        self.toast.cancel()
        if self.pausing:
            self.pausing = False
        else:
            if self.run:
                self.pause()
            else:
                self.run = True
                self.has_food = False
                self._direction = self.default_direction
                threading.Thread(target=self.draw_thread).start()
        return

    def pause(self):
        """
            暂停游戏，停止事件响应与页面绘制
            在暂停状态下，游戏只响应start操作
        :return:
        """
        self.pausing = True
        self.toast.show(resources.get_str("pausing"))

    def ispause(self):
        """
            当前是否在暂停状态
        :return:
        """
        return self.pausing

    def stop(self):
        """
            停止贪吃蛇游戏，并且清空页面
        :return:
        """
        self.run = False
        self.canvas.delete(self.tags_snake_body)
        self.canvas.delete(self.tags_snake_food)
        self.show_pre_toast()

    def isrun(self):
        """
            当前是否是运行状态
        :return:
        """
        return self.run

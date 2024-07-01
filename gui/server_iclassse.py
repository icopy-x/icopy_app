"""
    这个服务用于检测ICLASSSE读头的连接
    并且自动打开窗口
"""
import threading
import time

from serpool import Server

import hficlass
import actstack
import activity_main


class IClassSeServer(Server):
    """
        处理SE读头插入的事件
    """

    def __init__(self):
        # 默认不允许SE读头启动
        self.can_attack = False

    @staticmethod
    def getName():
        return "IClassSeAttack"

    def run_attack_listener(self):
        """
            SE读头的插入监听
        :return:
        """
        while True:
            time.sleep(4)
            if self.can_attack:  # 多一层外部逻辑，确保安全
                dev = hficlass.search_se_dev_reader()
                if dev is not None:
                    if self.can_attack:  # 只有可以监听的时候，才进行监听
                        # 发现了SE读头，我们需要启动SE读头专用的Activity页面
                        # 启动完成后，所有的逻辑都将交由该页面处理
                        print("开始启动SE外设页面")
                        actstack.start_activity(activity_main.IClassSEActivity)
                        print("启动SE外设页面完成")

        # 这一行有点东西好一些，不然总觉得怪怪的

    def onStart(self):
        """
            在此处，我们可以启动一个线程进行监听
            如果SE读头插入，我们可以进行专属SE读头的读取页面启动
        :return:
        """
        threading.Thread(target=self.run_attack_listener).start()

    def onData(self, bundle):
        """
            处理传过来的消息
            我们现在既定的逻辑是，
            传过来一个bool值表示是否启用SE读头监听
        :param bundle:
        :return:
        """
        # print("信息组合: ", bundle)
        if isinstance(bundle, dict):
            # act: actmain.MainActivity = bundle.get("activity")
            self.can_attack = bundle.get("bundle")
            print("当前是否可以进行处理: ", self.can_attack)
        return

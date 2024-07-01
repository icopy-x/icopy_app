"""
    远程功能任务
    负责执行和管理可远程操作的任务
    Remote Function Task(rftask)
"""
import os
import platform
import re
import signal
import socket
import socketserver
import subprocess
import threading
import time
import types


class RFServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True  # 我们只需要简简单单的开启地址复用就行


class RemoteTaskManager:
    """
        结构化的任务处理与管理对象
        1、可以通过此对象，开启PM3的任务执行终端，通过标准输入接口执行命令
        2、可以通过此对象，关闭PM3的任务执行终端
        3、可以通过此对象，重启PM3的任务执行终端
        4、可以通过此对象，获取PM3的任务执行结果
        5、堵塞型处理，由于设备只有一个，因此万万不可以异步执行多条指令

        注意，指令前缀为
            Nikola.D.CMD = {指令} 是控制PM3执行某个指令的（不包括大括号）
            Nikola.D.CTL = {指令} 是控制整个管理器的（不包括大括号）
            Nikola.D.PLT = {指令} 是执行所在平台的指令的转发器（不包括大括号）

        判断某个输出是否结束，请添加标志

        请记住，此任务执行器执行的可执行文件，它的输出必须是有flush的，
        否则无法被管理器读取到有效的输出
    """

    DEFAULT_END_WITH = r"Nikola\.D:.*?\d+\s+"
    DEFAULT_OFFLINE = "Nikola.D.OFFLINE"
    DEFAULT_CMD_START = "Nikola.D.CMD"
    DEFAULT_CTL_START = "Nikola.D.CTL"
    DEFAULT_PLT_START = "Nikola.D.PLT"

    def __init__(self,
                 cmd_start, cmd_stop, cwd, hp,
                 endwith=DEFAULT_END_WITH,  # 请看函数注释
                 cmdstart=DEFAULT_CMD_START,  # 请看类注释
                 ctlstart=DEFAULT_CTL_START,  # 请看类注释
                 pltstart=DEFAULT_PLT_START,  # 请看类注释
                 ):
        """
            初始化管理器
        :param endwith: 判断一次命令执行完成，输出是否结束的标志位
        :param cmd_start: 被执行的指令
        :param cwd: cmd被执行时的工作目录
        :param hp:  远端执行转发服务绑定的主机和端口: (host, port)
        """
        # 判断实例是否是这个类或者object是变量
        self.cmd_start = cmd_start
        if isinstance(cmd_start, types.FunctionType):
            self.cmd_start = cmd_start()

        self.cmd_stop = cmd_stop
        if isinstance(cmd_stop, types.FunctionType):
            self.cmd_stop = cmd_stop()

        self.cwd = cwd
        self.pi = None
        self.hp = hp

        self.endwith = endwith
        self.cmdstart = cmdstart
        self.ctlstart = ctlstart
        self.pltstart = pltstart

        self.has_read_thread = False
        self.has_manager = False
        self.has_tasking = False
        self.line_listener = None
        self.lock_tasking = threading.RLock()

        self.request_listener = None

        # 创建一个内部函数，这个函数用来桥接调用外部管理器的请求函数
        def request_task_cmd(cmd_task, listener, client: socket.socket):
            """
                请求任务
            :param client:
            :param cmd_task:
            :param listener:
            :return:
            """
            self.requestTask(cmd_task, listener)
            client.close()

        # 创建一个内部函数，这个函数用来桥接调用外部管理器的控制函数
        def request_task_ctl(cmd_task, listener, client: socket.socket):
            """
                请求任务
            :param client:
            :param cmd_task:
            :param listener:
            :return:
            """
            print("\n开始解析并且响应控制指令...")
            cmd_task = cmd_task.strip()
            if cmd_task == "restart":
                ret = self.reworkManager()
            elif cmd_task == "stop":
                self._destroy_subprocess()
                ret = True
            elif cmd_task == "start":
                self._create_subprocess()
                ret = True
            else:
                print("不支持的指令: ", cmd_task)
                ret = False
            ret = str(ret) + "\r\n"
            listener(ret)
            print("请求控制任务处理完成。")
            client.close()

        # 创建一个内部函数，这个函数用来桥接调用平台的指令
        def request_task_plt(cmd_task, listener, client: socket.socket):
            """
                请求任务
            :param client:
            :param cmd_task:
            :param listener:
            :return:
            """
            # 执行一次指令
            try:
                cmd_task = cmd_task.strip()
                # print("\n远程调试系统开始执行平台指令: ", cmd_task)
                # shell=True, 很关键
                output = subprocess.check_output(cmd_task, shell=True)
                # print("结束指令完成，输出: ", output)
            except Exception as e:
                output = str(e)
            # 获得结果并且返回
            if not isinstance(output, str):
                output = output.decode()
            listener(output + "\r\n" + self.DEFAULT_PLT_START)
            client.close()

        # 创建一个内部函数，这个函数用来解析和执行相关的指令
        def parse_cmd_map_actions(cmd_task, ):
            """
                执行指定的操作
            :param cmd_task:
            :return:
            """
            if not isinstance(cmd_task, str):
                cmd_task = cmd_task.decode().strip()

            cmd_group = cmd_task.split("=", 1)

            try:
                cmd_prev = cmd_group[0]
                cmd_act = cmd_group[1]

                if cmd_prev.startswith(self.cmdstart):
                    return request_task_cmd, cmd_act

                if cmd_prev.startswith(self.ctlstart):
                    return request_task_ctl, cmd_act

                if cmd_prev.startswith(self.pltstart):
                    return request_task_plt, cmd_act
            except Exception as e:
                print("行为解析出现异常: ", e)
            return None, None

        # 创建一个内部类，实现socket的封装服务处理接口
        class HandleServer(socketserver.StreamRequestHandler):

            def __init__(self, request, client_address, server):
                self.except_con = False
                super().__init__(request, client_address, server)

            # def socketObjPkg(self, client: socket.socket, data):
            #     """
            #         封装一下调用对象的类型转换
            #     :param data: 将要发送的数据
            #     :param client: 客户端对象
            #     :return:
            #     """
            #     client.sendall(data)

            def task(self, line):
                """
                    转发处理命令的结果的任务
                :return:
                """
                if self.except_con: return
                # print("回传行: ", line)
                # 不停的往回传接收到的数据
                try:
                    if isinstance(line, str):
                        line = line.encode()

                    self.request.sendall(line)
                    # self.socketObjPkg(self.request, line)
                except Exception as e:
                    print("链接异常: ", e)
                    self.except_con = True
                # print("回传完成！！！\n")

            def handle(self):
                # 获得客户端传输过来的命令
                data = self.rfile.readline().strip()

                # 解析当前需要执行的操作
                action, cmd_act = parse_cmd_map_actions(data)

                # 判断操作是否可用
                if action is None:
                    print("出现错误，传输过来的操作不可用，请阅读源代码，遵循命令传输的规范！！！")
                    return

                # 执行指令并且获得输出
                action(cmd_act, self.task, self.request)

                # 在请求处理结束之后，我们需要将链接结束掉
                # self.finish()

        self.ServerClass = HandleServer
        self.server = None

    def _set_has_tasking(self, has_tasking):
        """
            设置有任务在执行
        :return:
        """
        with self.lock_tasking: self.has_tasking = has_tasking

    def _run_std_output_error(self):
        """
            线程，用于读取程序的输出
        :return:
        """
        self.has_read_thread = True
        byte_buffer = bytearray()
        while self.has_read_thread:
            try:
                if self.pi is not None and not self.pi.poll():
                    line_bytes = self.pi.stdout.read(1)
                    if len(line_bytes) <= 0:
                        time.sleep(0.01)
                        # print("收到空内容")
                        continue
                    else:
                        if self.has_tasking:  # 当前有任务在执行，我们需要开始收集输出
                            byte_buffer.extend(line_bytes)
                            # 判断是否有换行b
                            has_r = byte_buffer.endswith(b'\r')
                            has_n = byte_buffer.endswith(b'\n')
                            has_rn = byte_buffer.endswith(b'\r\n')
                            if has_r or has_n or has_rn:
                                str_buffer_on_rn = byte_buffer.decode("utf-8", errors="ignore")
                                # 判断是否有结束标志，此处我们应当用最后发现的一行，而不是用整体数据，以提高效率
                                if re.search(self.endwith, str_buffer_on_rn) is not None:  # 结束标志永远在最后面
                                    self._set_has_tasking(False)
                                # 回调通知
                                if self.line_listener is not None:
                                    self.line_listener(str_buffer_on_rn)  # 回调行更细
                                # 谨记清空列表,不然下一行不会出来
                                byte_buffer.clear()
                        else:
                            byte_buffer.clear()

                else:
                    # 当前没有子进程在运行，我们为了CPU不被卡死，需要延迟循环。
                    time.sleep(0.01)

            except Exception as e:
                print("接收线程出现异常: ", e)
                time.sleep(0.01)
        print("[!] 警告：读取结束，PM3进程终止。")
        self.has_read_thread = False

    def _destroy_subprocess(self):
        """
            销毁子进程，释放资源
        :return:
        """
        self._set_has_tasking(False)
        if self.pi is not None:
            if self.cmd_stop is not None:  # 如果传入的自定义进程关闭指令不为空，则直接使用自定义的指令
                os.system(self.cmd_stop)

            try:
                os.killpg(self.pi.pid, signal.SIGUSR1)
                self.pi.terminate()
            except:
                pass
            self.pi = None

    def _destroy_read_thread(self):
        """
            停止读取线程
        """
        self.has_read_thread = False

    def _destroy_server_thread(self):
        """
            销毁服务线程
        :return:
        """
        if self.server is not None:
            self.server.shutdown()

    def _create_subprocess(self):
        """
            创建子进程，进行PM3组件的启动
            注意，同一个对象无法同时创建两个任务处理的进程
        :return:
        """
        if self.pi is not None and self.pi.poll() is not None:
            print("子进程已经存在，无法重复创建！！！")
            return

        self.pi = subprocess.Popen(
            self.cmd_start,  # 要执行的指令
            bufsize=1024 * 256,
            shell=True,
            close_fds=True,
            start_new_session=True,
            stdin=subprocess.PIPE,  # 输入管道
            stdout=subprocess.PIPE,  # 输出管道
            stderr=subprocess.STDOUT,
            cwd=self.cwd,  # 工作目录
        )
        print("输出流类型: ", self.pi.stdout)
        return self.pi

    def _create_read_thread(self):
        """
            创建读取线程，在有数据时
            自动读取标准输出和标准异常的输出消息
        :return:
        """
        if self.has_read_thread:
            print("已经存在标准输出和标准异常读取的线程，无法创建多个。")
            return
        threading.Thread(target=self._run_std_output_error).start()

    def _create_server_thread(self):
        """
            创建一个服务线程，用于转发执行PM3的任务
        :return:
        """
        if self.server is not None:
            print("已经存在转发服务，不允许多次启动。")
            return

        # 内部创建函数
        self.server = RFServer(self.hp, self.ServerClass)

        def startInternal():
            # 进行服务轮询监听
            self.server.serve_forever()

        # 启用子线程
        thread = threading.Thread(target=startInternal)
        thread.start()
        print("命令转发服务已启动，开始监听")

    def createCMD(self, cmd):
        """
            创建普通指令包
        :param cmd:
        :return:
        """
        return self.DEFAULT_CMD_START + " : " + cmd

    def createCTL(self, cmd):
        """
            创建控制指令包
        :param cmd:
        :return:
        """
        return self.DEFAULT_CTL_START + " : " + cmd

    def createPLT(self, cmd):
        """
            创建平台指令包
        :param cmd:
        :return:
        """
        return self.DEFAULT_PLT_START + " : " + cmd

    def startManager(self):
        """
            开启管理器，启动PM3的客户端，等待任务执行
        :return:
        """
        if self.has_manager:
            print("已经开启PM3管理器，拒绝多次开启。")
            return
        print("\n**********************************")
        print("PM3管理器的子进程启动中...")
        self._create_read_thread()
        self._create_subprocess()
        self._create_server_thread()
        self.has_manager = True
        print("启动完成，开始处理任务...")
        print("**********************************\n")

    def stopManger(self):
        """
            停止管理器，关闭PM3的客户端，结束任务执行
        :return:
        """
        self._destroy_subprocess()
        return self.pi is None

    def reworkManager(self):
        """
            重启管理器，恢复初始化状态
        :return:
        """
        # 先销毁
        print("\n开始销毁命令处理子进程...")
        self._destroy_subprocess()
        print("销毁命令处理子进程完成，开始重新创建...")
        # 再创建
        self._create_subprocess()
        print("重新创建完成.\n")
        return self.hasManager()

    def hasManager(self):
        """
            当前的PM3客户端管理器是否在运行
            换句话说，就是PM3的客户端有木有在正常运行
        :return:
        """
        return self.pi is not None and self.pi.poll() is None

    def destroy(self):
        """
            销毁所有的任务
        :return:
        """
        self._destroy_subprocess()
        self._destroy_read_thread()
        self._destroy_server_thread()

    def requestTask(self, cmd, listener):
        """
            请求执行任务，获得一个任务管理的封装对象
        :param listener:
        :param cmd:
        :return:
        """
        if self.has_tasking:
            print("不允许多个任务一起请求，这会导致输出流的重定向出现异常！")
            return

        if isinstance(cmd, str):
            cmd = cmd.encode()

        self._set_has_tasking(True)
        # 添加换行符，不然proxmark3的readline不会处理
        cmd_old = cmd
        if not cmd.endswith(b"\r\n"):
            cmd = cmd + b"\r\n"

        self.line_listener = listener

        print("\n指令发送中....")
        if self.pi is not None and not self.pi.poll():
            self.pi.stdin.write(cmd)
            # 写完后直接刷新到设备
            self.pi.stdin.flush()
            print("指令 {} 发送完成，等待完成中...".format(cmd_old))

            while self.has_tasking:
                time.sleep(0.001)

            print("requestTask() 执行任务完成。")
            return True
        else:
            print("管理器离线，请求失败。")
            listener(self.DEFAULT_OFFLINE)
            return False

    def hasTasking(self):
        """
            判断当前是否有任务在执行
        :return:
        """
        return self.has_tasking


if __name__ == '__main__':

    path = r"E:\\PM3\\已解压\\proxmark3-20201026"
    os.chdir(path)

    cwd_4_pm3 = os.path.join(os.path.abspath("."), "pm3")
    if platform.system() == "Windows":
        cwd_4_pm3 = os.path.abspath(os.getcwd())

    hp = ("0.0.0.0", 8888)

    test_cmd = r'proxmark3 com8 --flush'
    ptm = RemoteTaskManager(test_cmd, None, cwd_4_pm3, hp)
    ptm.startManager()

    # 不要让主线程退出
    while True:
        # ptm.requestTask("hf 14a info", lambda line: print(line, end=""))
        time.sleep(1)

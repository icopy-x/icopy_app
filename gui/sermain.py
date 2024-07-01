import importlib
import inspect
import os
import platform

from serpool import Server


class MainServer(Server):
    """
        主服务，这个服务是所有的服务的入口
    """

    NAME_MAIN_SERVER = "main"

    @staticmethod
    def getName():
        """
            返回服务名
        :return:
        """
        return MainServer.NAME_MAIN_SERVER

    @staticmethod
    def is_ser_mod_name_start(n):
        return n.startswith("server_")

    @staticmethod
    def is_ser_clz_name_start(n):
        return n.endswith("Server")

    @staticmethod
    def is_ser_clz_name(n):
        if inspect.isclass(n):
            module_name = getattr(n, "__module__")
            class_name = getattr(n, "__name__")
            # 判断是否是Act模块或者Act类
            is_mod = MainServer.is_ser_mod_name_start(module_name)
            is_clz = MainServer.is_ser_clz_name_start(class_name)
            return is_mod and is_clz
        return False

    def try_start_server(self, clz):
        """
            尝试启动服务
        :param clz:
        :return:
        """
        try:
            self.startServer(clz)
        except Exception as e:
            print("在启动服务时出现了异常: ", e)

    def check_all_server(self):
        """
            次入口初始化
        :return:
        """
        # 为了避免动态依赖，我们需要自动在运行时配置依赖
        # 我们需要搜索所有的activity相关的py文件，获取里面的class

        # 1、搜索当前目录下所有的activity规范内的文件
        #  我们限定，activity文件必须以activity开头，以各自的别名结尾
        #  比如 activity_

        try:
            files = os.listdir("lib")
        except Exception as e:
            print("寻找库路径出现异常: ", e)
            files = []

        # 测试开始 <
        # 在工程目录的构建下，此模块是跟act模块同级的
        # 因此可以直接进行列表，但是在发布状态，act存在于lib目录中
        # 万万不可直接list
        if platform.system() == "Windows":
            files = os.listdir(".")

        # 测试结束 >

        for file in files:
            # print("处理文件: ", file)
            if self.is_ser_mod_name_start(file):  # 我们需要处理
                name = file.rsplit(".")[0]
                # print("动态加载Server模块: ", name)
                lib = importlib.import_module(name)
                if inspect.ismodule(lib):  # 判断是否为模块
                    clzs = inspect.getmembers(lib, self.is_ser_clz_name)
                    for clz_t in clzs:  # 迭代所有的类，进行act储存
                        clz_name = clz_t[0]
                        clz_obj: Server = clz_t[1]

                        # print("类信息: ", clz_name)

                        # 类取出后,我们需要进行判断该类是否有实现getName函数
                        name = clz_obj.getName()

                        # 如果没有名称定义，则不允许启动
                        if name is None:
                            # print("没有清单的类: ", clz_name)
                            continue

                        # 最终，我们启动这个服务
                        print("正在尝试启动服务: ", name, "实现的类名是: ", clz_name)
                        self.try_start_server(clz_obj)
        return

    def onStart(self):
        """
            主服务启动的回调
        :return:
        """
        self.check_all_server()

        # 最终，我们在启动完成所有的子服务之后，
        # 完成自己的生命周期
        self.stopServer(self.NAME_MAIN_SERVER)

    def onStop(self):
        print()
        print("############################")
        print("所有存在的子服务完成，已达尽头")
        print("主服务已到尽头，将会停止服务。")
        print("############################")
        print()

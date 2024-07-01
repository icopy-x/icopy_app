"""
    基础服务池
"""

_SERVER_MAP = {}


class Server:
    """
        服务封装
    """

    @staticmethod
    def getName():
        """
            服务名，全局唯一
        :return:
        """
        return None

    def onStart(self):
        """
            启动服务
        :return:
        """

    def onStop(self):
        """
            结束服务
        :return:
        """

    def onData(self, bundle):
        """
            传给服务处理的数据
        :param bundle:
        :return:
        """

    def startServer(self, clz):
        """
            启动一个服务
        :param clz:
        :return:
        """
        start_server(clz)

    def stopServer(self, name):
        """
            停止已经启动的服务
        :param name:
        :return:
        """
        stop_server(name)

    def sendmsg(self, name, bundle):
        """
            发送消息给其他的服务
        :param name:
        :param bundle:
        :return:
        """
        send_msg(name, bundle)


def send_msg(name, bundle):
    """
        发送消息到服务中
    :param name:
    :param bundle:
    :return:
    """
    if name is None:
        raise Exception("不允许空的服务名")
    if name not in _SERVER_MAP:
        raise Exception("不允许发送给不存在的服务")

    server: Server = _SERVER_MAP[name]
    # 在数据回调中，发送消息
    server.onData(bundle)


def start_server(clz):
    """
        启动一个服务
    :return:
    """
    # 获取服务名
    name = clz.getName()
    if name is None:
        raise Exception("不允许启动无名服务！")
    # 判断服务是否已经存在
    if name in _SERVER_MAP:
        raise Exception("不允许重复启动服务！")

    # 实例化服务
    server: Server = clz()
    # OK，我们任务服务不存在，并且没有重复
    _SERVER_MAP[name] = server
    # 可以启动服务
    server.onStart()


def stop_server(name):
    """
        停止服务
    :param name:
    :return:
    """
    if name is None:
        raise Exception("不允许空的服务名")
    if name not in _SERVER_MAP:
        raise Exception("不允许停用不存在的服务")

    # OK，确保服务存在并且已经启动了之后，
    # 我们可以关闭服务了
    server = _SERVER_MAP.pop(name)
    server.onStop()
    # 请求释放内存
    del server

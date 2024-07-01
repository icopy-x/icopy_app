import socketserver
import socket
import sys
import threading

"""
    创建一个ServerSocket,进行消息等待
    1、客户端连接成功后，将会通过消息封包类型选择操作：
        a. 回调到Server预留的回调
        b. 直接通过客户端的链接对象进行数据返回
    2、所有的传输过程都是通过\r\n结尾的，遇到\r\n即为一帧
"""

# 处理的回调
LISTENER = None


class HandleServer(socketserver.StreamRequestHandler):

    def handle(self):
        # 进行处理以及结果返回
        data = self.rfile.readline().strip()
        if callable(LISTENER):
            fV = LISTENER(data)
            # 转换为字节流
            if isinstance(fV, str):
                fV = fV.encode("utf-8")
            self.request.send(fV)


def startServer(hp, listener):
    """
        开始服务器监听，注意，listener将会返回一个字符串，用作协议的结束标志
    :param hp:
    :param listener:
    :return:
    """
    # 监听器不可以为空，需要判断
    if not callable(listener):
        print("传入的监听器非执行的对象")
        return -1
    global LISTENER
    LISTENER = listener
    # 内部创建函数
    server = socketserver.ThreadingTCPServer(hp, HandleServer)

    def startInternal():
        # 进行服务轮询监听
        server.serve_forever()

    # 启用子线程
    thread = threading.Thread(target=startInternal)
    thread.start()
    print("开始监听")
    return server


def startClient(hp, message):
    """
        开始客户端传输服务，传输一段数据，自动添加换行,传输完成后返回一段数据表示对方的处理结果
    :param hp:
    :param message:
    :return:
    """
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(hp)
    # 转换为字节流
    if isinstance(message, str):
        message = message.encode("utf-8")
    # 发送数据本体
    client.send(message)
    # 发送换行结束符
    client.send(b"\r\n")
    # 接收数据
    buffer = []
    while True:
        data = client.recv(1024)
        if not data: break
        buffer.extend(data)
        # 判断是否有回车换行
        if b"\r\n" in buffer: break
    client.close()
    buffer = buffer[0:len(buffer)]
    return bytes(buffer)


if __name__ == '__main__':
    # 发送数据本体
    cmd_cmd = "Nikola.D.CMD = hf mf list\r\n".encode()
    cmd_ctl = "Nikola.D.CTL = restart\r\n".encode()
    cmd_plt = "Nikola.D.PLT = ping baidu.com\r\n".encode()

    cmd_final = ""
    if len(sys.argv) <= 1:
        print("未添加参数，自动使用命令测试模式...")
        cmd_final = cmd_cmd
    elif sys.argv[1] == "cmd":
        cmd_final = cmd_cmd
    elif sys.argv[1] == "ctl":
        cmd_final = cmd_ctl
    elif sys.argv[1] == "plt":
        cmd_final = cmd_plt
    else:
        print("未添加参数，自动使用命令测试模式...")
        cmd_final = cmd_cmd

    if cmd_final is not None and len(cmd_final) > 0 and not cmd_final.isspace():

        hp = ("127.0.0.1", 8888)

        print("开始连接到服务...")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(hp)
        print("服务连接成功...")

        print("开始发送命令...")

        client.send(cmd_final)
        print("命令发送完成，开始接收回复...")

        # 接收数据
        buffer = bytes()
        while True:
            data = client.recv(1024 * 512)
            if not data: break
            buffer += data
            if b"Nikola.D:" in buffer: break

        print("开始打印...")
        print(buffer.decode(errors="ignore", encoding="gbk"), end="")

        client.close()

import appfiles
import executor

FILE_READ = None


def read(infos):
    """
        读取14a的卡片
    :return:
    """
    global FILE_READ
    FILE_READ = appfiles.create_14443a(infos["uid"])
    return appfiles.save2any(executor.getPrintContent(), FILE_READ)

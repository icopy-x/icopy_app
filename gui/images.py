"""
    存放全局的图片对象
"""
import sys
import os
import debug
import re

from PIL import Image, ImageTk

CACHE_DIST = {}
RES_PATH = "/res/img/"


def createFileByNameFromRes(name):
    file = os.path.split(os.path.realpath(sys.argv[0]))[0]
    file = file + RES_PATH
    # print(file)
    return file + "/" + name


# img为pil格式mode = 1 的单色bmp
# 或者透明度为0/255双模式的png
# 注意，透明度不为255的像素会被设置为透明（0）
# color为rgb格式目标颜色,列表，顺序RGB
# 该函数只能将黑色像素转换为目标颜色，白色像素转换为透明
def transparent(img, color):
    L, H = img.size
    AIMBLACK = 0
    outimg = Image.new('RGBA', (L, H), (color[0], color[1], color[2], 0))  # 创建全透明的图片
    if img.mode == 1:
        AIMBLACK = 0
    elif img.mode == "RGBA":
        AIMBLACK = 255
    for h in range(H):
        for l in range(L):
            dot = (l, h)
            color_1 = img.getpixel(dot)
            # print(color_1)
            if img.mode == 1:
                if color_1 == AIMBLACK:
                    outimg.putpixel(dot, (color[0], color[1], color[2], 255))  # 将目标像素修改为不透明
            elif img.mode == "RGBA":
                outimg.putpixel(dot, (color[0], color[1], color[2], color_1[3]))  # 将目标像素修改为不透明
    # outimg.show()
    return outimg


# 创建透明图片
def makeTransparentImage(x, y, color, transparency, istk=1):
    # x, y, color, transparency, istk=1
    key = str(x) + str(y) + str(color) + str(transparency) + str(istk)
    if key in CACHE_DIST:
        return CACHE_DIST[key]
    # 预处理参数
    if not (istk == 1 or istk == 0):
        debug.ViewMsgASCIIln("创建透明图片错误，输出格式未知")
        return False
    # 预处理尺寸
    if x <= 0 or y <= 0:
        debug.ViewMsgASCIIln("创建透明图片错误，尺寸为0")
        outimg = Image.new('RGBA', (1, 1), (0, 0, 0, 0))  # 创建全透明的图片
        if istk == 1:
            return ImageTk.PhotoImage(outimg)
        elif istk == 0:
            return outimg
    # 预处理透明度
    if transparency < 0 or transparency > 255:
        debug.ViewMsgASCIIln("创建透明图片错误，透明度超限")
        return False
    # 预处理颜色
    if len(color) != 7:
        debug.ViewMsgASCIIln("创建透明图片错误，传入颜色值不正确（过短）")
        return False
    if color[0] != "#":
        debug.ViewMsgASCIIln("创建透明图片错误，传入颜色值需有#前缀")
        return False
    if not re.match('^[0-9a-fA-F]?[0-9a-fA-F]$', color[1:3], flags=0):
        debug.ViewMsgASCIIln("创建透明图片错误，传入颜色值不正确（非法）")
        return False
    if not re.match('^[0-9a-fA-F]?[0-9a-fA-F]$', color[3:5], flags=0):
        debug.ViewMsgASCIIln("创建透明图片错误，传入颜色值不正确（非法）")
        return False
    if not re.match('^[0-9a-fA-F]?[0-9a-fA-F]$', color[5:7], flags=0):
        debug.ViewMsgASCIIln("创建透明图片错误，传入颜色值不正确（非法）")
        return False

    # 分离颜色数值
    colorR = "0x" + color[1:3]
    colorR = int(colorR, 16)
    colorG = "0x" + color[3:5]
    colorG = int(colorG, 16)
    colorB = "0x" + color[5:7]
    colorB = int(colorB, 16)
    # 开始处理
    # 创建透明图片
    outimg = Image.new('RGBA', (x, y), (colorR, colorG, colorB, transparency))
    # outimg.show()
    if istk == 1:
        ret = ImageTk.PhotoImage(outimg)
        CACHE_DIST[key] = ret
        return ret
    elif istk == 0:
        CACHE_DIST[key] = outimg
        return outimg


def loadTk(name):
    key = name
    if key in CACHE_DIST: return CACHE_DIST[key]
    image = ImageTk.PhotoImage(Image.open(createFileByNameFromRes(name)))
    CACHE_DIST[key] = image
    return image


def load(name, rgb=((102, 102, 102), (255, 255, 255))):
    key = name
    if key in CACHE_DIST: return CACHE_DIST[key]
    # if name.endswith(".png"):
    #     img = Image.open(createFileByNameFromRes(name))
    #     img = ImageTk.PhotoImage(img)
    #     tuple_ret = img, img
    # else:
    image = Image.open(createFileByNameFromRes(name))
    tk_img_p = ImageTk.PhotoImage(transparent(image, rgb[0]))
    tk_img_n = ImageTk.PhotoImage(transparent(image, rgb[1]))
    # 合并为元组
    tuple_ret = tk_img_p, tk_img_n
    CACHE_DIST[key] = tuple_ret
    return tuple_ret

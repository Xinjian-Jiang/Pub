import win32gui
import win32con

def set_window_topmost(window_title):
    """
    将指定窗口置顶

    参数:
    - window_title: 窗口的标题（字符串）
    """
    # 查找窗口句柄
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        print(f"未找到窗口: {window_title}")
        return

    # 设置窗口为顶层窗口
    win32gui.SetWindowPos(
        hwnd,                                      # 窗口句柄
        win32con.HWND_TOPMOST,                     # 置顶标志
        0, 0, 0, 0,                               # x, y, width, height（这里不改变位置和大小）
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE # 不改变位置和大小
    )
    print(f"窗口 '{window_title}' 已置顶")


def set_window_position_and_size(window_title, x, y, width, height):
    """
    调整指定窗口的位置和大小

    参数:
    - window_title: 窗口的标题（字符串）
    - x: 左上角的 X 坐标
    - y: 左上角的 Y 坐标
    - width: 窗口的宽度
    - height: 窗口的高度
    """
    # 查找窗口句柄
    hwnd = win32gui.FindWindow(None, window_title)
    if hwnd == 0:
        print(f"未找到窗口: {window_title}")
        return
    
    # 调整窗口位置和大小
    win32gui.MoveWindow(hwnd, x, y, width, height, True)
    print(f"已调整窗口: {window_title} 到位置 ({x}, {y})，大小为 {width}x{height}")

def window_init():
    set_window_topmost("雷电模拟器")
    set_window_position_and_size("雷电模拟器", 0, 0, int(452*1.25), int(816*1.25))
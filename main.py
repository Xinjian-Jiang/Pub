# from resize import *
# from pub import *
#
# window_init()
#
# #print(SS())
#
# #print(get_model())
# #print(get_attr())
#
# while True:
#     ret = pub()
#     if ret == 2:
#         if keyboard.is_pressed('space'):
#             break
#         login()

from resize import window_init
from click import listen_clicks
from recognize import get_model, SS
from pub import *
from attr_ocr import get_attr

window_init()
while True:
    pub()

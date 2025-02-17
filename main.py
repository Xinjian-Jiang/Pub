from resize import *
from pub import *

window_init()

#print(SS())

#print(get_model())
#print(get_attr())

while True:
    ret = pub()
    if ret == 2:
        if keyboard.is_pressed('space'):
            break
        login()
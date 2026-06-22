from click import *
from data import *
from recognize import *
from excel import *

interval = 0.5

def pub():
    click(places["招募"], 1)
    cnt = 0
    while 1:
        cnt += 1
        click(places["换一批"], interval)
        click(places["快速"], 1)
        p = SS()
        if p == 1:
            click(places["英雄一"], interval)
            break
        if p == 2:
            click(places["英雄二"], interval)
            break
        if p == 3:
            click(places["英雄三"], interval)
            break
        if cnt > 10:
            click(places["离开"], interval)
            click(places["招募"], 2)
            cnt = 0
    click(places["按钮二"], interval)
    click(places["确定"], 2)
    click(places["离开"], interval)

    click(places["第一个"], interval)
    model = get_model()
    print(model)
    direction = directions[model]
    print(direction)
    if direction == "指定招募券":
        unemploy()
        return 1
    click(places["裸属性"], interval)
    attr0 = get_attr(model)
    print(attr0)
    click(places["总属性"], 2)

    click(places["按钮二"], 2)
    
    click(places["按钮三"], interval)
    if paths[direction][0] == 1:
        click(places["转职一"], interval)
    elif paths[direction][0] == 2:
        click(places["转职二"], interval)
    else:
        click(places["转职三"], interval)
    click(places["转职一"], interval)
    click(places["确定"], 2)

    for i in range (0, 2):
        click(places["按钮二"], interval)
    click(places["按钮二"], 2)
    click(places["按钮三"], interval)
    if paths[direction][1] == 1:
        click(places["转职一"], interval)
    elif paths[direction][1] == 2:
        click(places["转职二"], interval)
    else:
        click(places["转职三"], interval)
    click(places["转职一"], interval)
    click(places["确定"], 1)

    for i in range (0, 3):
        click(places["按钮二"], interval)
    click(places["按钮二"], 2)
    click(places["按钮三"], interval)
    click(places["转职一"], interval)
    click(places["转职一"], interval)
    click(places["确定"], 2)

    for i in range (0, 4):
        click(places["按钮二"], interval)
    click(places["按钮二"], 2)
    click(places["裸属性"], interval)
    attr = []
    try:
        attr = get_attr(model)
    except ValueError:
        return 2
    print(attr)
    write_excel([model] + [direction] + attr0 + attr)
    click(places["总属性"], 2)
    std = standards[direction]
    if is_unemploy(attr, std):
        unemploy()
        return 1
    elif (model == "火枪手" or model == "游侠") and attr[2] < 330:
        unemploy()
        return 1
    else:
        click(places["按钮四"], interval)
        return 0

def is_unemploy(attr, std):
    for i in range(0,4):
        if std[i] > 0 and attr[i] > std[i]:
            return 0
    return 1

def unemploy():
    click(places["按钮一"], interval)
    click(places["确定"], interval)
    time.sleep(3)
    click(places["确定"], 1)

    

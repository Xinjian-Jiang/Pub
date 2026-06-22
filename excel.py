import openpyxl

def write_excel(data):
    workbook = openpyxl.load_workbook("统计表.xlsx")
    sheet = workbook["原始统计数据"]
    sheet.append(data)
    workbook.save("统计表.xlsx")

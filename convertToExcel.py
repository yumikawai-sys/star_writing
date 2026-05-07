import win32com.client

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False

wb = excel.Workbooks.Open(r"C:\path\data.csv")

xlsx_path = r"C:\path\data.xlsx"

# 51 = xlsx
wb.SaveAs(xlsx_path, FileFormat=51)

wb.Close(False)
excel.Quit()

print("done")

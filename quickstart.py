import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
scopes = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']

credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes)
gc = gspread.authorize(credentials)
gauth = GoogleAuth()
drive = GoogleDrive(gauth)
your_sheet_key = "1rXp5Qc0QoQLZaiYSeWVxeJPAvWSlX2dOgf76mQr0cyA"
gs = gc.open_by_key(your_sheet_key)
worksheet1 = gs.worksheet('sheet1')
df = pd.DataFrame({
    'a':['1232131234'], 
    'b':['測試測試'], 
    'c':['測試內容測試內容'],
    'd':['']
})
df_values = df.values.tolist()
gs.values_append('sheet2', {'valueInputOption': 'RAW'}, {'values': df_values})


# data = worksheet1.get_all_records()
# df = pd.DataFrame(data)
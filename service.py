from pysafebrowsing import SafeBrowsing
import re
import requests
import openai
import math
import json
import os
import pyimgur
import base64
import pandas as pd
import gspread
import time
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    Template,
    TemplateMessage,
    ConfirmTemplate,
    CarouselTemplate,
    ButtonsTemplate,
    MessageAction,
    URIAction,
    PostbackAction,
    FlexMessage, 
    FlexContainer,
    FlexComponent,
    FlexBubble,
    FlexBox,
    QuickReply,
    QuickReplyItem
)

class GoogleSafeBrowsingService():
    def __init__(self):
        self.API_KEY = "AIzaSyDuC5RR1bx1U__tQxivy7LA4HLoLoHFXsE"

    def isHttpUrl(self, url):
        url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"
        return re.match(url_pattern, url)

    def risk(self, urls):
        keys = SafeBrowsing(self.API_KEY)
        lists = keys.lookup_urls(urls)
        dangers = []
        if len(lists) > 0 or lists is not None:
            for item in lists:
                if lists[item]["malicious"]:
                    dangers.append(item)
        return dangers

class GoogleVisionAIService():
    def __init__(self):
        self.key = "AIzaSyDuC5RR1bx1U__tQxivy7LA4HLoLoHFXsE"

    def stageInference(self, list, count):
        label = ["adult", "spoof", "medical", "violence", "racy"]
        output = []
        index = 0
        for item in list:
            if item > count:
                output.append(label[index])
            index += 1
        return output

    def scoreSwitch(self, str):
        if str == "VERY_LIKELY":
            return 10
        if str == "LIKELY":
            return 4
        if str == "POSSIBLE":
            return 2
        if str == "UNLIKELY":
            return 0.5
        return 0
    
    def queryImageContent(self, img):
        image_path = './downloaded_image.png'
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            encoded_image = base64.b64encode(image_data).decode('utf-8')
        request_data = {
            "requests": [
                {
                    "image": { "content": encoded_image },
                    "features": [
                        {
                            "type": "LABEL_DETECTION",
                            "maxResults": 5
                        },
                        {
                            "type": "LOGO_DETECTION",
                            "maxResults": 5
                        },
                        {
                            "type": "TEXT_DETECTION",
                            "maxResults": 5
                        },
                        {
                            "type": "SAFE_SEARCH_DETECTION",
                            "maxResults": 5
                        }
                    ]
                }
            ]
        }
        url = "https://vision.googleapis.com/v1/images:annotate?key=%s" % self.key
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=request_data, headers=headers)
        output = ""
        if response.status_code == 200:
            data = response.json()
            labels = data['responses'][0]['labelAnnotations']
            badge = ""
            for label in labels:
                badge += f"圖片有可能是{label['description']}, 可信度有{label['score']:.2f},"
            safes = "。對於圖片安全度分析結果:" + json.dumps(data['responses'][0]['safeSearchAnnotation'])
            texts = "。圖片內所有的文字:" + data['responses'][0]['textAnnotations'][0]['description']
            output = "將圖片丟給Google Vision AI分析後其報告: %s %s %s" % (badge, safes, texts)
        else:
            print(response)
            print("图像识别请求失败。")
        return output

    def queryImage(self, img, checklist):
        data = {
            "requests": [
                {
                    "image": {
                        "source": {
                            "imageUri": img
                        }
                    },
                    "features": [
                        {
                            "type": "SAFE_SEARCH_DETECTION",
                            "maxResults": 50
                        }
                    ]
                }
            ]
        }
        url = "https://vision.googleapis.com/v1/images:annotate?key=%s" % self.key

        response = requests.post(url, data=json.dumps(data), headers={
            "Content-Type": "application/json"
        })

        if response.status_code == 200:
            result = response.json()
            checklist[0] += self.scoreSwitch(result["responses"][0]["safeSearchAnnotation"]["adult"])
            checklist[1] += self.scoreSwitch(result["responses"][0]["safeSearchAnnotation"]["spoof"])
            checklist[2] += self.scoreSwitch(result["responses"][0]["safeSearchAnnotation"]["medical"])
            checklist[3] += self.scoreSwitch(result["responses"][0]["safeSearchAnnotation"]["violence"])
            checklist[4] += self.scoreSwitch(result["responses"][0]["safeSearchAnnotation"]["racy"])
            return checklist
        else:
            return checklist

class LineBotMessageService():
    def __init__(self):
        self.descriptionImageList = [
            "https://i.imgur.com/yKgbU3I.png",
            "https://i.imgur.com/m7iq3gn.png",
            "https://i.imgur.com/bNtWRaQ.png",
            "https://i.imgur.com/L4Gs1io.png",
            "https://i.imgur.com/GGQAwxE.png",
            "https://i.imgur.com/QE11yuJ.png",
            "https://i.imgur.com/GiqPcmn.png",
        ]
        self.descriptionTitleList = [
            "Step.1 開始使用資訊驗證功能",
            "Step.2 開始輸入文字或貼上文字驗證資訊",
            "Step.3 收縮選單並開啟圖片選擇功能",
            "Step.4 點選圖片圖樣，並選擇想查驗的圖片",
            "Step.5 點選輸入框右側，開始語音輸入功能",
            "Step.6 點選中間的錄音，計時開始即可輸入",
            "Step.7 查看預設圖文選單",
        ]
        self.descriptionTextList = [
            "點選手機畫面左下角，選單列的左邊「輸入文字框」關閉圖文選單，並開啟文字輸入框。",
            "1. 可以輸入欲檢測事情\n2. 將訊息轉傳至此聊天 \n3. 貼入文字進行檢測。",
            "1. 點選紅色方框左側「相機」圖示\n 2. 點選紅色方框「圖片」圖示。",
            "傳送與驗證的圖片至聊天室。",
            "可使用文字輸入框右側紅色方框處「錄音」圖示，亦可轉傳音檔至此聊天室驗證。",
            "「錄音」介面並點選中間錄音鍵，上方計時處開始計時後即可開始說話，完成後點選右側按鈕傳送鍵。",
            "想重新點選圖文選單的其他功能嗎? 點這邊。",
        ]
        self.installTitleList = [
            "Step.1 開始使用資訊驗證功能",
            "Step.2 開始輸入文字或貼上文字驗證資訊",
            "Step.3 收縮選單並開啟圖片選擇功能",
            "Step.4 點選圖片圖樣，並選擇想查驗的圖片",
            "Step.5 點選輸入框右側，開始語音輸入功能",
            "Step.6 點選中間的錄音，計時開始即可輸入",
            "Step.7 查看預設圖文選單",
        ]

    def imageResponseTemplate(self, title, text, img, timestamp):
        uri = 'https://www.youtube.com?key=%s' % timestamp
        carousel_template = TemplateMessage(
            alt_text=title,
                template=ButtonsTemplate(
                    title=title,
                    text=text,
                    thumbnail_image_url=img,
                    actions=[
                        URIAction(
                            label='閱讀詳細資料',
                            uri=uri
                        )
                    ]
                )
            )
        return carousel_template

    def audioResponseTemplate(self, title, text, timestamp):
        uri = 'https://www.youtube.com?key=%s' % timestamp
        carousel_template = TemplateMessage(
            alt_text=title,
                template=ButtonsTemplate(
                    title=title,
                    text=text,
                    actions=[
                        URIAction(
                            label='閱讀詳細資料',
                            uri=uri
                        )
                    ]
                )
            )
        return carousel_template

    def trustableTextTemplate(self, event, text, timestamp):
        uri = 'https://www.youtube.com?key=%s' % timestamp
        if len(event.message.text) > 20:
            title = "檢測文字訊息「%s...」結果" % event.message.text[:20]
        else:
            title = "檢測文字訊息「%s」結果" % event.message.text
        carousel_template = TemplateMessage(
                alt_text=title,
                template=ButtonsTemplate(
                title=title,
                text=text,
                actions=[
                    URIAction(
                        label='閱讀詳細資料',
                        uri=uri
                    )
                ]
            )
        )
        return carousel_template

    def sendReplyMessage(self, configuration, event, template):
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[template]
                )
            )
    
    def descriptionTemplate(self):
        buttons = []
        for item in range(len(self.descriptionImageList)):
            if item == 6:
                temp = TemplateMessage(
                    alt_text='查看操作說明與流程之步驟',
                    template=ButtonsTemplate(
                        title=self.descriptionTitleList[item],
                        text=self.descriptionTextList[item],
                        thumbnail_image_url=self.descriptionImageList[item],
                        actions=[
                            MessageAction(label="點我嘗試發送訊息", text="現在虛擬貨幣入金50美金立即送LINE POINT 66666點。")
                        ]
                    )
                )
            else:
                temp = TemplateMessage(
                    alt_text='查看操作說明與流程之步驟',
                    template=ButtonsTemplate(
                        title=self.descriptionTitleList[item],
                        text=self.descriptionTextList[item],
                        thumbnail_image_url=self.descriptionImageList[item],
                        actions=[
                            URIAction(label='影片操作範例', uri='https://www.youtube.com/')
                        ]
                   )
                )
            buttons.append(temp)

        carousel_template = TemplateMessage(
            alt_text='查看操作說明與流程',
            template=CarouselTemplate(
                columns=[
                    buttons[0].template,
                    buttons[1].template,
                    buttons[2].template,
                    buttons[3].template,
                    buttons[4].template,
                    buttons[5].template,
                    buttons[6].template
                ]
            )
        )
        return carousel_template
    
    def installTemplate(self):
        quick_reply = QuickReply(
            items=[
                QuickReplyItem(action=MessageAction(label="Chrome插件", text="Chrome插件安裝資訊")),
                QuickReplyItem(action=MessageAction(label="Firefox插件", text="Firefox插件安裝資訊")),
                QuickReplyItem(action=MessageAction(label="Safari插件", text="Safari插件安裝資訊")),
                QuickReplyItem(action=MessageAction(label="LINE機器人", text="LINE機器人安裝資訊"))
            ]
        )
        text_message = TextMessage(
            text='您要查看哪個安裝資訊呢?',
            quick_reply=quick_reply
        )
        return text_message
    
    def LinebotTextQuest(self, title, msg):
        carousel_template = TemplateMessage(
                alt_text='Buttons Template',
                template=ButtonsTemplate(
                    title=title,
                    text=msg,
                    actions=[
                        URIAction(
                            label='影片操作範例',
                            uri='https://www.youtube.com/'
                        )
                    ]
               )
            )
        return carousel_template

    def unServiceTemplate(self, msgType):
        text = "此服務可以傳送文字、音訊與圖片至此，將為您分析是否為詐騙訊息，亦可點擊下方按鈕查看說明。"
        if (msgType == "video"):
            title = "很抱歉! 目前尚未提供影片分析服務"
        elif(msgType == "sticker"):
            title = "很抱歉! 目前尚未提供貼圖分析服務"
        carousel_template = TemplateMessage(
            alt_text=title,
                template=ButtonsTemplate(
                    title=title,
                    text=text,
                    actions=[
                        MessageAction(
                            label="點我閱讀操作說明", 
                            text="閱讀操作說明"
                        )
                    ]
                )
            )
        return carousel_template
    
class OpenDataAPIService():
    def __init__(self):
        self.API_KEY = ""
        self.ScamLineIdAPI = "https://od.moi.gov.tw/api/v1/rest/datastore/A01010000C-001277-053?limit=1000000"
        self.GambleAPI = "https://od.moi.gov.tw/api/v1/rest/datastore/A01010000C-002150-013?limit=1000000"

    # 呼叫API
    def callScamLineIdAPI(self):
        try:
            response = requests.get(self.ScamLineIdAPI)
            response.raise_for_status()  # 檢查回應狀態碼
            data = response.json()
            return data, True
        except requests.exceptions.RequestException as e:
            print("請求異常:", e)
            return e, False
        except ValueError as e:
            print("JSON解析錯誤:", e)
            return e, False
        except Exception as e:
            print("發生異常:", e)
            return e, False

    def callGambleAPI(self):
        try:
            response = requests.get(self.GambleAPI)
            response.raise_for_status()  # 檢查回應狀態碼
            data = response.json()
            return data, True
        except requests.exceptions.RequestException as e:
            print("請求異常:", e)
            return e, False
        except ValueError as e:
            print("JSON解析錯誤:", e)
            return e, False
        except Exception as e:
            print("發生異常:", e)
            return e, False

    def compareLineId(self, context, lists):
        output = []
        if lists["success"]:
            id_values = [record["帳號"] for record in lists["result"]["records"]]
            id_pattern = '|'.join(re.escape(id_val) for id_val in id_values)
            id_regex = re.compile(id_pattern)

        for con in context:
            if id_regex.search(con):
                output.append(con)
        return output

    def compareGambleWebUrl(self, links, lists):
        output = []
        if lists["success"]:
            for i in range(len(lists["result"]["records"])):
                weburl = lists["result"]["records"][i]["WEBURL"]
                for j in links:
                    pattern = r"%s" % weburl
                    match = re.search(pattern, j)
                    if match:
                        output.append(weburl)
        return output


openai.organization = "org-3J59dtoNNWOyIR8CE6GHHPJR"
openai.api_key = "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"

class OpenAIService():
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.system = "回答可信度，只需要0-100分數，不需要其他答案，如果無法判斷則回答-1"
        self.demo = "只要每天早上一杯地瓜葉牛奶。不僅有效降低三高，甚至連痛風也沒了；此外，地瓜葉牛奶的作法也很簡單，只要先將地瓜葉川燙過後，再加入鮮奶打成汁即可。"
        self.assistant = "0"
        self.badge_system = "%s \n\n 請只給我以上的文章最簡約的3至4個標籤，並使用繁體中文回應，並使用1. 2. 3. 4.條列"

    def findNumbers(self, string):
        pattern = r'-?\d+'  # 正規表達式模式，表示一個或多個數字
        numbers = re.findall(pattern, string)
        return numbers

    def createScoreChat(self, quest):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.system},
                {"role": "user", "content": self.demo},
                {"role": "assistant", "content": self.assistant},
                {"role": "user", "content": quest},
            ]
        )

        msg = completion.choices[0].message
        score = int(self.findNumbers(msg["content"])[0])
        return score

    def createBadgeChat(self, quest):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": self.badge_system % quest},
            ]
        )

        msg = completion.choices[0].message["content"]
        lines = msg.split('\n')
        result = []
        for line in lines:
            parts = line.split('. ')
            if len(parts) > 1:
                result.append(parts[1])
        return result
    
    def createLinebotChat(self, quest):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "是否為詐騙的手法與指出是否有可疑之處，並使用繁體中文回應。"},
                {"role": "user", "content": quest},
            ]
        )
        msg = completion.choices[0].message["content"]
        
        if len(msg) >= 60:
            limits = msg[:56] + "..."
        return limits, msg
    
    def audioTransText(self):
        audio_file= open("downloaded_audio.mp3", "rb")
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript['text']
    
    def audioLinebotChat(self, quest):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "分析是否有可疑或詐騙的疑慮，並使用繁體中文回應。"},
                {"role": "user", "content": quest},
            ]
        )
        msg = completion.choices[0].message["content"]
        
        if len(msg) >= 60:
            limits = msg[:56] + "..."
        return limits, msg

class GoogleCustomSearchAPIService():
    def __init__(self):
        self.endpoint = "https://www.googleapis.com/customsearch/v1?cx=%s&key%s=&q=%s"
        self.apiKey = "AIzaSyDuC5RR1bx1U__tQxivy7LA4HLoLoHFXsE"
        self.engineId = "e1d5cbbd723774fc6"

    def deepCompare(self, keyword):
        try:
            url = self.endpoint % (self.engineId, self.apiKey, keyword)
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data, True
        except requests.exceptions.RequestException as e:
            print("請求異常:", e)
            return e, False
        except ValueError as e:
            print("JSON解析錯誤:", e)
            return e, False
        except Exception as e:
            print("發生異常:", e)
            return e, False

class BlackListService():
    def __init__(self):
        self.using = [
            "abuse", "ads", "crypto", "drugs", "facebook",
            "fraud", "gambling", "malware", "phishing", "piracy", "porn",
            "ransomware", "scam", "tiktok", "torrent", "tracking"
        ]

    def read_json_file(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data

    def typeResponser(self, index):
        return self.using[index]

    def searchTypeWeb(self, url):
        dirname = os.path.dirname(os.path.abspath(__file__))

        uindex = 0
        result = []
        for item in self.using:
            path = "%s/urls/%s.json" % (dirname, item)
            data = self.read_json_file(path)

            webs = data["data"]
            for temp in webs:
                if (temp["url"] == url):
                    result.append(uindex)
            uindex += 1
        return result

    def checkMultiableData(self, urls, filters):
        dirname = os.path.dirname(os.path.abspath(__file__))
        result = []
        for item in filters:
            path = "%s/urls/%s.json" % (dirname, item)
            data = self.read_json_file(path)
            webs = data["data"]
            for link in urls:
                for temp in webs:
                    if (temp["url"] == link):
                        result.append(temp["url"])
        return result

class WebCrawlerService():
    def __init__(self) -> None:
        pass

    def additionChild(self, data):
        temp = []
        for item in data:
            if str(item.get_text().strip()) != "":
                temp.append(str(item.get_text().replace(
                    '\n', '').replace('\t', '').strip()))
        return temp

    def progress_elements(self, soup):
        resultData = []
        resultData.append(self.additionChild(soup.find_all('h1')))
        resultData.append(self.additionChild(soup.find_all('h2')))
        resultData.append(self.additionChild(soup.find_all('h3')))
        resultData.append(self.additionChild(soup.find_all('h4')))
        resultData.append(self.additionChild(soup.find_all('h5')))
        resultData.append(self.additionChild(soup.find_all('h6')))
        resultData.append(self.additionChild(soup.find_all('meta')))
        resultData.append(self.additionChild(soup.find_all('title')))
        resultData.append(self.additionChild(soup.find_all('link')))
        resultData.append(self.additionChild(soup.find_all('div')))
        resultData.append(self.additionChild(soup.find_all('img')))
        resultData.append(self.additionChild(soup.find_all('span')))
        resultData.append(self.additionChild(soup.find_all('a')))
        resultData.append(self.additionChild(soup.find_all('ul')))
        resultData.append(self.additionChild(soup.find_all('p')))
        resultData.append(self.additionChild(soup.find_all('table')))
        resultData.append(self.additionChild(soup.find_all('form')))

        result = [
            {
                "tags": "<h1>",
                "data": resultData[0]
            },
            {
                "tags": "<h2>",
                "data": resultData[1]
            },
            {
                "tags": "<h3>",
                "data": resultData[2]
            },
            {
                "tags": "<h4>",
                "data": resultData[3]
            },
            {
                "tags": "<h5>",
                "data": resultData[4]
            },
            {
                "tags": "<h6>",
                "data": resultData[5]
            },
            {
                "tags": "<meta>",
                "data": resultData[6]
            },
            {
                "tags": "<title>",
                "data": resultData[7]
            },
            {
                "tags": "<link>",
                "data": resultData[8]
            },
            {
                "tags": "<div>",
                "data": resultData[9]
            },
            {
                "tags": "<img>",
                "data": resultData[10]
            },
            {
                "tags": "<span>",
                "data": resultData[11]
            },
            {
                "tags": "<a>",
                "data": resultData[12]
            },
            {
                "tags": "<ul>",
                "data": resultData[13]
            },
            {
                "tags": "<p>",
                "data": resultData[14]
            },
            {
                "tags": "<table>",
                "data": resultData[15]
            },
            {
                "tags": "<form>",
                "data": resultData[16]
            },
        ]
        return result

class GoogleSheetService():
    def __init__(self):
        self.sheetID = "1rXp5Qc0QoQLZaiYSeWVxeJPAvWSlX2dOgf76mQr0cyA"
        self.API_KEY = "AIzaSyDuC5RR1bx1U__tQxivy7LA4HLoLoHFXsE"
        self.SCOPE = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    
    def queryLineResult(self, id):
        credentials = Credentials.from_service_account_file('credentials.json', scopes=self.SCOPE)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key(self.sheetID)
        worksheet1 = gs.worksheet('lineResult')
        data = worksheet1.get_all_records()
        df = pd.DataFrame(data)
        matching_rows = df[df.iloc[:, 0] == int(id)]
        if not matching_rows.empty:
            second_column_values = matching_rows.iloc[:, 1].tolist()
            third_column_values = matching_rows.iloc[:, 2].tolist()
            fourth_column_values = matching_rows.iloc[:, 3].tolist()
            return second_column_values, third_column_values, fourth_column_values
        else:
            return None, None, None

    def getAllValue(self):
        credentials = Credentials.from_service_account_file('credentials.json', scopes=self.SCOPE)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key(self.sheetID)
        worksheet1 = gs.worksheet('lineResult')
        data = worksheet1.get_all_records()
        df = pd.DataFrame(data)
    
    def appendValue(self, timestamp, title, context, img):
        credentials = Credentials.from_service_account_file(
            'credentials.json', scopes=self.SCOPE)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key(self.sheetID)
        df = pd.DataFrame({
            'a':[timestamp], 
            'b':[title], 
            'c':[context],
            'd':[img]
        })
        df_values = df.values.tolist()
        gs.values_append("lineResult", {'valueInputOption': 'RAW'}, {'values': df_values})

    def appendComment(self, timestamp, title, url, context, user_id):
        credentials = Credentials.from_service_account_file(
            'credentials.json', scopes=self.SCOPE)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key(self.sheetID)
        df = pd.DataFrame({
            'a':[timestamp], 
            'b':[title], 
            'c':[url],
            'd':[context],
            'e':[user_id],
        })
        df_values = df.values.tolist()
        gs.values_append("comment", {'valueInputOption': 'RAW'}, {'values': df_values})

    def appendCache(self, timestamp, url, result):
        credentials = Credentials.from_service_account_file(
            'credentials.json', scopes=self.SCOPE)
        gc = gspread.authorize(credentials)
        gauth = GoogleAuth()
        drive = GoogleDrive(gauth)
        gs = gc.open_by_key(self.sheetID)
        df = pd.DataFrame({
            'a':[timestamp],
            'c':[url],
            'd':[result]
        })
        df_values = df.values.tolist()
        gs.values_append("cacheWeb", {'valueInputOption': 'RAW'}, {'values': df_values})

class ImgurUploadService():
    def __init__(self):
        self.CLIENT_ID = "2595df26315f361"
        self.CLIENT_SECRET = "e4ba84445df411ec9be4853531997143264efe98"
        self.REFRESH_TOKEN = "3e005262a959ca2845cdeb263cb2f11bd3dba1a6"

    def glucose_graph(self):
        image_path = 'downloaded_image.png'
        response = requests.post(
            'https://api.imgur.com/oauth2/token',
            data = {
                'refresh_token': self.REFRESH_TOKEN,
                'client_id': self.CLIENT_ID,
                'client_secret': self.CLIENT_SECRET,
                'grant_type': 'refresh_token',
            }
        )
        access_token = response.json()['access_token']
        headers = { 'Authorization': f'Bearer {access_token}'}
        with open(image_path, 'rb') as f:
            files = {'image': (image_path, f)}
            response = requests.post(
                'https://api.imgur.com/3/upload', 
                headers=headers,
                files=files)
        image_url = ""
        if response.status_code == 200:
            image_url = response.json()['data']['link']
        return image_url

class LibService():
    def __init__(self):
        self.lists = [
            "無法判斷", "不可信賴", "保留質疑", "中度信賴", "高度安全", "可安全瀏覽"
        ]

    def convertString(self, str):
        return str.replace('\n', ' ').replace('\r', '').strip()

    def rankingArticle(self, score):
        if score < 0:
            return self.lists[0]
        if score == 100:
            score -= 1
        return self.lists[math.floor(score/20)+1]

    def hrefsOutput(self, data):
        links = []
        for item in data:
            key = item.get('href')
            if (key != None and key != "javascript:void(0)" and key != "javascript:void(0);"
                    and key != "#" and key != "/" and key != "" and key[0] != "/"):
                links.append(item.get('href'))
        return links

    def contextOutput(self, data):
        context = []
        prev = ""
        for item in data:
            temp = item.get_text().replace('\n', '').replace('\t', '').strip()
            if prev != temp and temp != None and temp != "":
                prev = temp
                context.append(temp)
        return context

    def convertTimestamp(self):
        now = time.time()
        integer_value = int(now)
        string_value = str(integer_value)
        return string_value
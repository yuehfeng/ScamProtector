from pysafebrowsing import SafeBrowsing
import re
import requests
import openai
import math
import json
import os
import pyimgur

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
        for item in lists:
            if lists[item]["malicious"]:
                print(lists[item])
                dangers.append(item)

        return dangers

class OpenDataAPIService():
    def __init__(self):
        self.API_KEY = ""
        self.ScamLineIdAPI = "https://od.moi.gov.tw/api/v1/rest/datastore/A01010000C-001277-053"
        self.GambleAPI = "https://od.moi.gov.tw/api/v1/rest/datastore/A01010000C-002150-013"
    
    # 呼叫API
    def callScamLineIdAPI(self):
        try:
            response = requests.get(self.ScamLineIdAPI)
            response.raise_for_status() # 檢查回應狀態碼
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
            response.raise_for_status() # 檢查回應狀態碼
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

    def compareLineId(self, content, lists):
        output = []
        if lists["success"]:
            # 欄位
            fields = []
            for item in lists["result"]["fields"]:
                fields.append(item["id"])
            # 查找紀錄
            for i in range(len(lists["result"]["records"])):
                id = lists["result"]["records"][i][fields[1]]
                pattern = r"%s" % id
                match = re.search(pattern, content)
                if match:
                    output.append(id)
                # print(lists["result"]["records"][i][fields[1]])
        return output
    
    def compareGambleWebUrl(self, uri, lists):
        output = []
        if lists["success"]:
            # 欄位
            fields = []
            for item in lists["result"]["fields"]:
                fields.append(item["id"])
            # 查找紀錄
            for i in range(len(lists["result"]["records"])):
                weburl = lists["result"]["records"][i][fields[1]]
                pattern = r"%s" % weburl
                match = re.search(pattern, uri)
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
    
    def findNumbers(self, string):
        pattern = r'-?\d+'  # 正規表達式模式，表示一個或多個數字
        numbers = re.findall(pattern, string)
        return numbers
    
    def createScoreChat(self, quest):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages = [
                {"role": "system", "content": self.system},
                {"role": "user", "content": self.demo},
                {"role": "assistant", "content": self.assistant},
                {"role": "user", "content": quest},
            ]
        )

        msg = completion.choices[0].message
        score = int(self.findNumbers(msg["content"])[0])
        print(completion)
        return score
    
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
            "abuse", "adobe", "ads", "crypto", "drugs", "everything", "facebook", \
            "fraud", "gambling", "malware", "phishing", "piracy", "porn", "ransomware", \
            "scam", "tiktok", "torrent", "tracking"
        ]
    
    def read_json_file(self, file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    
    def typeResponser(self, index):
        return self.using[index]
    
    # 比對黑名單資料
    def searchTypeWeb(self, url):
        dirname = os.path.dirname(os.path.abspath(__file__))
        
        uindex = 0
        result = []
        for item in self.using:
            path = "%s/urls/%s.json" % (dirname, item)
            data = self.read_json_file(path)

            webs = data["data"]
            for temp in webs:
                if(temp["url"] == url):
                    result.append(uindex)
            uindex += 1
        return result

class ImgurUploadService():
    def __init__(self):
        self.CLIENT_ID = "2595df26315f361"

    def glucose_graph(self, imgpath, message_id):
        im = pyimgur.Imgur(self.CLIENT_ID)
        upload_image = im.upload_image(imgpath, title=message_id)
        return upload_image.link

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
import json
import os

def read_json_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def main():
    dirname = os.path.dirname(os.path.abspath(__file__))
    
    using = [
        "abuse", "adobe", "ads", "crypto", "drugs", "everything", "facebook", "fraud", "gambling", "malware", "phishing", "piracy", "porn", "ransomware", "scam", "tiktok", "torrent", "tracking"
    ]

    uindex = 0
    sum = 0
    for item in using:
        path = "%s/urls/%s.json" % (dirname, item)
        # 讀取 JSON 檔案
        json_data = read_json_file(path)
        # 計算陣列長度
        array_length = len(json_data["data"])

        sum += array_length
        log = "第%2d筆 | 資料類型: %10s 陣列長度: %7d" % (uindex+1, using[uindex], array_length)
        print(log)
        uindex += 1

    print("總計長度為: ", sum)

if __name__ == '__main__':
    main()
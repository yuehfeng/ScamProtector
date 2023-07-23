import json

def read_file(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
    return data

def write_json(data, output_file_path):
    with open(output_file_path, 'w') as file:
        json.dump(data, file)

def main():
    input_file_path = "C:/www-server/ScamProtectorBackend/urls/tracking.txt"
    output_file_path = "C:/www-server/ScamProtectorBackend/urls/tracking.json"

    # 讀取檔案
    file_data = read_file(input_file_path)
    lines = file_data.splitlines()
    
    # 列印每一行
    index = 0
    result = []
    for line in lines:
        words = line.split()

        if len(words) == 3:
            temp = {
                "ip": words[1],
                "url": words[2]
            }
            result.append(temp)
        if len(words) == 2:
            temp = {
                "ip": words[0],
                "url": words[1]
            }
            result.append(temp)
        # print(index, line)

    res = {
        "data": result
    }
    # 將資料轉換為JSON格式
    json_data = json.dumps(res)
    json_result = json.loads(json_data)
    write_json(json_result, output_file_path)

    print("檔案已成功輸出為JSON格式！")

if __name__ == '__main__':
    main()
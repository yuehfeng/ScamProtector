ScamProtector 詐騙護手
===

- 初始化安裝
`pip install -r requirement.txt`

- 輸出安裝套件資訊
`pip freeze > requirements.txt`

- 程式進入點/啟動
`py main.py`

- API End-Points
**Web Routes**
| #   | Process   | End-Point               |
| --- | --------- | ----------------------- |
| 1   | Completed | `/`                     |
| 2   | Completed | `/api/v1/web/crawler`   |
| 3   | Completed | `/api/v1/web/blocklist` |
| 4   | Process   | `/api/v1/web/deep`      |
| 5   | Process   | `/api/v1/web/comment`      |

**Extension Routes**
| #     | Process | End-Point             |
| ----- | ------- | --------------------- |
| 1     | Process | `/api/v1/ext/risk`    |
| 2     | Process | `/api/v1/ext/context` |
| 3     | Process | `/api/v1/ext/image`   |
| 4     | Process | `/api/v1/ext/trust`   |
| 5     | Process | `/api/v1/ext/badge`   |
| **6** | Process | `/api/v1/ext/save`    |

**Linebot Routes**
| #   | Process | End-Point       |
| --- | ------- | --------------- |
| 1   | Process | `/callback` |

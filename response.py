from flask import jsonify

class Response(object):
    def __init__(self):
        self.codeMap = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            419: "Page Expired",
            423: "Too Many Request",
        }
    
    def success(self):
        data = {
            'success': True,
            'feedback': "",
            'data': None
        }
        return jsonify(data)
    
    def successWithData(self, result):
        data = {
            'success': True,
            'feedback': "",
            'data': result
        }
        return jsonify(data)
    
    def errorWithData(self, code, result):
        data = {
            'success': False,
            'feedback': {
                'code': code,
                'msg': self.codeMap[code],
                'detail': result
            },
            'data': None
        }
        return jsonify(data)
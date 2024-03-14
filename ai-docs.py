from flask import Flask, request, jsonify
import json
import hmac
import hashlib
import base64
import time
import requests
import json
import tcvectordb
import os
import tcvectordb
from tcvectordb import exceptions
from tcvectordb.model.collection_view import Embedding
from zhipuai import ZhipuAI


vdbclient = tcvectordb.VectorDBClient(
    url='http://lb-n27j42ga-xxx.clb.ap-guangzhou.tencentclb.com:40000', 
    username='root', 
    key='xxx'
    )

app = Flask(__name__)
access_token = "xxx" #TEST
DINGDING_WEBHOOK_URL = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
PORT = 8890
 
def searchKnowlege(question):
    db = vdbclient.database('testdb')
    collView = db.collection_view('knowlege')
    doc_list = collView.search(
            content=question,
            limit=5,
        )
    knowlege = ''
    print("\n\n查询向量数据库：")
    for count,doc in enumerate(doc_list):
            print(f"===================== 查询到知识条目 {count}=====================")
            print(doc.data.text)
            knowlege += doc.data.text
    return knowlege

# baichuan
def generate_answer_from_baichuan(msg):
    url = "https://api.baichuan-ai.com/v1/chat/completions"
    api_key = "sk-xxxxxx"
    data = {
        "model": "Baichuan2-Turbo",
        "messages": [{
                "role": "user",
                "content": msg
            }]
    }
    json_data = json.dumps(data)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }
    response = requests.post(url, data=json_data, headers=headers,timeout=60)
    if response.status_code == 200:
        reply = json.loads(response.text)["choices"][0]["message"]["content"]
        return reply
    else:
        print(response.text)
        print("请求失败，状态码:", response.status_code)

# glm4
def generate_answer_from_zhipu(msg):
    client = ZhipuAI(api_key="xxx")
    response = client.chat.completions.create(
        model="glm-4",
        messages=[
            {
                "role": "user",
                "content": msg
            },
            {
                "role": "system", 
                "content": "你是一个 GitLab 专家，你的任务是根据用户给出的问题和背景知识，给出专业的回答，回答内容中如果涉及 markdown 的标题和代码块，请去掉'#'井号以及'```'这样的代码块标识，如果你根据背景知识没有找到合适的答案，不要编造答案。"
            }
        ],
        top_p=0.7,
        temperature=0.95,
        max_tokens=1024,
        stream=True,
    )
    answer = ''
    for chunk in response:
        answer += chunk.choices[0].delta.content

    return answer
    
# send dingdig message 
def send_to_dingding(dingding_msg):
    url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title":"AI Answer",
            "text": dingding_msg
            }
    }
    print(dingding_msg)
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == "0":
        print("\n钉钉消息发送成功：\n", dingding_msg)
    else:
        print("\n钉钉消息发送失败并提醒用户：\n", response.json())
        dingding_msg = str(response.json())
        data = {
        "msgtype": "markdown",
        "markdown": {
            "title":"AI Answer",
            "text": dingding_msg
            }
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))

@app.route('/dingding', methods=['POST'])
def dingding():
   data = request.json
   question = data.get('text', {}).get('content')
   print("\n钉钉问题:\n", question)

   knowleges = searchKnowlege(question)
   content = json.dumps({
         "请回答问题：": question,
         "背景知识如下：": knowleges
      },ensure_ascii=False)
   answer_baichuan=generate_answer_from_baichuan(content)
   answer_zhipu=generate_answer_from_zhipu(content)
    # 绕开钉钉URL阻断
   if 'gitlab.com' in answer_zhipu:
        answer_zhipu = answer_zhipu.replace('gitlab.com', 'example.com')
   if 'gitlab.com' in answer_zhipu:
        answer_baichuan = answer_baichuan.replace('gitlab.com', 'example.com')
   dingding_msg = f"## 百川 AI 回答：\n {answer_baichuan} \n ------------------ \n  ## 智谱 AI 回答：\n {answer_zhipu}"
   print("\n\n===================== AI 回答：=====================\n\n")
   send_to_dingding(dingding_msg)
   return jsonify({"errcode": 0, "errmsg": "success"})

if __name__ == '__main__':
   app.run(host='0.0.0.0', port=PORT, debug=False)

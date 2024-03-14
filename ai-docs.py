from flask import Flask, request, jsonify
import json
import requests
from tcvectordb import VectorDBClient
from zhipuai import ZhipuAI
import random
from http import HTTPStatus

vdbclient = VectorDBClient(
    url='http://lb-xxxxxxxx.clb.ap-guangzhou.tencentclb.com:40000', 
    username='root', 
    key='xxxxx'
    )

app = Flask(__name__)
access_token = "xxxx"  # 请替换为您的具体access_token
DINGDING_WEBHOOK_URL = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
PORT = 8890
prompt = "你是一个gitlab专家，可以根据用户给的背景知识回答问题。如果背景知识里面没有找到答案，直接说找不到答案。"

def search_knowledge(question):
    db = vdbclient.database('testdb')
    collView = db.collection_view('knowlege')
    doc_list = collView.search(
            content=question,
            limit=5,
        )
    knowledge = ''
    for count, doc in enumerate(doc_list):
        knowledge += doc.data.text
    return knowledge

def generate_answer_openai(msg):
    # 请替换为您的OpenAI API密钥
    openai.api_key = "YOUR_API_KEY"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": msg},
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    response_content = response.choices[0].message.content.replace('\n\n', '\n')
    return response_content

def generate_answer_qianwen(msg):
    # 请替换为您的dashscope API密钥
    messages = [{'role': 'system', 'content': prompt},
                {'role': 'user', 'content': msg}]
    response = dashscope.Generation.call(
        dashscope.Generation.Models.qwen_plus,
        messages=messages,
        seed=random.randint(1, 10000),
        result_format='message',
    )
    content = response['output']['choices'][0]['message']['content']
    return content

def generate_answer_zhipu(msg):
    client = ZhipuAI(api_key="YOUR_API_KEY")
    response = client.chat.completions.create(
        model="glm-4",
        messages=[{"role": "user", "content": msg}],
        top_p=0.7,
        temperature=0.95,
        max_tokens=1024,
        stream=False,
    )
    content = json.loads(response.json())['choices'][0]['message']['content']
    return content

def send_to_dingding(dingding_msg):
    url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}"
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "AI Answer",
            "text": dingding_msg
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    errcode = response.json()["errcode"]
    if errcode == 0:
        print("钉钉消息发送成功：", dingding_msg)
    else:
        print("钉钉消息发送失败并提醒用户：", str(response.json()))
        dingding_msg = str(response.json())
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "AI Answer",
                "text": "出错了：" + dingding_msg
            }
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))

@app.route('/dingding', methods=['POST'])
def dingding():
    data = request.json
    question = data.get('text', {}).get('content')
    knowledges = search_knowledge(question)
    content = json.dumps({
         "请回答问题：": question,
         "背景知识如下：": knowledges
      }, ensure_ascii=False)
    answer_openai = generate_answer_openai(content)
    answer_zhipu = generate_answer_zhipu(content)
    answer_qianwen = generate_answer_qianwen(content)
    
    if 'gitlab.com' in answer_zhipu:
        answer_zhipu = answer_zhipu.replace('gitlab.com', 'example.com')
    if 'gitlab.com' in answer_openai:
        answer_openai = answer_openai.replace('gitlab.com', 'example.com')
    if 'gitlab.com' in answer_qianwen:
        answer_qianwen = answer_qianwen.replace('gitlab.com', 'example.com')
        
    dingding_msg = f"# Openai：\n{answer_openai}\n<br> <br> \n# ChatGLM4：\n{answer_zhipu}\n<br> <br> \n# 通义千问：\n{answer_qianwen}"
    send_to_dingding(dingding_msg)
    return jsonify({"errcode": 0, "errmsg": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

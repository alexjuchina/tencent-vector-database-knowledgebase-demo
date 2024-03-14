import json
import random
import requests
from flask import Flask, request, jsonify
from http import HTTPStatus
import openai
import dashscope
from zhipuai import ZhipuAI
import tcvectordb

# Configuration
ACCESS_TOKEN = "xxxx"
DINGDING_WEBHOOK_URL = f"https://oapi.dingtalk.com/robot/send?access_token={ACCESS_TOKEN}"
PORT = 8890
VECTORDB_CLIENT = tcvectordb.VectorDBClient(
    url='http://lb-xxx-xxxx.clb.ap-guangzhou.tencentclb.com:40000',
    username='root',
    key='xxxx'
)
PROMPT = "你是一个gitlab专家，可以根据用户给的背景知识回答问题。如果背景知识里面没有找到答案，直接说找不到答案。"
OPENAI_API_KEY = "sk-xxxx"
OPENAI_BASE_URL = "https://api.chatanywhere.com.cn"
ZHIPU_API_KEY = "xxx"

app = Flask(__name__)
openai.api_key = OPENAI_API_KEY
openai.base_url = OPENAI_BASE_URL

def search_knowledge(question):
    """Search knowledge from vector database."""
    db = VECTORDB_CLIENT.database('testdb')
    coll_view = db.collection_view('knowlege')
    doc_list = coll_view.search(content=question, limit=5)
    knowledge = ''
    print("\n\n查询向量数据库：")
    for count, doc in enumerate(doc_list):
        print(f"===================== 查询到知识条目 {count}=====================")
        print(doc.data.text)
        knowledge += doc.data.text
    return knowledge

# openai
def generate_answer_from_openai(msg):
    """Generate answer using OpenAI."""
    messages = [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": msg},
    ]
    response = openai.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    return response.choices[0].message.content.replace('\n\n', '\n')

# qianwen
def generate_answer_from_qianwen(msg):
    """Generate answer using QianWen."""
    messages = [{"role": "system", "content": PROMPT}, {"role": "user", "content": msg}]
    response = dashscope.Generation.call(
        dashscope.Generation.Models.qwen_plus,
        messages=messages,
        seed=random.randint(1, 10000),
        result_format='message',
    )
    if response.status_code == HTTPStatus.OK:
        return response['output']['choices'][0]['message']['content']
    else:
        print(f'Request id: {response.request_id}, Status code: {response.status_code}, '
              f'Error code: {response.code}, Error message: {response.message}')

# chatglm4
def generate_answer_from_zhipu(msg):
    """Generate answer using Zhipu AI."""
    client = ZhipuAI(api_key=ZHIPU_API_KEY)
    response = client.chat.completions.create(
        model="glm-4",
        messages=[{"role": "user", "content": msg}],
        top_p=0.7,
        temperature=0.95,
        max_tokens=1024,
        stream=False,
    )
    return json.loads(response.json())['choices'][0]['message']['content']

# send dingding message
def send_to_dingding(dingding_msg):
    """Send message to DingDing webhook."""
    url = DINGDING_WEBHOOK_URL
    headers = {'Content-Type': 'application/json;charset=utf-8'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"AI Answer",
            "text": dingding_msg
        }
    }
    print(dingding_msg)
    response = requests.post(url, headers=headers, data=json.dumps(data))
    errcode = response.json()["errcode"]
    if errcode == 0:
        print("\n钉钉消息发送成功：\n", dingding_msg)
    else:
        print("\n钉钉消息发送失败并提醒用户：\n", str(response.json()))
        dingding_msg = str(response.json())
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "AI Answer",
                "text": "出错了：" + dingding_msg
            }
        }
        requests.post(url, headers=headers, data=json.dumps(data))

@app.route('/dingding', methods=['POST'])
def dingding():
    data = request.json
    question = data.get('text', {}).get('content')
    print("\n钉钉问题:\n", question)

    knowledges = search_knowledge(question)
    content = json.dumps({
        "请回答问题：": question,
        "背景知识如下：": knowledges
    }, ensure_ascii=False)
    answer_openai = generate_answer_from_openai(content)
    print("\nopenai:\n", answer_openai)
    answer_zhipu = generate_answer_from_zhipu(content)
    print("\nzhipu:\n", answer_zhipu)
    answer_qianwen = generate_answer_from_qianwen(content)
    print("\nqianwen:\n", answer_qianwen)

    # 绕开钉钉URL阻断
    answer_zhipu = answer_zhipu.replace('gitlab.com', 'example.com')
    answer_openai = answer_openai.replace('gitlab.com', 'example.com')
    answer_qianwen = answer_qianwen.replace('gitlab.com', 'example.com')

    dingding_msg = f"# Openai：\n{answer_openai}\n<br> <br> \n# ChatGLM4：\n{answer_zhipu}\n<br> <br> \n# 通义千问：\n{answer_qianwen}"
    print("\n\n===================== AI 回答：=====================\n\n")
    send_to_dingding(dingding_msg)
    return jsonify({"errcode": 0, "errmsg": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)

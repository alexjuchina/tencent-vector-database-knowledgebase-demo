## AI 知识库

使用腾讯云向量数据库（目前免费），结合国内大模型 API（智谱GLM4、百川）+ 钉钉，实现知识库的向量化以及问答。

## 如何运行

确保安装了所需的 Python 库，并可以访问腾讯云向量数据库（VectorDB）和其他相关服务。

1. 安装依赖库：
   ```bash
   pip install flask requests tcvectordb zhipuai
   ```

2. 运行 Flask 应用：
   ```bash
   python your_app.py
   ```
   访问 `http://localhost:8890` 可以查看服务运行情况。

## 功能和接口

### 1. `/dingding` 接口

- **描述**：该接口用于接收用户问题，查询相关知识，调用百川 AI 和智谱 AI 进行回答，最后将答案以 markdown 格式发送至钉钉群。

- **请求**：POST 请求，数据为 JSON 格式，包含字段 `text`，其中 `content` 存储用户提出的问题。

- **返回**：JSON 格式，包含 `errcode` 和 `errmsg` 字段，表示是否成功发送。

## 关于 VectorDB 和 AI 服务

- **VectorDB**：使用 `tcvectordb` 库连接 VectorDB，检索相关知识用于问题回答。

- **百川 AI**：通过 `generate_answer_from_baichuan` 函数调用百川 AI 服务获取回答。

- **智谱 AI**：通过 `generate_answer_from_zhipu` 函数调用智谱 AI 服务获取回答。

## 其他信息

- 服务端口：8890
- 钉钉 Webhook URL： `https://oapi.dingtalk.com/robot/send?access_token={access_token}`

**注意**：确保配置相应的 API 密钥和访问令牌，并测试 API 的可用性和稳定性。

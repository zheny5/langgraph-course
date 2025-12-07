# ingestion.py 代码详细拆解

## 📋 文件概述

`ingestion.py` 是 RAG 系统的**数据摄取模块**，负责：
1. 从网页加载文档
2. 将文档分割成小块
3. 创建向量数据库和检索器

---

## 🔍 逐行代码拆解

### 第一部分：导入依赖库

```python
from dotenv import load_dotenv
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
# from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
```

#### 各库的作用：

1. **`dotenv.load_dotenv`**
   - 从 `.env` 文件加载环境变量
   - 用于管理 API 密钥等敏感信息

2. **`RecursiveCharacterTextSplitter`**
   - LangChain 的文本分割器
   - 将长文档递归地分割成小块
   - 使用 tiktoken 编码器进行精确的 token 计数

3. **`Chroma`**
   - 向量数据库，用于存储文档的嵌入向量
   - 支持持久化存储（保存到磁盘）
   - 提供相似度搜索功能

4. **`WebBaseLoader`**
   - 网页文档加载器
   - 从 URL 抓取网页内容
   - 自动解析 HTML 并提取文本

5. **`HuggingFaceEmbeddings`**（已启用）
   - 使用 HuggingFace 的嵌入模型
   - 将文本转换为向量表示
   - 模型：`sentence-transformers/all-MiniLM-L6-v2`

6. **`OpenAIEmbeddings`**（已注释）
   - OpenAI 的嵌入模型
   - 需要 API 密钥，成本较高
   - 代码中已切换为免费的 HuggingFace 模型

---

### 第二部分：加载环境变量

```python
load_dotenv()
```

**作用**：
- 读取项目根目录下的 `.env` 文件
- 将环境变量加载到 `os.environ` 中
- 后续代码可以通过 `os.getenv()` 访问

**示例 .env 文件内容**：
```bash
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
DEEPSEEK_API_KEY=...
```

---

### 第三部分：定义数据源 URL

```python
urls = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",
]
```

**作用**：
- 定义要加载的知识库来源
- 这些是 Lilian Weng 的博客文章，涵盖：
  - **Agent（智能体）**：AI 代理系统
  - **Prompt Engineering（提示工程）**：如何设计提示词
  - **Adversarial Attacks on LLM（对抗攻击）**：大语言模型的安全问题

**为什么选择这些文章？**
- 与 RAG 系统的主题相关
- 内容质量高，适合作为知识库

---

### 第四部分：加载网页文档

```python
docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]
```

#### 第 16 行：`docs = [WebBaseLoader(url).load() for url in urls]`

**执行流程**：
1. 遍历 `urls` 列表中的每个 URL
2. 为每个 URL 创建 `WebBaseLoader` 实例
3. 调用 `.load()` 方法抓取网页内容
4. 返回 `Document` 对象列表

**返回结果**：
```python
docs = [
    [Document(page_content="...", metadata={...})],  # URL 1 的文档
    [Document(page_content="...", metadata={...})],  # URL 2 的文档
    [Document(page_content="...", metadata={...})],  # URL 3 的文档
]
```

**注意**：每个 URL 可能返回多个 `Document` 对象（如果网页有多个部分）

#### 第 17 行：`docs_list = [item for sublist in docs for item in sublist]`

**作用**：扁平化嵌套列表

**转换过程**：
```python
# 转换前（嵌套列表）
docs = [
    [doc1, doc2],  # URL 1 的文档列表
    [doc3],        # URL 2 的文档列表
    [doc4, doc5]   # URL 3 的文档列表
]

# 转换后（扁平列表）
docs_list = [doc1, doc2, doc3, doc4, doc5]
```

**为什么需要扁平化？**
- 后续处理需要统一的文档列表
- 方便批量处理所有文档

---

### 第五部分：文档分割

```python
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=250, chunk_overlap=0
)
doc_splits = text_splitter.split_documents(docs_list)
```

#### 创建分割器

**`RecursiveCharacterTextSplitter.from_tiktoken_encoder()`**：
- 使用 **tiktoken** 编码器（OpenAI 的 tokenizer）
- 精确计算 token 数量，而不是字符数
- 确保分割后的块大小符合模型要求

**参数说明**：
- **`chunk_size=250`**：
  - 每个文档块的最大 token 数
  - 250 tokens ≈ 200-300 个单词
  - **为什么这么小？** 可能是为了更精确的检索，或者测试目的

- **`chunk_overlap=0`**：
  - 文档块之间的重叠 token 数
  - 0 表示没有重叠
  - **通常建议设置重叠**（如 50），避免在边界处丢失上下文

#### 执行分割

**`text_splitter.split_documents(docs_list)`**：
- 将每个文档递归地分割成小块
- 优先按段落分割，然后是句子，最后是字符
- 返回分割后的 `Document` 对象列表

**分割示例**：
```python
# 原始文档（1000 tokens）
doc = Document(page_content="很长的文章内容...")

# 分割后（每个 250 tokens）
doc_splits = [
    Document(page_content="文章第1部分..."),  # 250 tokens
    Document(page_content="文章第2部分..."),  # 250 tokens
    Document(page_content="文章第3部分..."),  # 250 tokens
    Document(page_content="文章第4部分..."),  # 250 tokens
]
```

---

### 第六部分：创建向量数据库（已注释）

```python
# vectorstore = Chroma.from_documents(
#     documents=doc_splits,
#     collection_name="rag-chroma",
#     embedding=OpenAIEmbeddings(),
#     persist_directory="./.chroma",
# )
```

**这段代码的作用**（如果取消注释）：
- **首次运行**时创建向量数据库
- 将文档和嵌入向量存储到 Chroma
- 保存到本地目录 `./.chroma`

**为什么被注释？**
- 向量数据库已经创建过了
- 避免重复创建，节省时间和 API 调用

**如果取消注释会发生什么？**
- 重新生成所有文档的嵌入向量
- 覆盖现有的向量数据库
- 需要 OpenAI API 密钥（如果使用 OpenAIEmbeddings）

---

### 第七部分：创建检索器

```python
retriever = Chroma(
    collection_name="rag-chroma",
    persist_directory="./.chroma",
    # embedding_function=OpenAIEmbeddings(),
    embedding_function=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
).as_retriever()
```

#### 连接现有向量数据库

**`Chroma()`** 构造函数：
- **`collection_name="rag-chroma"`**：
  - 集合名称，用于标识不同的知识库
  - 可以创建多个集合存储不同主题的文档

- **`persist_directory="./.chroma"`**：
  - 向量数据库的存储路径
  - 如果目录不存在，会自动创建
  - 持久化存储，重启后数据仍然存在

- **`embedding_function=HuggingFaceEmbeddings(...)`**：
  - 指定嵌入模型
  - **必须与创建时使用的模型一致**！
  - 模型：`all-MiniLM-L6-v2`
    - 384 维向量
    - 速度快，质量好
    - 免费使用

#### 转换为检索器

**`.as_retriever()`**：
- 将 Chroma 向量数据库转换为检索器对象
- 提供 `invoke(query)` 方法进行相似度搜索
- 返回与查询最相关的文档

**检索器使用示例**（在其他文件中）：
```python
# graph/nodes/retrieve.py
documents = retriever.invoke("agent memory?")
# 返回最相关的文档列表
```

---

## 🔄 完整执行流程

```
1. 加载环境变量 (.env)
   ↓
2. 定义 URL 列表
   ↓
3. 使用 WebBaseLoader 抓取网页内容
   ↓
4. 扁平化文档列表
   ↓
5. 使用 RecursiveCharacterTextSplitter 分割文档
   ↓
6. （可选）创建向量数据库（首次运行）
   ↓
7. 连接现有向量数据库并创建检索器
   ↓
8. 导出 retriever 供其他模块使用
```

---

## ⚠️ 注意事项

### 1. 嵌入模型一致性
- **创建向量数据库时**使用的嵌入模型
- **检索时**使用的嵌入模型
- **必须相同**，否则检索结果不准确

### 2. 首次运行 vs 后续运行
- **首次运行**：需要取消注释 `Chroma.from_documents()` 创建数据库
- **后续运行**：直接使用现有的数据库（当前代码状态）

### 3. chunk_size 的选择
- **当前设置**：250 tokens（较小）
- **建议**：根据模型上下文窗口调整
  - GPT-3.5: 4096 tokens → chunk_size 可以设置 1000-2000
  - GPT-4: 8192 tokens → chunk_size 可以设置 2000-4000

### 4. chunk_overlap 的重要性
- **当前设置**：0（无重叠）
- **建议**：设置 10-20% 的重叠
  - 避免在边界处丢失上下文
  - 提高检索质量

---

## 🎯 代码优化建议

### 建议 1：添加重叠
```python
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=250,
    chunk_overlap=25  # 10% 重叠
)
```

### 建议 2：条件创建数据库
```python
import os

if not os.path.exists("./.chroma"):
    # 首次运行，创建数据库
    vectorstore = Chroma.from_documents(
        documents=doc_splits,
        collection_name="rag-chroma",
        embedding_function=HuggingFaceEmbeddings(...),
        persist_directory="./.chroma",
    )
```

### 建议 3：添加错误处理
```python
try:
    docs = [WebBaseLoader(url).load() for url in urls]
except Exception as e:
    print(f"加载 URL 失败: {url}, 错误: {e}")
```

---

## 📊 总结

`ingestion.py` 是 RAG 系统的**数据准备阶段**，负责：
- ✅ 从网页加载原始文档
- ✅ 将文档分割成适合处理的小块
- ✅ 创建向量数据库和检索器
- ✅ 为后续的检索和生成提供数据基础

**关键输出**：`retriever` 对象，供 `graph/nodes/retrieve.py` 使用。


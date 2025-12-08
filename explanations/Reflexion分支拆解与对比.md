# Reflexion 分支详细拆解与对比

## 📚 当前 Reflexion 分支概述

这是一个**更高级的 Reflexion Agent**，结合了**研究型问答**和**工具调用**功能。与之前的简单 Reflection 分支相比，这个版本更加复杂和功能丰富。

---

## 🏗️ 项目结构

```
langgraph-course/
├── main.py           # 主入口，定义工作流图
├── chains.py         # 链定义（draft 和 revise）
├── schemas.py        # Pydantic 数据模型
├── tool_executor.py  # 工具执行器
└── pyproject.toml    # 依赖配置
```

---

## 🔍 核心文件详细拆解

### 1. schemas.py - 数据模型定义

#### 文件功能
定义 Pydantic 模型，用于结构化输出和数据验证。

#### 代码拆解

```python
class Reflection(BaseModel):
    missing: str = Field(description="Critique of what is missing.")
    superfluous: str = Field(description="Critique of what is superfluous")
```

**Reflection 类**：
- **missing**：指出答案中缺少什么
- **superfluous**：指出答案中多余的部分
- 用于结构化反思反馈

---

```python
class AnswerQuestion(BaseModel):
    """Answer the question."""

    answer: str = Field(description="~250 word detailed answer to the question.")
    reflection: Reflection = Field(description="Your reflection on the initial answer.")
    search_queries: List[str] = Field(
        description="1-3 search queries for researching improvements to address the critique of your current answer."
    )
```

**AnswerQuestion 类**：
- **answer**：~250 字的详细答案
- **reflection**：反思对象（包含 missing 和 superfluous）
- **search_queries**：1-3 个搜索查询，用于改进答案

**特点**：
- 一次性输出答案、反思和搜索查询
- 结构化数据，便于处理

---

```python
class ReviseAnswer(AnswerQuestion):
    """Revise your original answer to your question."""

    references: List[str] = Field(
        description="Citations motivating your updated answer."
    )
```

**ReviseAnswer 类**：
- 继承自 `AnswerQuestion`
- 额外包含 **references**：引用列表
- 用于修订后的答案

---

### 2. chains.py - 链定义

#### 文件功能
定义两个链：`first_responder`（初始回答）和 `revisor`（修订回答）。

#### 代码拆解

#### 基础提示词模板

```python
actor_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are expert researcher.
Current time: {time}

1. {first_instruction}
2. Reflect and critique your answer. Be severe to maximize improvement.
3. Recommend search queries to research information and improve your answer.""",
        ),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Answer the user's question above using the required format."),
    ]
).partial(
    time=lambda: datetime.datetime.now().isoformat(),
)
```

**提示词结构**：
1. **角色定义**：专家研究员
2. **当前时间**：动态插入
3. **三个任务**：
   - 提供答案
   - 反思和批评答案
   - 推荐搜索查询
4. **消息占位符**：插入历史消息
5. **格式要求**：使用所需格式

**`.partial()` 方法**：
- 预填充部分参数
- `time` 使用 lambda 函数动态生成

---

#### First Responder 链

```python
first_responder_prompt_template = actor_prompt_template.partial(
    first_instruction="Provide a detailed ~250 word answer."
)

first_responder = first_responder_prompt_template | llm.bind_tools(
    tools=[AnswerQuestion], tool_choice="AnswerQuestion"
)
```

**功能**：
- 初始回答生成器
- 使用 `AnswerQuestion` 工具
- 强制使用该工具（`tool_choice="AnswerQuestion"`）

**输出格式**：
```python
{
    "answer": "详细答案...",
    "reflection": {
        "missing": "缺少的信息...",
        "superfluous": "多余的信息..."
    },
    "search_queries": ["查询1", "查询2", "查询3"]
}
```

---

#### Revisor 链

```python
revise_instructions = """Revise your previous answer using the new information.
    - You should use the previous critique to add important information to your answer.
        - You MUST include numerical citations in your revised answer to ensure it can be verified.
        - Add a "References" section to the bottom of your answer (which does not count towards the word limit). In form of:
            - [1] https://example.com
            - [2] https://example.com
    - You should use the previous critique to remove superfluous information from your answer and make SURE it is not more than 250 words.
"""

revisor = actor_prompt_template.partial(
    first_instruction=revise_instructions
) | llm.bind_tools(tools=[ReviseAnswer], tool_choice="ReviseAnswer")
```

**修订指令**：
- 使用新信息修订答案
- 添加重要信息（基于之前的批评）
- **必须包含数字引用**
- 添加"References"部分
- 删除多余信息
- 确保不超过 250 字

**输出格式**：
```python
{
    "answer": "修订后的答案...",
    "reflection": {...},
    "search_queries": [...],
    "references": ["https://example.com", ...]  # 新增
}
```

---

### 3. tool_executor.py - 工具执行器

#### 文件功能
定义工具执行节点，用于执行搜索查询。

#### 代码拆解

```python
tavily_tool = TavilySearch(max_results=5)

def run_queries(search_queries: list[str], **kwargs):
    """Run the generated queries."""
    return tavily_tool.batch([{"query": query} for query in search_queries])
```

**功能**：
- 使用 Tavily 搜索工具
- `max_results=5`：每个查询最多返回 5 个结果
- `batch()`：批量执行多个查询

---

```python
execute_tools = ToolNode(
    [
        StructuredTool.from_function(run_queries, name=AnswerQuestion.__name__),
        StructuredTool.from_function(run_queries, name=ReviseAnswer.__name__),
    ]
)
```

**ToolNode**：
- LangGraph 预构建的工具执行节点
- 支持两个工具：`AnswerQuestion` 和 `ReviseAnswer`
- 自动执行工具调用

---

### 4. main.py - 工作流定义

#### 文件功能
定义完整的 LangGraph 工作流，连接所有节点。

#### 代码拆解

```python
from langchain_core.messages import BaseMessage, ToolMessage
from langgraph.graph import END, MessageGraph
from chains import revisor, first_responder
from tool_executor import execute_tools

MAX_ITERATIONS = 2
```

**导入说明**：
- `MessageGraph`：LangGraph 的消息图（简化版状态图）
- `MAX_ITERATIONS = 2`：最大迭代次数

---

#### 构建图

```python
builder = MessageGraph()
builder.add_node("draft", first_responder)
builder.add_node("execute_tools", execute_tools)
builder.add_node("revise", revisor)
builder.add_edge("draft", "execute_tools")
builder.add_edge("execute_tools", "revise")
```

**节点定义**：
1. **draft**：初始回答生成
2. **execute_tools**：执行搜索工具
3. **revise**：修订答案

**边定义**：
- `draft → execute_tools`：生成后执行搜索
- `execute_tools → revise`：搜索后修订

---

#### 条件判断函数

```python
def event_loop(state: List[BaseMessage]) -> str:
    count_tool_visits = sum(isinstance(item, ToolMessage) for item in state)
    num_iterations = count_tool_visits
    if num_iterations > MAX_ITERATIONS:
        return END
    return "execute_tools"
```

**功能**：
- 统计 `ToolMessage` 的数量
- 如果超过 `MAX_ITERATIONS`（2），结束
- 否则继续执行工具

**逻辑**：
- 每次工具执行都会添加 `ToolMessage`
- 通过统计 `ToolMessage` 数量判断迭代次数

---

#### 条件边

```python
builder.add_conditional_edges("revise", event_loop, {END:END, "execute_tools":"execute_tools"})
builder.set_entry_point("draft")
```

**条件路由**：
- 从 `revise` 节点出发
- 根据 `event_loop` 的结果路由
- `END` → 结束
- `"execute_tools"` → 继续执行工具

---

## 🔄 完整工作流程

### 工作流图

```
开始
  ↓
draft (生成初始答案)
  ↓
execute_tools (执行搜索)
  ↓
revise (修订答案)
  ↓
event_loop() 判断
  ├─→ 迭代次数 > 2 → END (结束)
  └─→ 迭代次数 ≤ 2 → execute_tools (继续搜索)
                      ↓
                  返回 revise (循环)
```

### 执行示例

#### 第 1 轮：初始回答

```python
# 输入
"Write about AI-Powered SOC / autonomous soc problem domain, 
 list startups that do that and raised capital."

# draft 节点
输出: {
    "answer": "AI-Powered SOC (Security Operations Center) is...",
    "reflection": {
        "missing": "缺少具体的初创公司名称和融资信息",
        "superfluous": "一些通用描述可以删除"
    },
    "search_queries": [
        "AI-Powered SOC startups funding",
        "autonomous SOC companies raised capital",
        "security operations center AI startups"
    ]
}

# execute_tools 节点
执行搜索，获取结果

# revise 节点
基于搜索结果修订答案
```

#### 第 2 轮：修订

```python
# revise 节点
输出: {
    "answer": "修订后的答案，包含具体公司名称...",
    "reflection": {...},
    "search_queries": [...],
    "references": [
        "https://example.com/startup1",
        "https://example.com/startup2"
    ]
}

# event_loop 判断
ToolMessage 数量 = 2
2 ≤ 2 → 继续（因为 > 2 才结束）

# 第 3 轮后
ToolMessage 数量 = 3
3 > 2 → 返回 END
```

---

## 📊 两个分支的对比

### 1. 简单 Reflection 分支（之前）

#### 特点
- ✅ **简单**：只有生成和反思两个节点
- ✅ **轻量**：不需要工具调用
- ✅ **快速**：迭代速度快

#### 工作流
```
GENERATE → REFLECT → GENERATE → ...
```

#### 应用场景
- Twitter 推文改进
- 内容创作优化
- 不需要外部信息的任务

#### 终止条件
- 基于消息数量（> 6）

---

### 2. Reflexion 分支（当前）

#### 特点
- ✅ **复杂**：三个节点 + 工具调用
- ✅ **功能丰富**：包含搜索和研究
- ✅ **结构化**：使用 Pydantic 模型

#### 工作流
```
draft → execute_tools → revise → [循环]
```

#### 应用场景
- 研究型问答
- 需要外部信息的任务
- 需要引用的学术性回答

#### 终止条件
- 基于工具调用次数（> 2）

---

## 🔍 详细对比表

| 特性 | 简单 Reflection | Reflexion |
|------|----------------|-----------|
| **节点数量** | 2（生成、反思） | 3（draft、工具、revise） |
| **工具调用** | ❌ 无 | ✅ Tavily 搜索 |
| **结构化输出** | ❌ 无 | ✅ Pydantic 模型 |
| **引用支持** | ❌ 无 | ✅ 数字引用和 References |
| **终止条件** | 消息数量 | 工具调用次数 |
| **复杂度** | 低 | 高 |
| **应用场景** | 内容创作 | 研究型问答 |
| **迭代逻辑** | 生成→反思→生成 | 生成→搜索→修订→搜索 |
| **输出质量** | 中等 | 高（有引用） |

---

## 🎯 关键区别总结

### 1. 架构复杂度

**简单 Reflection**：
- 2 个节点
- 简单的消息传递
- 无工具调用

**Reflexion**：
- 3 个节点
- 工具集成
- 结构化数据模型

### 2. 功能差异

**简单 Reflection**：
- 自我评估和改进
- 基于提示词的反馈

**Reflexion**：
- 自我评估 + 外部搜索
- 结构化反思（missing/superfluous）
- 引用和验证

### 3. 输出质量

**简单 Reflection**：
- 改进的内容
- 无引用验证

**Reflexion**：
- 改进的内容
- 数字引用
- References 部分
- 可验证的信息

### 4. 应用场景

**简单 Reflection**：
- 推文优化
- 内容创作
- 不需要外部信息的任务

**Reflexion**：
- 研究型问答
- 学术性回答
- 需要引用和验证的任务

---

## 💡 设计模式对比

### 简单 Reflection 模式

```
生成 → 反思 → 改进 → 反思 → ...
```

**特点**：
- 纯文本反馈
- 基于提示词的评估
- 简单的循环

### Reflexion 模式

```
生成 → 搜索 → 修订 → 搜索 → ...
```

**特点**：
- 结构化反馈（missing/superfluous）
- 外部信息补充
- 引用和验证
- 更复杂的控制流

---

## 📝 总结

### 简单 Reflection 分支
- **适合**：内容创作、推文优化
- **特点**：简单、快速、轻量
- **优势**：易于理解和实现

### Reflexion 分支
- **适合**：研究型问答、学术性任务
- **特点**：复杂、功能丰富、高质量
- **优势**：输出质量高，有引用验证

**选择建议**：
- 如果只需要改进内容质量 → 使用简单 Reflection
- 如果需要外部信息和引用 → 使用 Reflexion

两个分支都展示了 Reflection 模式的核心思想：**自我评估和迭代改进**，但实现方式和应用场景不同！


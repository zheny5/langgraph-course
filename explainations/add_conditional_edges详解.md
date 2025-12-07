# add_conditional_edges 详解

## 📋 问题

在 `main.py` 第 28-35 行：
```python
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {
        END: END,
        ACT: ACT,
    },
)
```

这三行代码是什么意思？

---

## 🔍 答案：添加条件边（Conditional Edges）

`add_conditional_edges` 是 LangGraph 的方法，用于添加**条件路由边**，根据某个条件函数的结果决定工作流的下一步。

---

## 💡 函数签名

```python
add_conditional_edges(
    source_node,      # 源节点
    condition_func,   # 条件判断函数
    path_map          # 路径映射字典
)
```

---

## 🎯 代码逐行解析

### 第 28 行：`flow.add_conditional_edges(`

**作用**：调用 LangGraph 的方法，添加条件边

### 第 29 行：`AGENT_REASON,`

**参数 1：源节点**
- `AGENT_REASON` = `"agent_reason"`（推理节点）
- 表示条件边从 `agent_reason` 节点出发

### 第 30 行：`should_continue,`

**参数 2：条件判断函数**

让我们看看 `should_continue` 的定义（第 15-18 行）：
```python
def should_continue(state: dict) -> str:
    if not state["messages"][LAST].tool_calls:
        return END
    return ACT
```

**功能**：
- 检查最后一条消息是否有工具调用
- **没有工具调用** → 返回 `END`（结束）
- **有工具调用** → 返回 `ACT`（执行工具）

### 第 31-34 行：路径映射字典

```python
{
    END: END,  # 如果返回 "END"，则路由到 END（结束）
    ACT: ACT,  # 如果返回 "ACT"，则路由到 ACT（工具节点）
}
```

**作用**：将条件函数的返回值映射到目标节点

---

## 🔄 完整执行流程

### 工作流图

```
开始
  ↓
agent_reason (推理节点)
  ↓
should_continue() 判断
  ├─→ 返回 "END" → END (结束)
  └─→ 返回 "ACT" → ACT (工具节点)
                      ↓
                  返回 agent_reason (循环)
```

### 场景 1：LLM 直接回答（不需要工具）

```python
# 步骤1：agent_reason 节点执行
state = {
    "messages": [
        HumanMessage("Hello"),
        AIMessage("Hi! How can I help?")  # 没有 tool_calls
    ]
}

# 步骤2：should_continue 判断
should_continue(state)
# 检查: state["messages"][-1].tool_calls = None
# 返回: "END"

# 步骤3：路由
# "END" → END
# 工作流结束 ✅
```

### 场景 2：LLM 需要调用工具

```python
# 步骤1：agent_reason 节点执行
state = {
    "messages": [
        HumanMessage("what is the weather in sf?"),
        AIMessage(
            "I'll search for that.",
            tool_calls=[{"name": "tavily_search", "args": {...}}]  # 有工具调用
        )
    ]
}

# 步骤2：should_continue 判断
should_continue(state)
# 检查: state["messages"][-1].tool_calls = [...]
# 返回: "ACT"

# 步骤3：路由
# "ACT" → ACT (工具节点)
# 执行工具，然后返回 agent_reason (循环)
```

---

## 📊 可视化说明

### 不使用条件边（固定路径）

```python
# 固定路径：总是执行工具
flow.add_edge(AGENT_REASON, ACT)
flow.add_edge(ACT, AGENT_REASON)
```

**问题**：即使 LLM 已经给出最终答案，也会继续执行工具（浪费资源）

### 使用条件边（智能路由）

```python
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {
        END: END,  # 如果不需要工具，结束
        ACT: ACT,  # 如果需要工具，执行工具
    },
)
```

**优势**：
- ✅ 根据实际情况决定下一步
- ✅ 避免不必要的工具调用
- ✅ 提高效率，节省成本

---

## 🎯 路径映射字典详解

### 字典结构

```python
{
    "条件函数返回值1": "目标节点1",
    "条件函数返回值2": "目标节点2",
}
```

### 当前代码

```python
{
    END: END,  # "END" → END 节点
    ACT: ACT,  # "ACT" → ACT 节点
}
```

**等价写法**：
```python
{
    "END": END,  # 字符串键
    "ACT": ACT,
}
```

**或者**：
```python
{
    END: "__end__",  # 使用字符串常量
    ACT: "act",
}
```

### 更复杂的示例

```python
def route_question(state):
    question = state["question"]
    if "天气" in question:
        return "weather"
    elif "计算" in question:
        return "calculator"
    else:
        return "general"

flow.add_conditional_edges(
    "router",
    route_question,
    {
        "weather": "weather_node",
        "calculator": "calc_node",
        "general": "general_node",
    }
)
```

---

## 🔧 与其他边的对比

### 1. 普通边（add_edge）

```python
flow.add_edge(ACT, AGENT_REASON)
```

**特点**：
- 固定路径
- 无条件判断
- 总是执行

### 2. 条件边（add_conditional_edges）

```python
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {END: END, ACT: ACT}
)
```

**特点**：
- 动态路径
- 根据条件判断
- 智能路由

### 3. 入口点（set_entry_point）

```python
flow.set_entry_point(AGENT_REASON)
```

**特点**：
- 定义起始节点
- 只执行一次
- 工作流入口

---

## 💡 实际应用示例

### 完整工作流

```python
# 1. 创建图
flow = StateGraph(MessagesState)

# 2. 添加节点
flow.add_node(AGENT_REASON, run_agent_reasoning_engine)
flow.add_node(ACT, tool_node)

# 3. 设置入口点
flow.set_entry_point(AGENT_REASON)

# 4. 添加条件边（关键！）
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {
        END: END,  # 不需要工具 → 结束
        ACT: ACT,  # 需要工具 → 执行工具
    },
)

# 5. 添加普通边
flow.add_edge(ACT, AGENT_REASON)  # 工具执行后 → 继续推理
```

### 执行流程

```
开始
  ↓
agent_reason
  ↓
should_continue() 判断
  ├─→ 没有工具调用 → END (结束) ✅
  └─→ 有工具调用 → ACT
                      ↓
                  执行工具
                      ↓
                  返回 agent_reason (循环)
                      ↓
                  再次判断...
```

---

## 🎓 关键概念总结

### 条件边的作用

1. **智能路由**：根据状态决定下一步
2. **动态控制流**：不是固定路径
3. **提高效率**：避免不必要的操作

### 三个参数

1. **source_node**：从哪个节点出发
2. **condition_func**：判断函数（返回路由键）
3. **path_map**：路由键到目标节点的映射

### 判断函数的要求

- 接收 `state` 作为参数
- 返回一个字符串（路由键）
- 返回值必须在 `path_map` 中存在

---

## 📝 常见错误

### 错误 1：返回值不在 path_map 中

```python
def should_continue(state):
    return "UNKNOWN"  # ❌ 不在 path_map 中

flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {END: END, ACT: ACT}  # 没有 "UNKNOWN"
)
# 会抛出 KeyError
```

### 错误 2：忘记添加对应的边

```python
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {END: END, ACT: ACT}
)
# 如果路由到 ACT，但没有添加 ACT 节点，会报错
```

### 正确做法

```python
# 1. 先添加所有节点
flow.add_node(AGENT_REASON, ...)
flow.add_node(ACT, ...)

# 2. 再添加条件边
flow.add_conditional_edges(
    AGENT_REASON,
    should_continue,
    {END: END, ACT: ACT}
)
```

---

## 🔗 相关概念

- **条件边**：`add_conditional_edges`
- **普通边**：`add_edge`
- **入口点**：`set_entry_point`
- **状态图**：`StateGraph`

---

## 📝 总结

这三行代码的作用是：

1. **从 `AGENT_REASON` 节点出发**
2. **调用 `should_continue` 函数判断**
3. **根据返回值路由**：
   - `"END"` → 结束工作流
   - `"ACT"` → 执行工具节点

**核心价值**：实现**智能路由**，根据 LLM 是否需要工具来决定下一步，避免不必要的操作，提高效率！


可能需要重新设计一下架构，1.subagent以及skills连接符还是改为短横线"-"，因为所有的skills都是这样写的，      
  方便扩展。2.subagent的上下文独立，不继承主agent的上下文，subagent之间的上下文相互独立；3._agent.md中定     
  义的skills在启动此subagent是加载到此subagent的上下文中，主agent拥有所有subagent以及skills的调配权；4.      
  由于目前不开放系统级的bash命令，所以需要在executor中模拟一个能执行python脚本的方法```bash                  
  python src/registry/skills/tool_matcher/scripts/match.py \                                                 
  --query "compare two groups" \                                                                             
  --top-k 5                                                                                                  
  ```；5.目前只实现了简单的任务分配，需要考虑复杂的任务拆解，比如可能会调用多个skills、多个agent的情况，     
  中间还可能需要对用户进行追问等等。请给我一个完整可落地的执行方案，可以参考claude code的技术agent_cente     
  r/draft/claudecode_tech/use_skills.md和agent_center/draft/claudecode_tech/use_subagent.md                  
                                                                                                             
● 让我先阅读参考文件，然后设计方案：                                                                         
                                                                                                             
● Read 3 files (ctrl+o to expand)                                                                            
                                                                                                             
● 让我探索当前的代码结构，了解需要修改的部分：                                                               
                                                                                                             
● Explore(探索代码结构分析架构重构)                                                                          
  ⎿  Done (21 tool uses · 0 tokens · 1m 28s)                                                                 
                                                                                                             
● 根据参考文档和你的需求，让我创建一个完整的架构重构方案：                                                   
                                                                                                             
● Updated plan                                                                                               
  ⎿  /plan to preview                                                                                        
                                                                                                             
● 计划已创建完成。主要内容包括：                                                                             
                                                                                                             
  核心设计                                                                                                   
                                                                                                             
  1. 命名统一：所有 skills 和 agents 改用短横线命名（如 tool-matcher, routing-agent）                        
  2. 上下文隔离：通过 ExecutionContext 类实现，subagent 不继承主 agent 对话历史                              
  3. Skills 预加载：agent 启动时将其配置的 skills 完整内容加载到上下文                                       
  4. 调用协议：统一的 JSON 格式用于调用 skills、subagents 和追问                                             
  5. Python 脚本执行：在 executor 中模拟执行 python scripts/xxx.py --arg value 格式                          
  6. 复杂任务支持：多步骤任务、迭代对话、结果聚合                                                            
                                                                                                             
─────────────────────────────────────────────────────────────────────────────────────────────────────────────
 Ready to code?                                                                                              
                                                                                                             
 Here is Claude's plan:                                                                                      
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Agent Center 架构重构方案                                                                                   
                                                                                                             
 目标                                                                                                        
                                                                                                             
 参考 Claude Code 的 agent_skills 开放标准，重构当前架构以支持：                                             
 1. 统一使用短横线 "-" 命名（skills 和 subagents）                                                           
 2. Subagent 上下文独立（不继承主 agent 对话历史）                                                           
 3. Skills 预加载到 subagent 上下文                                                                          
 4. 主 agent 拥有所有 subagents 和 skills 的调配权                                                           
 5. Executor 中模拟 Python 脚本执行                                                                          
 6. 支持复杂任务拆解（多 skills、多 agents、追问、迭代）                                                     
                                                                                                             
 ---                                                                                                         
 架构设计                                                                                                    
                                                                                                             
 1. 命名规范变更                                                                                             
                                                                                                             
 当前 → 目标                                                                                                 
 ┌────────┬─────────────────────────────────┬─────────────────────────────────┐                              
 │  类型  │            当前命名             │            目标命名             │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ semantic_search                 │ semantic-search                 │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ tool_matcher                    │ tool-matcher                    │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ data_analyzer                   │ data-analyzer                   │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ literature_matcher              │ literature-matcher              │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ pipeline_decision               │ pipeline-decision               │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Skills │ question_generator              │ question-generator              │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Agents │ routing_agent                   │ routing-agent                   │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Agents │ pipeline_agent                  │ pipeline-agent                  │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Agents │ data_analyst_agent              │ data-analyst-agent              │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Agents │ conversation_orchestrator_agent │ conversation-orchestrator-agent │                              
 ├────────┼─────────────────────────────────┼─────────────────────────────────┤                              
 │ Agents │ general_purpose_agent           │ general-purpose-agent           │                              
 └────────┴─────────────────────────────────┴─────────────────────────────────┘                              
 2. 目录结构重组织                                                                                           
                                                                                                             
 src/registry/                                                                                               
 ├── agents/                    # Subagents 定义                                                             
 │   ├── routing-agent.md                                                                                    
 │   ├── pipeline-agent.md                                                                                   
 │   ├── data-analyst-agent.md                                                                               
 │   ├── conversation-orchestrator-agent.md                                                                  
 │   └── general-purpose-agent.md                                                                            
 │                                                                                                           
 ├── skills/                    # Skills 定义                                                                
 │   ├── semantic-search/                                                                                    
 │   │   ├── SKILL.md                                                                                        
 │   │   └── scripts/                                                                                        
 │   │       └── search.py                                                                                   
 │   ├── tool-matcher/                                                                                       
 │   │   ├── SKILL.md                                                                                        
 │   │   └── scripts/                                                                                        
 │   │       └── match.py                                                                                    
 │   ├── data-analyzer/                                                                                      
 │   │   ├── SKILL.md                                                                                        
 │   │   └── scripts/                                                                                        
 │   │       └── analyze.py                                                                                  
 │   ├── literature-matcher/                                                                                 
 │   │   ├── SKILL.md                                                                                        
 │   │   └── scripts/                                                                                        
 │       └── match.py                                                                                        
 │   ├── pipeline-decision/                                                                                  
 │   │   ├── SKILL.md                                                                                        
 │   │   └── scripts/                                                                                        
 │   │       └── decide.py                                                                                   
 │   └── question-generator/                                                                                 
 │       ├── SKILL.md                                                                                        
 │       └── scripts/                                                                                        
 │           └── generate.py                                                                                 
                                                                                                             
 3. Agent/Skill Frontmatter 规范                                                                             
                                                                                                             
 Agent Frontmatter                                                                                           
                                                                                                             
 ---                                                                                                         
 name: agent-name                                                                                            
 description: Agent 描述                                                                                     
 tools: [Read, Write, Grep]                                                                                  
 model: inherit                                                                                              
 max_turns: 10                                                                                               
 skills: [skill-1, skill-2]  # 预加载的 skills                                                               
 subagents: [sub-agent-1, sub-agent-2]  # 可调用的 subagents                                                 
 ---                                                                                                         
                                                                                                             
 Skill Frontmatter                                                                                           
                                                                                                             
 ---                                                                                                         
 name: skill-name                                                                                            
 description: Skill 描述                                                                                     
 allowed-tools: [Read, Grep]                                                                                 
 context: inline  # inline | fork                                                                            
 agent: general-purpose  # 仅当 context: fork 时有效                                                         
 ---                                                                                                         
                                                                                                             
 4. 执行流程设计                                                                                             
                                                                                                             
 ┌─────────────────────────────────────────────────────────────┐                                             
 │                     主 Agent 执行                             │                                           
 │  (继承用户对话历史，拥有所有 subagents 和 skills 调配权)         │                                        
 └──────────────────────────┬──────────────────────────────┘                                                 
                            │                                                                                
            ┌───────────────┼───────────────┐                                                                
            │               │               │                                                                
            ▼               ▼               ▼                                                                
     ┌───────────┐   ┌─────────┐   ┌──────────────┐                                                          
     │ 调用 Skill │   │调用Subagent │  │ 追问用户     │                                                      
     │           │   │           │  │              │                                                         
     ▼           ▼   ▼           ▼  ▼              │                                                         
 ┌─────────────────────────────────────────────────────────┐                                                 
 │  Skill 执行（隔离）         Subagent 执行（隔离）           │                                             
 │  - 预加载 skill 内容     - 独立上下文                   │                                                 
 │  - 模拟 Python 脚本       - 预加载 skills                 │                                               
 │  - 返回结果             - 返回结果                       │                                                
 └─────────────────────────────────────────────────────────┘                                                 
                            │                                                                                
                            ▼                                                                                
 ┌─────────────────────────────────────────────────────────┐                                                 
 │                     结果聚合                               │                                              
 │  - 收集所有结果                                             │                                             
 │  - 综合决策                                                 │                                             
 │  - 追问/迭代                                                 │                                            
 └─────────────────────────────────────────────────────────┘                                                 
                                                                                                             
 5. 调用协议设计                                                                                             
                                                                                                             
 Skill 调用格式                                                                                              
                                                                                                             
 {                                                                                                           
   "action": "use_skill",                                                                                    
   "skill": "tool-matcher",                                                                                  
   "input": {"query": "compare two groups"}                                                                  
 }                                                                                                           
                                                                                                             
 Subagent 调用格式                                                                                           
                                                                                                             
 {                                                                                                           
   "action": "delegate_to_agent",                                                                            
   "agent": "pipeline-agent",                                                                                
   "context": "fork",  // inherit | fork                                                                     
   "input": {"query": "..."}                                                                                 
 }                                                                                                           
                                                                                                             
 用户追问格式                                                                                                
                                                                                                             
 {                                                                                                           
   "action": "ask_user",                                                                                     
   "question": "请问样本量是多少？",                                                                         
   "reasoning": "需要样本量来选择合适的统计方法"                                                             
 }                                                                                                           
                                                                                                             
 多步骤任务格式                                                                                              
                                                                                                             
 {                                                                                                           
   "action": "multi_step",                                                                                   
   "steps": [                                                                                                
     {"action": "use_skill", "skill": "data-analyzer"},                                                      
     {"action": "use_skill", "skill": "literature-matcher"},                                                 
     {"action": "ask_user", "question": "是否需要生成代码？"}                                                
   ]                                                                                                         
 }                                                                                                           
                                                                                                             
 ---                                                                                                         
 实施步骤                                                                                                    
                                                                                                             
 Phase 1: 命名规范化                                                                                         
                                                                                                             
 1.1 重命名 Skills 目录                                                                                      
                                                                                                             
 mv semantic_search semantic-search                                                                          
 mv tool_matcher tool-matcher                                                                                
 mv data_analyzer data-analyzer                                                                              
 mv literature_matcher literature-matcher                                                                    
 mv pipeline_decision pipeline-decision                                                                      
 mv question_generator question-generator                                                                    
                                                                                                             
 1.2 重命名 Agents 文件                                                                                      
                                                                                                             
 mv routing_agent.md routing-agent.md                                                                        
 mv pipeline_agent.md pipeline-agent.md                                                                      
 mv data_analyst_agent.md data-analyst-agent.md                                                              
 mv conversation_orchestrator_agent.md conversation-orchestrator-agent.md                                    
 mv general_purpose_agent.md general-purpose-agent.md                                                        
                                                                                                             
 1.3 更新配置引用                                                                                            
                                                                                                             
 - config/agents.yaml 中的 agent 名称和 skills                                                               
 - config/skills.yaml 中的 skill 名称                                                                        
 - 各 agent 的 skills 引用                                                                                   
 - executor.py 中的引用                                                                                      
                                                                                                             
 Phase 2: Executor 重构                                                                                      
                                                                                                             
 2.1 新增上下文隔离机制                                                                                      
                                                                                                             
 创建 ExecutionContext 类：                                                                                  
 class ExecutionContext:                                                                                     
     def __init__(self, parent=None, inherit_history=True):                                                  
         self.parent = parent                                                                                
         self.conversation_history = [] if not inherit_history else (parent.conversation_history if parent   
 else [])                                                                                                    
         self.isolated = not inherit_history                                                                 
                                                                                                             
 2.2 新增 Python 脚本执行器                                                                                  
                                                                                                             
 创建 PythonScriptExecutor 类：                                                                              
 class PythonScriptExecutor:                                                                                 
     def execute_script(self, script_path: str, args: Dict) -> Dict:                                         
         # 解析脚本路径和参数                                                                                
         # 使用 subprocess 在隔离环境中执行                                                                  
         # 返回标准输出和错误                                                                                
                                                                                                             
 2.3 新增任务解析器                                                                                          
                                                                                                             
 创建 TaskParser 类：                                                                                        
 class TaskParser:                                                                                           
     def parse_response(self, response: str) -> List[Dict]:                                                  
         # 解析技能调用                                                                                      
         # 解析 subagent 调用                                                                                
         # 解析用户追问                                                                                      
         # 解析多步骤任务                                                                                    
                                                                                                             
 2.4 新增执行编排器                                                                                          
                                                                                                             
 创建 ExecutionOrchestrator 类：                                                                             
 class ExecutionOrchestrator:                                                                                
     def execute_with_context(self, agent_name: str, input_data: Dict, context: ExecutionContext):           
         # 创建隔离上下文                                                                                    
         # 执行 agent                                                                                        
         # 解析任务链                                                                                        
         # 执行 skills/subagents                                                                             
         # 聚合结果                                                                                          
                                                                                                             
 Phase 3: Agent/Skill 配置更新                                                                               
                                                                                                             
 3.1 更新所有 Skill 文件                                                                                     
                                                                                                             
 - 将 SKILL.md 中的引用从下划线改为短横线                                                                    
 - 更新 __init__.py 中的导入路径                                                                             
                                                                                                             
 3.2 更新所有 Agent 文件                                                                                     
                                                                                                             
 - 更新 skills 列表使用短横线                                                                                
 - 添加 subagents 列表（如需要）                                                                             
 - 添加调用协议说明                                                                                          
                                                                                                             
 3.3 更新配置文件                                                                                            
                                                                                                             
 - config/agents.yaml                                                                                        
 - config/skills.yaml                                                                                        
                                                                                                             
 Phase 4: 复杂任务支持                                                                                       
                                                                                                             
 4.1 任务拆解 Prompt 模板                                                                                    
                                                                                                             
 在 agent prompt 中添加任务拆解指南：                                                                        
 ## Task Decomposition                                                                                       
                                                                                                             
 For complex tasks, decompose into multiple steps:                                                           
 1. Identify required skills and subagents                                                                   
 2. Determine execution order                                                                                
 3. Plan for intermediate user confirmations                                                                 
 4. Aggregate results                                                                                        
                                                                                                             
 Output format:                                                                                              
 ```json                                                                                                     
 {                                                                                                           
   "plan": [...],                                                                                            
   "estimated_steps": N                                                                                      
 }                                                                                                           
                                                                                                             
 #### 4.2 迭代对话支持                                                                                       
 ```python                                                                                                   
 class ConversationalLoop:                                                                                   
     def execute_with_iterations(self, max_iterations: int):                                                 
         for i in range(max_iterations):                                                                     
             result = self.execute_agent(...)                                                                
             if result.requires_user_input():                                                                
                 # 等待用户输入后继续                                                                        
                 break                                                                                       
                                                                                                             
 Phase 5: 验证测试                                                                                           
                                                                                                             
 5.1 单元测试                                                                                                
                                                                                                             
 - 上下文隔离测试                                                                                            
 - Skill 执行测试                                                                                            
 - Subagent 调用测试                                                                                         
 - Python 脚本执行测试                                                                                       
                                                                                                             
 5.2 集成测试                                                                                                
                                                                                                             
 - 完整任务链测试                                                                                            
 - 多 skill 调用测试                                                                                         
 - 多 agent 协作测试                                                                                         
 - 追问流程测试                                                                                              
                                                                                                             
 ---                                                                                                         
 关键文件清单                                                                                                
                                                                                                             
 需要重命名的文件                                                                                            
                                                                                                             
 1. src/registry/skills/semantic_search/ → semantic-search/                                                  
 2. src/registry/skills/tool_matcher/ → tool-matcher/                                                        
 3. src/registry/skills/data_analyzer/ → data-analyzer/                                                      
 4. src/registry/skills/literature_matcher/ → literature-matcher/                                            
 5. src/registry/skills/pipeline_decision/ → pipeline-decision/                                              
 6. src/registry/skills/question_generator/ → question-generator/                                            
 7. src/registry/agents/routing_agent.md → routing-agent.md                                                  
 8. src/registry/agents/pipeline_agent.md → pipeline-agent.md                                                
 9. src/registry/agents/data_analyst_agent.md → data-analyst-agent.md                                        
 10. src/registry/agents/conversation_orchestrator_agent.md → conversation-orchestrator-agent.md             
 11. src/registry/agents/general_purpose_agent.md → general-purpose-agent.md                                 
                                                                                                             
 需要修改的代码文件                                                                                          
                                                                                                             
 1. src/core/executor.py - 核心执行引擎                                                                      
 2. src/core/agent_manager.py - agent 管理                                                                   
 3. src/core/skill_manager.py - skill 管理                                                                   
 4. src/api/routes.py - API 路由                                                                             
 5. config/agents.yaml - agent 配置                                                                          
 6. config/skills.yaml - skill 配置                                                                          
                                                                                                             
 需要新增的类                                                                                                
                                                                                                             
 1. ExecutionContext - 上下文隔离                                                                            
 2. PythonScriptExecutor - Python 脚本执行                                                                   
 3. TaskParser - 任务解析                                                                                    
 4. ExecutionOrchestrator - 执行编排                                                                         
 5. ConversationalLoop - 迭代对话                                                                            
                                                                                                             
 需要更新的 SKILL.md                                                                                         
                                                                                                             
 所有 skills 的 SKILL.md 文件，更新：                                                                        
 - 目录引用                                                                                                  
 - Python 脚本引用                                                                                           
 - Skill 之间的相互引用                                                                                      
                                                                                                             
 ---                                                                                                         
 预期效果                                                                                                    
                                                                                                             
 执行流程示例                                                                                                
                                                                                                             
 用户问题: "我有两组数据，想比较差异，应该用什么方法？"                                                      
                                                                                                             
 routing-agent → general-purpose-agent                                                                       
   ↓ (分析：需要先了解数据特征)                                                                              
 general-purpose-agent → skill: data-analyzer                                                                
   ↓ (执行：获取数据特征)                                                                                    
 general-purpose-agent → skill: tool-matcher                                                                 
   ↓ (执行：匹配统计工具)                                                                                    
 general-purpose-agent → ask_user                                                                            
   ↓ "请问两组数据是独立的还是配对的？"                                                                      
 用户: "独立的"                                                                                              
 general-purpose-agent → skill: tool-matcher                                                                 
   ↓ (重新匹配：独立样本检验)                                                                                
 general-purpose-agent → 返回结果                                                                            
                                                                                                             
 复杂任务示例                                                                                                
                                                                                                             
 用户需求: "帮我分析这个临床试验数据并生成分析报告"                                                          
                                                                                                             
 routing-agent → pipeline-agent                                                                              
   ↓ (任务：数据分析和报告生成)                                                                              
 pipeline-agent (fork context)                                                                               
   ↓                                                                                                         
 pipeline-agent → skill: data-analyzer (预加载)                                                              
 pipeline-agent → skill: literature-matcher (预加载)                                                         
 pipeline-agent → ask_user "需要生成代码吗？"                                                                
   ↓ 用户确认                                                                                                
 pipeline-agent → subagent: data-analyst-agent                                                               
   ↓                                                                                                         
 data-analyst-agent (fork context)                                                                           
 data-analyst-agent → 生成代码                                                                               
 data-analyst-agent → 返回结果                                                                               
   ↓                                                                                                         
 pipeline-agent → 聚合结果 → 返回给用户                                                                      
                                                                                                             
 ---                                                                                                         
 风险评估                                                                                                    
 ┌──────────────────────────────┬──────┬────────────────────────┐                                            
 │             风险             │ 影响 │        缓解措施        │                                            
 ├──────────────────────────────┼──────┼────────────────────────┤                                            
 │ 大规模重命名可能破坏现有引用 │ 高   │ 使用自动化脚本批量替换 │                                            
 ├──────────────────────────────┼──────┼────────────────────────┤                                            
 │ 上下文隔离可能丢失重要信息   │ 中   │ 提供 inherit 选项      │                                            
 ├──────────────────────────────┼──────┼────────────────────────┤                                            
 │ 复杂任务流程难以调试         │ 中   │ 详细的日志记录         │                                            
 ├──────────────────────────────┼──────┼────────────────────────┤                                            
 │ Python 脚本执行安全性        │ 低   │ 沙箱环境执行           │                                            
 ├──────────────────────────────┼──────┼────────────────────────┤                                            
 │ 性能影响                     │ 低   │ 异步执行优化           │                                            
 └──────────────────────────────┴──────┴────────────────────────┘                                            
 ---                                                                                                         
 时间估算                                                                                                    
 ┌───────┬───────────────┬──────────┐                                                                        
 │ Phase │     任务      │ 预计时间 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 1     │ 命名规范化    │ 1-2 小时 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 2     │ Executor 重构 │ 4-6 小时 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 3     │ 配置更新      │ 2-3 小时 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 4     │ 复杂任务支持  │ 3-4 小时 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 5     │ 测试验证      │ 2-3 小时 │                                                                        
 ├───────┼───────────────┼──────────┤                                                                        
 │ 总计  │ 12-18 小时    │          │                                                                        
 └───────┴───────────────┴──────────┘                                                                        
 ---                                                                                                         
 后续优化                                                                                                    
                                                                                                             
 1. 性能优化: 异步并行执行 skills/subagents                                                                  
 2. 缓存机制: skill 结果缓存                                                                                 
 3. 监控面板: 任务执行可视化                                                                                 
 4. 插件系统: 支持第三方 skills/subagents 
window.OEP_GUIDE_LOCALE = {
  "labels": {
    "OEP Metadata — Workflow field guide": "OEP Metadata｜流程详解",
    "Skip to walkthrough": "跳到流程说明",
    "WORKFLOW FIELD GUIDE": "工作流程详解",
    "Explore a workflow": "选择要了解的功能",
    "Read the README ↗": "阅读 README ↗",
    "Self-contained · works offline": "独立页面 · 无需联网",
    "Documentation / How it works": "使用文档 / 工作原理",
    "Who does what ↓": "各自负责什么 ↓",
    "One Skill. Five workflows.": "一个 Skill，五项功能。",
    "Follow the work.": "跟着流程走，",
    "See every handoff.": "看懂每一步。",
    "Walk through the evidence, decisions and files behind each operation. Choose a workflow, then move through it one step at a time.": "从输入证据、程序检查到 AI 判断和结果文件，逐步了解每项操作是如何完成的。选择一项功能，即可开始。",
    "31 explained steps": "31 个说明环节",
    "Code + host AI + your decisions": "AI 主导 + 工具检查 + 你的必要决策",
    "Illustrative guide · no execution": "交互说明 · 不执行真实任务",
    "Play steps": "自动播放",
    "Pause": "暂停",
    "← Back": "← 上一步",
    "Next step →": "下一步 →",
    "Try this prompt in your agent": "在 Agent 中试试这个 prompt",
    "Copy prompt": "复制 prompt",
    "Copied ✓": "已复制 ✓",
    "Select prompt to copy": "请选中文本复制",
    "Prompts use Codex syntax. In Claude Code, use": "示例使用 Codex 调用语法。在 Claude Code 中请使用",
    ". Command fragments above abbreviate the Python helper invocation; see the README for setup.": "。上方命令为 Python 工具的简写，完整调用方式见 README。",
    "Read the complete walkthrough": "展开阅读完整流程",
    "A division of responsibilities": "明确各自的职责",
    "You set the scope.": "你来确定任务范围。",
    "Choose the inputs and target, supply missing facts, inspect the results, and authorize a specific remote action when needed. A local draft does not authorize upload.": "选择输入和目标，补充缺失事实，检查结果，并在需要时授权具体的远程操作。生成本地草稿不代表授权上传。",
    "Python binds and checks.": "Python 负责绑定与校验。",
    "Read the outcome, not just the badge.": "查看真实结果，而不只看“通过”。",
    "OEP Metadata / Interactive companion to the README": "OEP Metadata / README 配套交互说明",
    "Skill entry": "Skill 入口",
    "Setup & commands": "安装与命令",
    "This interactive walkthrough needs JavaScript. Open the README or the linked Skill entry for the written instructions.": "交互说明需要 JavaScript；也可阅读 README 或 Skill 入口文档。",
    "Input / what arrives": "输入 / 从哪里开始",
    "Output / what leaves": "输出 / 这步得到什么",
    "ILLUSTRATIVE COMMAND OR ARTIFACT": "命令或产物示例",
    "BEFORE YOU CONTINUE": "继续之前，请注意",
    "STEP": "步骤",
    "Workflow": "功能",
    "Inputs:": "输入：",
    "Outputs:": "输出：",
    "Gate:": "检查条件：",
    "Step": "步骤",
    "of": "/",
    "Workflow navigation": "功能导航",
    "Choose a workflow": "选择功能",
    "Workflow steps": "流程步骤",
    "Selected step": "当前步骤",
    "Walkthrough position": "当前进度",
    "AI input and output": "这一环节给 AI 什么，它会返回什么",
    "Illustrative fixture notice": "以下为两列两行合成数据的完整示例。输入来自真实工具调用，示例候选按契约编写并通过接收检查；这是静态演示，不是现场模型回答。",
    "Injected error notice": "组合流程故意在生成结果中放入错误标题，演示独立评审如何发现并修复语义错误。程序接收通过并不证明语义正确。",
    "Prompt assembly notice": "这里的完整示例由文档整理：展示宿主 AI 的任务要求、角色规则、当时的输入及候选输出。运行工具只返回数据与检查，不自动拼 prompt 或安排下一角色。",
    "Full AI prompt": "查看完整 AI 输入提示词与材料",
    "Full AI output": "查看完整 AI 候选输出示例",
    "Copy all": "复制全部",
    "Input material": "完整输入材料",
    "Candidate file": "完整候选文件",
    "Characters": "字符",
    "Example source": "示例数据：power.csv（year、power 两列，两行）；背景说明声明容量单位为 GW。",
    "Re-review notice": "这是应用修复补丁后，由全新 Reviewer 接收的任务。它的哈希、当前标题和输入上下文都已更新。",
    "No AI execution notice": "本步骤不单独展示语义候选 JSON；宿主 AI 仍负责决定下一步、调用工具和解释结果。程序只执行明确调用的确定性操作。",
    "Full original prompt": "查看完整提示词 · 英文原版",
    "Command authorship": "谁编写命令，谁执行处理？",
    "Command authorship explanation": "通常由宿主 AI / 协调 Agent 根据你的要求和当前运行状态编写、调用命令；也可以由你手工输入。终端启动 Python 工具后，数据读取、统计、快照和校验由程序执行。页面的角色标签指主要处理方，不代表命令一定由人编写。",
    "Command example prompt": "给宿主 AI 的请求：读取 examples/capacity.csv 和 examples/capacity-source.md，创建生成任务 runs/draft-01，先收集资料，不上传。请编写并调用对应工具命令。",
    "Command example output": "AI 可能编写并调用的完整命令",
    "Review results / read by category": "评审结果 / 按类别阅读",
    "A reviewed field is not necessarily a problem.": "被评审的字段，不一定都有问题。",
    "Start with conflicts and unresolved questions. Evidence-supported and not-applicable decisions are recorded separately so they do not inflate the issue list.": "先看冲突问题和待确认事项。证据支持与不适用的判断单独记录，避免把已确认项也当成问题。",
    "Illustrative example: one field in each category. Actual counts are computed from the review, not from this demonstration.": "以下是每类一个字段的说明示例。真实报告中的数量由评审结果计算，不使用这些示例数字。",
    "Conflicts - inspect or correct": "冲突问题：需要核查或修改",
    "Evidence contradicts the current value. Inspect the finding, evidence and proposed replacement.": "现有值与证据冲突。需要查看问题说明、依据和建议替换值。",
    "Example: the value is GW, while the source declares TWh. A proposed replacement is TWh.": "示例：当前值为 GW，但来源明确写的是 TWh，因此建议替换为 TWh。",
    "Unresolved - needs evidence": "待确认事项：需要补充证据",
    "There is not enough evidence to confirm the value. This is not a confirmed error; provide a declaration or retain uncertainty.": "证据不足，暂时无法确认。它不是已经确认的错误；应补充声明，或保留未知状态。",
    "Example: no nulls were observed, but no non-null constraint was declared.": "示例：数据中没有观察到空值，但没有材料声明该列禁止空值。",
    "Evidence-supported - expand to inspect": "证据支持：展开查看已确认项",
    "Available evidence supports the current value within the reviewed scope. Usually no action is needed.": "当前证据在本次评审范围内支持该值，通常不需要处理。",
    "Example: the alpha-3 description agrees with the codebook and observed country codes.": "示例：alpha-3 的字段说明与数据字典、实际三位国家码一致。",
    "Not applicable - expand to inspect": "不适用：展开查看理由",
    "The concept does not apply, with a stated reason. Missing evidence alone does not establish inapplicability.": "有理由认定该项不适用。仅仅没有找到信息，不能据此认定不适用。",
    "Example: an authoritative declaration confirms there was no grant funding, so a grant number is not applicable.": "示例：权威材料明确声明未接受项目资助，因此资助编号不适用。",
    "The AI drives the task. Tools check its work.": "AI 推进整个任务，工具检查结果。",
    "The host AI leads.": "宿主 AI 负责推进。",
    "The AI reads, asks, writes, checks, repairs and decides when to deliver. It coordinates any fresh independent Reviewer; Python tools do not call a model or choose roles.": "AI 阅读、提问、编写、检查、修正并决定交付，按需协调全新独立 Reviewer。Python 工具不调用模型，也不选择角色。",
    "Snapshots, hashes and validation gates make accepted results traceable. Tool responses inform the AI; they do not schedule a workflow or prove factual correctness.": "快照、哈希与校验约束保证过程可追溯。工具结果供 AI 判断，不编排工作流，也不能证明事实正确。",
    "Generated metadata must pass checks before delivery. If honest completion is impossible, the AI stops with a concise explanation. OEP uploads need verified readback; production writes remain unverified by this project.": "生成的 metadata 交付前必须通过检查。无法如实完成时，AI 停止并简要解释。OEP 上传需回读确认；本项目尚未验证生产环境写入。",
    "These are decision categories, not severity scores. Program checks appear directly in review.md. Read summary.md for grouped actions; there is no separate validation or question JSON to interpret.": "这是判断类别，不是严重程度评分。程序检查直接写在 review.md 中，合并后的行动事项看 summary.md；不再另出 validation 或 question JSON。",
    "Core tool path": "核心工具路径",
    "Tools used only when needed": "按需工具，不必每次都执行",
    "Returned views and evidence": "返回视图与证据完整性",
    "Why collect is smaller, and which checks remain": "collect 为什么变小了，哪些资料与校验还在",
    "The same four-row example was measured in three representations. These are JSON response sizes, not task-speed guarantees.": "以下是同一份四行示例的三种返回大小。数字指 JSON 返回量，不是任务耗时或普遍提速承诺。",
    "Full response, indented": "完整返回，带缩进",
    "Identical information, compact JSON": "信息不变，仅去掉缩进",
    "Generation view with deduplication": "生成视图，去重并按任务精简",
    "One copy of the evidence": "同一份证据只传一次",
    "Metadata, profile, background text, constraints, snapshots and hashes are preserved. Duplicate profile evidence points to context.profile; review-only lists and internal guards remain available in the full context.": "metadata、profile、背景正文、约束、快照和哈希都保留。重复的 profile 证据引用 context.profile；评审专用列表与内部保护结构仍在完整 context 中。",
    "Acceptance and delivery still validate": "接收和交付仍有两道校验",
    "record-metadata checks the document, evidence and bindings before acceptance. deliver checks again. A separate check is available for diagnostics; independent combined review still needs a current conflict-free assessment.": "record-metadata 在接收前检查文档、依据和绑定，deliver 交付前再次检查。独立 check 可按需用于诊断；组合任务仍需当前版本的独立评审且无冲突。",
    "The AI can query a field with schema --pointer or inspect --view full when needed. Unknown facts remain unknown. Mechanical validity and these small tests do not prove factual correctness for every dataset.": "AI 可用 schema --pointer 查询具体字段，必要时用 inspect --view full 查看完整内容。缺乏依据的事实仍保持未知。程序合法和这些小样本测试不能证明所有数据集的事实必然正确。",
    "A correction and a new review are separate steps": "修正副本与重新评审，是两个步骤",
    "Illustrative example; these counts are not a live run.": "以下为示意，数量不是当前任务的实时结果。",
    "Original review.md": "原文件的 review.md",
    "1 conflict · 1 unknown": "1 个冲突 · 1 个待确认项",
    "Documented unit corrected": "已按来源修正单位",
    "New review of the suggested copy": "对建议副本新建一次评审",
    "0 conflicts · 1 unknown": "0 个冲突 · 1 个待确认项",
    "The old report keeps its original findings. A fresh review can clear the corrected conflict; an unsupported license or date still needs evidence.": "旧报告保留对原文件的判断。重新评审可以确认冲突已经修正；缺乏依据的许可证或日期仍需补充证据。",
    "Select a tool to open its explanation. Counts cover core Skill commands only; AI file operations and model requests are separate. Detailed stages also include human and AI work.": "点击工具可跳到对应说明。数字只统计 Skill 的核心业务命令；AI 读写文件和模型请求另计。下方详细环节也包含人和 AI 的工作。",
    "Full localized prompt": "查看完整提示词 · 中文阅读版",
    "Localized prompt notice": "中文阅读版说明同一任务要求；metadata、哈希、schema 与原始证据保留英文原文。实际执行以 Skill 和当前工具契约为准。",
    "Language": "语言",
    "Chinese": "中文",
    "Deutsch": "Deutsch",
    "English": "English"
  },
  "flows": [
    {
      "name": "生成元数据",
      "short": "收集 → 检查接收 → 复查交付",
      "description": "AI 阅读资料、决定提问和工具调用，修正程序错误，最后交付 metadata 和简要说明。",
      "prompt": "用 $oep-metadata 为 examples/capacity.csv 生成元数据，背景资料是 examples/capacity-source.md，保存到 runs/draft-01。交付前修正程序校验错误，缺乏依据的事实保留未知，简要说明我还需要确认的内容。不独立评审，不上传。",
      "steps": [
        {
          "actor": "你 → 宿主 AI",
          "title": "说明目标与资料",
          "body": "给 AI 一个数据集、相关文档及用途。宿主 AI 负责选择工具、编写和执行命令，你只需提出任务。",
          "inputs": "数据集、背景资料、预期用途",
          "outputs": "明确范围的 AI 任务",
          "gate": "支持多份背景资料；一个生成任务对应一份数据集元数据。"
        },
        {
          "actor": "宿主 AI → Python",
          "title": "收集证据，观察结构",
          "body": "AI 调用 collect。程序冻结输入，返回当前生成视图：一份 profile、证据、哈希和中性模板。直接复用这份结果，无变化时再次 inspect 只会重复内容。",
          "inputs": "一份数据 + 多个 background 参数",
          "outputs": "工具返回模板、profile、证据 ID 与哈希",
          "gate": "中性模板不是 AI 答案；没观察到空值也不能证明字段禁止为空。"
        },
        {
          "actor": "宿主 AI ↔ 你",
          "title": "先读材料，再问关键问题",
          "body": "AI 看完资料，合并相关缺口，只询问会影响结果的关键事实。你回答后，AI 把声明登记为证据并刷新上下文。",
          "inputs": "资料证据与任务用途",
          "outputs": "必要的澄清，或明确保留未知",
          "gate": "不会把每个空白的可选字段都变成一个问题。"
        },
        {
          "actor": "宿主 AI",
          "title": "编写一个候选包",
          "body": "AI 对照证据编写 metadata 和逐字段依据。一个候选文件包含 input_hash、metadata 和 provenance，由接收工具检查后再保存。",
          "inputs": "当前生成视图与原始资料",
          "outputs": "一份 metadata 候选包",
          "gate": "无需再复制一份裸 metadata。需要单独诊断时使用 check --candidate。"
        },
        {
          "actor": "宿主 AI → Python",
          "title": "接收为工作版本",
          "body": "AI 调用 record-metadata，一次完成检查和接收。如果拒绝，AI 读取原因、修改后再提交。接收只保存工作版本，是否交付仍由 AI 决定。",
          "inputs": "当前 input_hash、metadata、provenance",
          "outputs": "已接收的工作版本、检查结果和新哈希\n或供 AI 修正的拒绝原因",
          "gate": "程序校验拒绝不会改变当前 metadata 或哈希。最终交付时仍会复查。"
        },
        {
          "actor": "宿主 AI → Python → 你",
          "title": "交付两个有用的文件",
          "body": "AI 写简要说明，合并需要你处理的事项与重要限制，再显式调用 deliver。程序复查后才导出；无法完成则由 AI 调用 stop。",
          "inputs": "通过检查的工作版本 + AI 简要说明",
          "outputs": "metadata.json + summary.md",
          "gate": "接收与交付保留两道校验。缺少关键事实时可以如实停止；可选未知事项在 summary.md 中合并说明。"
        }
      ],
      "route": [
        {
          "label": "collect",
          "step": 1,
          "detail": "冻结资料，直接返回当前输入。"
        },
        {
          "label": "record-metadata",
          "step": 4,
          "detail": "检查候选，接收为工作版本。"
        },
        {
          "label": "deliver",
          "step": 5,
          "detail": "再次复查，导出 metadata.json 与 summary.md。"
        }
      ],
      "route_count": "3 次核心工具调用",
      "route_note": "调用之间由 AI 阅读资料、按需提问并编写候选。接收失败时，返回 AI 修改，再次提交。",
      "optional": [
        {
          "label": "schema --pointer",
          "detail": "字段含义不清楚时，查询该字段的说明。"
        },
        {
          "label": "check --candidate",
          "detail": "排查草稿时，按需单独执行只读检查。"
        },
        {
          "label": "evidence-add",
          "detail": "登记会影响结果的用户声明或新资料。"
        },
        {
          "label": "inspect",
          "detail": "输入变化或恢复任务时再读取；完整诊断用 --view full。"
        }
      ]
    },
    {
      "name": "评审现有元数据",
      "short": "先看冲突与有意义的未知",
      "description": "AI 对照证据评审当前声明，程序检查建议修改，原始文件保持不变。",
      "prompt": "用 $oep-metadata 对照 input/data.csv 和 input/source.md 评审 input/metadata.json，保存到 runs/review-01。先显示冲突和有意义的未知，简要总结我需要处理的事项，保留原文件。不上传。",
      "steps": [
        {
          "actor": "你 → 宿主 AI",
          "title": "选择评审对象",
          "body": "指定 metadata 快照，以及可用的数据和文档。AI 决定需要怎样核查。",
          "inputs": "已有 metadata 与证据",
          "outputs": "针对该快照的评审任务",
          "gate": "原文件即使存在程序错误，也可以输出有效的评审报告。"
        },
        {
          "actor": "宿主 AI → Python",
          "title": "读取检查与冻结证据",
          "body": "collect 已返回评审视图、原始证据、哈希、检查和非空评审目标。AI 直接复用并阅读资料，必要时再查看完整诊断信息。",
          "inputs": "冻结的 metadata、证据和约束",
          "outputs": "检查结果与评审目标",
          "gate": "schema 合法不能证明许可证和字段说明正确。"
        },
        {
          "actor": "宿主 AI ↔ 你",
          "title": "核查有意义的疑点",
          "body": "AI 只追查会影响判断的信息，必要时问关键问题。空白可选字段不会自动变成待确认问题。",
          "inputs": "现有声明与原始资料",
          "outputs": "有依据的结论，或明确的不确定性",
          "gate": "新补充的重要事实先登记为证据，再绑定评审。"
        },
        {
          "actor": "宿主 AI",
          "title": "判断每项现有声明",
          "body": "Reviewer 给出 supported、conflict、unknown 或 not_applicable，写清理由与依据。只有 conflict 可以附建议替换值。",
          "inputs": "当前 metadata、目标字段、原始证据",
          "outputs": "评审候选 JSON",
          "gate": "unknown 是证据不足，不是确认错误；缺信息本身也不等于不适用。"
        },
        {
          "actor": "宿主 AI → Python",
          "title": "检查修改建议",
          "body": "AI 登记意见，并阅读建议副本的检查结果。无效建议应先修改；全过程不改原文件。",
          "inputs": "当前哈希与完整评审意见",
          "outputs": "AI 判断数量、程序检查数量\n建议副本的检查结果",
          "gate": "未通过程序检查的建议 metadata 不会作为可用副本导出。"
        },
        {
          "actor": "宿主 AI → Python → 你",
          "title": "交付报告与简要说明",
          "body": "AI 合并真正需要处理的事项。报告先列冲突和未知，其他判断折叠，并直接包含程序检查。",
          "inputs": "已登记意见与简要说明",
          "outputs": "review.md、summary.md；适用时另有合法 metadata.suggested.json",
          "gate": "报告标明本次评审对象。原报告记录的冲突，不表示建议副本仍然保留同一错误。"
        }
      ],
      "route": [
        {
          "label": "collect",
          "step": 0,
          "detail": "冻结原始文件，返回评审目标。"
        },
        {
          "label": "record-review",
          "step": 4,
          "detail": "登记判断，检查建议副本。"
        },
        {
          "label": "deliver",
          "step": 5,
          "detail": "导出评审、简要说明，以及适用时的合法建议副本。"
        }
      ],
      "route_count": "3 次核心工具调用",
      "route_note": "AI 对照证据判断已有声明。报告绑定这次输入；建议副本是另一份文件，需要单独评审才能得到新报告。",
      "optional": [
        {
          "label": "schema --pointer",
          "detail": "按字段查看含义，无需整份读取 schema。"
        },
        {
          "label": "evidence-add",
          "detail": "登记关键补充证据，刷新绑定。"
        },
        {
          "label": "新建评审任务",
          "detail": "需要新的结论时，对建议副本单独评审。"
        }
      ]
    },
    {
      "name": "生成、独立评审与修复",
      "short": "AI 协调各角色，工具提供约束",
      "description": "宿主 AI 主导生成、全新独立评审和有依据的修复；程序约束接收与交付，不编排角色。",
      "prompt": "用 $oep-metadata 根据 input/data.csv 和 input/source.md 生成 metadata，再让全新独立 Agent 评审。修正有证据的问题，每次修改后重新独立评审，最多两轮修复。保存到 runs/checked-01，说明剩余限制。不上传。",
      "steps": [
        {
          "actor": "协调 AI → Python",
          "title": "准备组合任务",
          "body": "协调 AI 冻结资料、读取工具结果，设定修正预算，并决定怎样使用 Agent 与工具。",
          "inputs": "数据、文档、用途",
          "outputs": "中性工作上下文与证据",
          "gate": "程序不启动 Agent，也不会指挥下一个角色。"
        },
        {
          "actor": "生成 AI → Python",
          "title": "生成、校验并接收",
          "body": "生成 AI 理解资料，修正程序错误，提交工作版本。引用证据和校验通过都不保证语义正确。",
          "inputs": "中性模板与原始材料",
          "outputs": "通过程序检查的工作版本",
          "gate": "AI 可询问关键事实，并进行多轮检查和修正。"
        },
        {
          "actor": "协调 AI → 全新 Reviewer",
          "title": "请求独立判断",
          "body": "AI 导出当前 reviewer-input 包，再启动全新 Reviewer，只给该包和冻结来源快照。包中不包含生成理由和旧评审意见。",
          "inputs": "隔离的评审输入与角色要求",
          "outputs": "绑定当前版本的干净评审包\n每个已填评审目标对应一项判断",
          "gate": "评审包包含候选模板、字段契约、来源快照验证说明和程序检查范围。新的上下文由宿主提供。"
        },
        {
          "actor": "协调 AI → Python",
          "title": "登记评审，决定下一步",
          "body": "AI 登记真实的独立评审候选，分别读取 AI 判断数、程序检查数和建议副本的检查结果，再决定有依据的修复、必要的提问、交付或停止。",
          "inputs": "冲突、有意义的未知、程序检查",
          "outputs": "修复、澄清或停止的决定",
          "gate": "不会由代码自动切到 Repair 或宣布任务完成。"
        },
        {
          "actor": "修复 AI → Python",
          "title": "应用有依据的修改",
          "body": "协调 AI 或 Repair Agent 编写限定范围的补丁。程序核对旧值、评审范围、依据和完整结果。",
          "inputs": "当前哈希、问题与来源证据",
          "outputs": "已接收的新版本，或由 AI 解读的拒绝原因",
          "gate": "接收修改会使旧评审失效；循环重复的版本被拒绝。"
        },
        {
          "actor": "协调 AI → 新 Reviewer",
          "title": "复查并重新独立评审",
          "body": "修改或补充证据后，AI 请求全新独立评审。没有进展、缺关键证据或预算耗尽时停止。",
          "inputs": "修改后的 metadata 与更新的上下文",
          "outputs": "绑定当前版本和证据的新评审",
          "gate": "复用之前的评审回答，不算全新独立评审。"
        },
        {
          "actor": "协调 AI → Python → 你",
          "title": "选择交付，或诚实停止",
          "body": "程序检查通过且当前独立评审无 conflict 时，AI 可显式交付；剩余未知以简要、合并后的事项说明。",
          "inputs": "合法 metadata、当前评审、AI 简要说明",
          "outputs": "metadata.json、review.md、summary.md；停止则只有 summary.md",
          "gate": "程序校验和 Agent 意见一致都不能保证事实绝对正确。"
        }
      ],
      "route": [
        {
          "label": "collect",
          "step": 0,
          "detail": "冻结数据与背景资料。"
        },
        {
          "label": "record-metadata",
          "step": 1,
          "detail": "检查并接收生成候选。"
        },
        {
          "label": "review-input",
          "step": 2,
          "detail": "导出当前版本的干净评审包。"
        },
        {
          "label": "record-review",
          "step": 3,
          "detail": "登记全新独立 Reviewer 的判断。"
        },
        {
          "label": "deliver",
          "step": 6,
          "detail": "复查当前版本，交付经过评审的结果。"
        }
      ],
      "route_count": "未发生修复时的 5 次核心调用",
      "route_note": "宿主 AI 启动全新 Reviewer，并决定是否修复。每次接收修改后，都要重新导出评审包、重新独立评审，再决定交付。",
      "optional": [
        {
          "label": "apply-patch",
          "detail": "应用有证据的评审修改，然后获取全新独立评审。"
        },
        {
          "label": "evidence-add",
          "detail": "补充关键证据；旧评审随之失效。"
        },
        {
          "label": "stop",
          "detail": "说明缺少证据、无法隔离、预算耗尽或没有进展。"
        }
      ]
    },
    {
      "name": "上传元数据",
      "short": "先计划，再执行与回读",
      "description": "通过单独授权的操作更新已有 OEP 表的元数据。计划绑定候选和目标，执行前再次检查平台状态。",
      "prompt": "使用 $oep-metadata，为 input/metadata.json 准备上传到 https://openenergyplatform.org 上已有表 your_table 的计划。备份、差异和计划保存到 runs/upload-01，暂不执行。",
      "steps": [
        {
          "title": "明确本次更新",
          "actor": "你",
          "body": "指定 metadata 文件、已有 OEP 表和目标站点。明确只准备计划，或授权执行某个具体计划。上传数据行、建表和发布表属于其他操作。",
          "inputs": "元数据 JSON、目标站点与表",
          "outputs": "范围明确的上传请求",
          "gate": "生成本地 metadata 不等于授权远程写入。"
        },
        {
          "title": "校验并检查远端状态",
          "actor": "AI → CLI 与 Python",
          "body": "在准备上传前先校验 metadata。读取当前远端 metadata，并检查表的 Open Peer Review 状态。无法确认时记录为未知，不能当作未在评审。",
          "inputs": "候选 metadata 与当前 OEP 状态",
          "outputs": "远端快照与评审状态",
          "gate": "只有明确确认未在评审，计划才具备执行条件。"
        },
        {
          "title": "保存可检查的计划",
          "actor": "Python 程序",
          "body": "保存远端备份、待上传候选和可读差异。绑定目标、候选哈希、远端哈希、评审状态和计划哈希，输出路径使用相对引用。",
          "inputs": "本地候选与远端快照",
          "outputs": "metadata.remote.backup.json、metadata.diff\nmetadata.upload.json、upload.plan.json",
          "gate": "准备计划尚未发送更新 metadata 的 POST。"
        },
        {
          "title": "授权并绑定执行",
          "actor": "你与 AI → CLI",
          "body": "检查差异和目标，用匹配的 metadata、表名和输出目录执行所选计划。API Token 从指定环境变量读取，计划文件所在目录在运行时绑定。",
          "inputs": "已授权计划与环境变量中的 API Token",
          "outputs": "通过核对的本地计划和候选绑定",
          "gate": "候选过期、计划哈希变化或输出目录不匹配，都会被拒绝。"
        },
        {
          "title": "复查后只尝试一次",
          "actor": "Python 与 OEP",
          "body": "再次确认评审未激活，且远端 metadata 仍与计划快照一致。发送候选前创建独占的尝试标记。结果不确定时不会自动重试。",
          "inputs": "当前远端状态与绑定计划",
          "outputs": "一次 metadata 更新尝试",
          "gate": "客户端预检查不等于服务端原子条件写入，仍存在并发窗口。"
        },
        {
          "title": "回读并记录结果",
          "actor": "Python 程序",
          "body": "重新读取已存储的 metadata，与写入响应和原始请求比较。记录已验证、服务端发生变更，或需要人工检查的不确定结果。",
          "inputs": "写入响应与远端回读",
          "outputs": "metadata.readback.json、upload.receipt.json",
          "gate": "HTTP 成功不等于已验证。本项目仍未验证真实生产环境写入。"
        }
      ],
      "route": [
        {
          "label": "metadata-upload",
          "step": 0,
          "detail": "校验并准备绑定目标的备份、差异和计划。"
        },
        {
          "label": "检查计划",
          "step": 2,
          "detail": "AI 与用户检查具体的拟更新内容。"
        },
        {
          "label": "metadata-upload --execute",
          "step": 4,
          "detail": "执行用户已授权的目标与操作。"
        },
        {
          "label": "回读回执",
          "step": 5,
          "detail": "回读远端结果，核对并报告回执。"
        }
      ],
      "route_count": "准备计划 → 检查 → 授权范围内执行",
      "route_note": "AI 理解计划与已有授权。准备和执行时都会复查远端状态；成功上传也包括回读验证。",
      "optional": [
        {
          "label": "check",
          "detail": "准备上传前，按需排查本地 metadata 错误。"
        },
        {
          "label": "重新准备计划",
          "detail": "候选或远端状态变化后，准备新计划。"
        }
      ]
    },
    {
      "name": "保存或提交评审",
      "short": "将本地意见映射到 OEP 字段",
      "description": "把完成的本地评审转换为平台现有 Open Peer Review 协议。保存、提交和授予徽章是不同操作。",
      "prompt": "用 $oep-metadata 为 runs/review-01 的评审意见准备 OEP Open Peer Review 草稿保存计划，目标表为 your_table，平台为 https://openenergyplatform.org。由 AI 选取对应快照，使用我提供的授权会话 cookie，计划保存到 runs/review-save-01。先不要执行。",
      "steps": [
        {
          "title": "选定快照、意见与动作",
          "actor": "你",
          "body": "提供已经完成的评审及匹配的 metadata 快照，选择 save 或 submit；已有评审还需给出对应 ID。授权会话 Cookie 文件单独提供。",
          "inputs": "metadata、绑定的 review JSON、表与动作",
          "outputs": "范围明确的保存或提交请求",
          "gate": "API Token 不能替代已登录的 Web 会话。"
        },
        {
          "title": "核对账号角色与快照",
          "actor": "Python 与 OEP",
          "body": "核对本地评审与选定 metadata 的哈希。读取平台页面，确认评审权限和当前轮次，再比较平台公开的资源字段与本地快照。",
          "inputs": "本地评审与已认证的平台页面",
          "outputs": "通过核对的字段映射和页面状态",
          "gate": "子 Agent 不等于另一个平台账号，贡献者与评审者分离仍然适用。"
        },
        {
          "title": "映射平台支持的意见",
          "actor": "Python 程序",
          "body": "supported 映射为 Accept；有替换建议的 conflict 映射为 Suggest；没有替换值的 conflict 映射为 Deny。unknown 和 not_applicable 不能变成批准。报告跳过项，拒绝不支持的修改。",
          "inputs": "逐字段意见与平台字段键",
          "outputs": "OPR 请求内容、映射项和跳过项",
          "gate": "submit 要求覆盖所有已填写的平台字段；全 Accept 的完成与徽章流程不在此适配器内。"
        },
        {
          "title": "准备并检查计划",
          "actor": "Python 与你",
          "body": "保存解析后的远端备份、请求内容和哈希绑定的上传计划。检查意见能否表达，以及本次动作究竟是保存还是提交。原始 HTML 和会话凭据不复制进这些产物。",
          "inputs": "映射后的请求与远端状态指纹",
          "outputs": "opr.remote.backup.json、opr.upload.json\nupload.plan.json",
          "gate": "保存可以保留不完整草稿；提交时，必需字段上的未决意见会阻止执行。"
        },
        {
          "title": "执行已授权动作",
          "actor": "AI → CLI、Python 与 OEP",
          "body": "重复使用相同的表、动作、评审 ID 和输出目录。复查角色、轮次、快照及字段历史，再发送一次带 CSRF 的认证请求。新建草稿后，从平台页面识别评审 ID，不能猜测。",
          "inputs": "已授权计划与 Web 会话",
          "outputs": "一次保存或提交尝试",
          "gate": "Cookie 文件应在运行产物之外。尝试结果不确定时，先核查再决定是否重试。"
        },
        {
          "title": "验证意见及轮次变化",
          "actor": "Python 与你",
          "body": "回读评审，比较预期的字段意见和状态。提交需要确认轮次转换；保存需要确认仍处于预期的可编辑轮次。提交新草稿前，使用已验证的 ID 重新准备计划。",
          "inputs": "回读历史与平台状态",
          "outputs": "opr.readback.json、upload.receipt.json",
          "gate": "不隐含授予徽章、完成评审或平台认证，真实生产环境行为仍未验证。"
        }
      ],
      "route": [
        {
          "label": "review-upload",
          "step": 0,
          "detail": "准备选定的保存或提交操作。"
        },
        {
          "label": "检查映射",
          "step": 2,
          "detail": "核对角色、冻结快照和意见映射。"
        },
        {
          "label": "review-upload --execute",
          "step": 4,
          "detail": "执行用户已授权的操作。"
        },
        {
          "label": "回读回执",
          "step": 5,
          "detail": "回读意见和平台状态，确认结果。"
        }
      ],
      "route_count": "保存和提交是不同的操作",
      "route_note": "AI 使用与意见匹配的 metadata 快照。保存计划不等于提交评审，也不隐含授予平台徽章。",
      "optional": [
        {
          "label": "save",
          "detail": "在适配器允许时，保存尚未完成的工作意见。"
        },
        {
          "label": "submit",
          "detail": "使用已核实的评审 ID，为已授权的提交准备独立计划。"
        }
      ]
    }
  ],
  "language": "zh-CN"
};

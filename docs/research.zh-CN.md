# 选题与验证记录

调研日期：2026-11-16。这个文件记录产品判断，不把搜索结果当作用户验证，也不承诺星数。

## 避开本地已有项目

工作目录中已有 skill-diff，处理 Agent Skill 更新差异与静态审查。本项目面向机器人学习数据的来源和帧区间，使用场景与该项目不同。

## 可查证的信号

- [LeRobot](https://github.com/huggingface/lerobot)：调研时 GitHub API 返回 28,911 stars。这个数字只说明生态有规模，不代表本工具已经有需求或用户。
- [Issue #1492](https://github.com/huggingface/lerobot/issues/1492)：用户明确提出在训练中划分 holdout episode、计算验证损失的需求。
- [Issue #250](https://github.com/huggingface/lerobot/issues/250)：讨论真实数据集的验证损失和验证集。这些问题说明评估流程受关注，不能证明窗口泄漏普遍存在，也不表明当前版本仍缺少该功能。
- [官方加载示例](https://github.com/huggingface/lerobot/blob/main/examples/dataset/load_lerobot_dataset.py)：动作加载可以使用多个未来帧；官方测试也覆盖 episode 边界裁剪。这支持“读取范围需要明确”的技术背景，不支持“LeRobot 默认泄漏”的结论。
- [官方数据工具](https://huggingface.co/docs/lerobot/using_dataset_tools)：已经支持划分与合并。本项目不重做完整数据管理。
- [Calibra](https://github.com/Calibra-Robotics/Calibra)：已经覆盖数据质量和 duplicate/near-duplicate leakage。我们不能宣称首次发现或首次解决机器人数据泄漏。
- [TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)：已有通用时间序列 gap 分割方法。

## 选择的产品范围

目标用户是维护自定义机器人切片、跨视角数据、增强副本和合并数据集的开发者。产品假设是：他们能够提供原始录制来源，但缺少一个小巧、离线、能显示窗口证据并验证新划分的检查工具。

差异点是明确的来源坐标契约、时间轴证据、组隔离与连通分量划分组合。这个组合有实用价值的可能性，但不是不可替代的技术壁垒。

首版刻意只处理可验证的区间与来源条件。未知来源的相似演示、训练统计泄漏、真实策略效果仍需要其他工具。

## 发布后优先验证

1. 找到三种真实数据准备流程的脱敏 manifest，检查接入是否需要超过十分钟。
2. 记录实际发现的问题和误报，尤其是 loader 已在 clip 边界裁剪的情况。
3. 收集来源映射难以提供的原因；如果普遍缺少 provenance，优先改进导出而不是堆检测功能。
4. 衡量是否有人在训练前重复运行、接入 CI 或贡献真实案例；星数只是后续信号。
5. 未完成上述验证前，明确标为 alpha，不写“生产验证”“提升成功率”等宣传。

## 发布素材与节奏

首屏使用真实运行生成的 before/after 报告；一条命令可离线体验。英文 README 面向社区，中文文档方便本地开发者。提供 MIT 许可、测试、格式契约、贡献指南和问题模板。

首轮发布可围绕“同一原始录制的两个片段，为何没有交集却仍共享动作窗口”这个具体例子。只在规则允许的社区分享，说明这是合成示例，并链接到算法和限制。不要批量给无关仓库提 issue、群发消息或制造 stars。

本次没有代发社区消息，也没有真实用户、实机训练或性能收益验证。

# FSU 脚本修改工作区

对 `【FSU】EAFC FUT WEB 增强器-26.09.user.js` 进行功能优化的版本管理工作区。

## 目录说明

| 路径 | 说明 |
|------|------|
| `working/` | 工作区 — 在此文件中进行修改 |
| `archive/` | 版本快照 — 每次重大修改前的完整备份 |
| `CHANGELOG.md` | 修改日志 — 详细记录每次改了什么、为什么改 |
| `VERSION` | 当前版本号 |

## 修改流程

1. 确认要修改的内容
2. 创建快照：`cp working/* archive/v26.09-mod-NN.user.js`
3. 修改 `working/` 中的脚本
4. 更新 `CHANGELOG.md`
5. 更新 `VERSION`
6. 提交 git commit

## 回退方法

- **Git**: `git revert <commit>` 或 `git checkout <hash> -- working/`
- **文件快照**: 从 `archive/` 复制对应版本覆盖 `working/`

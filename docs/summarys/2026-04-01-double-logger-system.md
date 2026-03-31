# 双文件日志系统实现总结

## 需求
原单一日志文件 `app.log` 内容太多太乱，需要分离：
- **log_full**: 完整日志，便于调试
- **log_main**: 只记录关键日志，方便快速查看系统状态

## 实现方案
采用 **Python logging 标准库的多handler + 过滤器** 方案：
- 一个 logger，多个 handler
- `MainLogFilter` 自定义过滤器过滤关键事件
- `TimedRotatingFileHandler` 自动轮转清理

### 配置
| 文件 | 格式 | 级别 | 轮转策略 |
|------|------|------|----------|
| `logs/log_full.log` | JSON结构化 | DEBUG+（所有日志）| 每周轮转，保留1周备份 |
| `logs/log_main.log` | 纯文本人类可读 | INFO+（仅关键事件） | 每周轮转，保留2周备份 |

### 关键事件进入 log_main
- 前后端连接建立/断开
- ASR服务连接状态
- 阿里云Token过期时间
- 数据传输统计
- 音频/摄像头/字幕开关切换（每次切换都有明显日志）
- 应用启动信息
- **所有 WARNING 和 ERROR 自动保留**

## 修改文件
只修改了一个文件：**`backend/utils/logger.py`**
- 添加 `TimedRotatingFileHandler` 导入
- 添加 `MainLogFilter` 过滤器类
- 修改 `setup_logging()` 配置双handler

无需修改任何业务代码，零侵入。

## 验证结果
- ✅ 两个日志文件正确生成
- ✅ `log_full` 包含所有日志（含debug）
- ✅ `log_main` 只包含关键日志，格式清晰易读
- ✅ 自动轮转配置正确，会自动清理旧日志
- ✅ 开关音频/摄像头事件正确记录到 `log_main`

## 经验
使用 Python 标准库 `logging.Filter` 可以很灵活地实现日志分流，配合不同的 `Formatter` 可以让不同输出目标有不同格式。`TimedRotatingFileHandler` 内置轮转清理，不需要自己写定时任务。

## 2026-04-01 更新：增加状态显示增强

### 需求改进
`audio_toggled`、`subtitle_toggled`、`camera_toggled` 这些切换事件日志只显示事件名称，不明确当前是**开启**还是**关闭**状态。

### 改进方案
在 `MainLogFormatter` 解析 JSON 时增加特殊处理：如果日志数据包含 `enabled` 字段，自动将布尔值转换为"开启/关闭"中文文字并追加到日志消息后。

效果示例：
```
2026-04-01 01:27:31 [INFO][websocket] audio_toggled -> 开启
2026-04-01 01:27:33 [INFO][websocket] subtitle_toggled -> 关闭
```

### 代码质量清理 (simplify)
- 将方法内 `import json` 移到文件顶部，避免重复导入
- 修正函数返回类型注解，使其准确

### 验证
- ✅ 开关事件清晰显示当前状态
- ✅ 不影响原有其他日志格式
- ✅ Python 语法检查通过

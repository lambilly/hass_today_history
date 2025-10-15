# 历史上的今天 Home Assistant 集成

这是一个用于 Home Assistant 的集成，通过探数API获取"历史上的今天"数据，并提供滚动显示功能。

## 功能特点

- 📅 获取历史上的今天重要事件
- 🔄 自动过滤敏感内容（逝世、去世等）
- ⏰ 可配置的数据更新间隔（60-43200分钟）
- 📜 头条滚动显示功能，可配置滚动间隔（5-300秒）
- 🏷️ 中文界面，易于配置
- 📊 提供两个实体：今日历史和滚动历史

## 安装

### 通过 HACS 安装（推荐）

1. 在 HACS 中点击"集成"
2. 点击右下角的"添加自定义存储库"
3. 输入仓库URL (https://github.com/lambilly/hass_today_history/)并选择类别为"集成"
4. 在集成列表中找到"历史上的今天"并安装
5. 重启 Home Assistant

### 手动安装

1. 将 `custom_components/today_history` 文件夹复制到您的 Home Assistant 配置目录中
2. 重启 Home Assistant

## 配置

### 第一步：获取 API 密钥

1. 访问 [探数API](https://www.tanshuapi.com/)
2. 注册账号并申请免费的"历史上的今天"API密钥

### 第二步：添加集成

1. 进入 Home Assistant → 设置 → 设备与服务 → 集成
2. 点击"添加集成"
3. 搜索"历史上的今天"
4. 输入您的 API 密钥
5. 配置数据更新间隔和头条滚动间隔
6. 点击提交

## 实体

集成会创建以下实体：

### 传感器.今日历史
- **状态**: 数据更新时间
- **属性**:
  - `title`: 标题
  - `today_item`: 今日历史事件
  - `history_list`: 历史事件列表
  - `total_count`: 总事件数量
  - `update_interval`: 数据更新间隔（分钟）

### 传感器.滚动历史
- **状态**: 当前日期
- **属性**:
  - `title`: 事件标题
  - `year`: 事件年份
  - `month`: 事件月份
  - `day`: 事件日期
  - `content`: 事件内容
  - `scroll_index`: 当前滚动索引
  - `total_items`: 总事件数量
  - `scroll_interval`: 滚动间隔（秒）

## 设备

集成会创建一个名为"信息查询"的设备，包含上述两个实体。

## 配置选项

在集成选项中可以调整以下设置：

- **数据更新间隔**: 60-43200分钟（默认1440分钟，即24小时）
- **头条滚动间隔**: 5-300秒（默认30秒）

## 自动化示例

```yaml
# 当有新历史数据时发送通知
automation:
  - alias: "今日历史更新通知"
    trigger:
      platform: state
      entity_id: sensor.jin_ri_li_shi
    action:
      service: notify.mobile_app
      data:
        message: "今日历史已更新：{{ state_attr('sensor.jin_ri_li_shi', 'today_item').content }}"

# 使用滚动历史内容
automation:
  - alias: "显示历史事件"
    trigger:
      platform: time_pattern
      seconds: "/30"
    action:
      service: persistent_notification.create
      data:
        title: "历史上的今天"
        message: "{{ state_attr('sensor.gun_dong_li_shi', 'content') }}"
```
## 故障排除
### 常见问题
1.	API密钥无效
o	检查API密钥是否正确
o	确认在探数API平台已激活"历史上的今天"服务
2.	无法获取数据
o	检查网络连接
o	查看Home Assistant日志获取详细错误信息
3.	实体不更新
o	检查数据更新间隔设置
o	确认集成配置正确

## 日志调试
如需调试信息，请在 configuration.yaml 中添加：

```yaml
logger:
  default: info
  logs:
    custom_components.today_history: debug
```
## 支持
如有问题，请：
1.	查看 Home Assistant 日志
2.	检查集成配置
3.	在项目仓库提交 Issue

## 许可证
MIT License

## 贡献
欢迎提交 Pull Request 和 Issue 来改进这个集成。


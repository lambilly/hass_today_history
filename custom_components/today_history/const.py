"""常量."""
DOMAIN = "today_history"
API_URL = "https://api.tanshuapi.com/api/today_in_history/v1/index?key="

# 过滤关键词
FORBIDDEN_KEYWORDS = [
    "去世", "逝世", "诞辰", "病故", "病逝", 
    "死亡", "出生", "身亡", "自杀", "长逝", "长辞", "葬"
]

# 默认间隔
DEFAULT_UPDATE_INTERVAL = 1440  # 默认更新间隔1440分钟（24小时）
DEFAULT_SCROLL_INTERVAL = 30    # 默认滚动间隔30秒

# 属性键
ATTR_TODAY_ITEM = "today_item"
ATTR_HISTORY_LIST = "history_list"
ATTR_TOTAL_COUNT = "total_count"
ATTR_SCROLL_CONTENT = "scroll_content"
ATTR_SCROLL_INDEX = "scroll_index"
ATTR_CURRENT_DATE = "current_date"
ATTR_UPDATE_INTERVAL = "update_interval"
ATTR_SCROLL_INTERVAL = "scroll_interval"
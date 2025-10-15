"""历史上的今天集成."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    API_URL,
    FORBIDDEN_KEYWORDS,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_SCROLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置集成入口."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = TodayHistoryCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成入口."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class TodayHistoryCoordinator(DataUpdateCoordinator):
    """数据更新协调器."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """初始化."""
        update_interval_minutes = entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        update_interval = timedelta(minutes=update_interval_minutes)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.entry = entry
        self.api_key = entry.data["api_key"]
        self.scroll_interval = entry.options.get("scroll_interval", DEFAULT_SCROLL_INTERVAL)
        self.current_scroll_index = 0
        self.filtered_data = []

    async def _async_update_data(self) -> dict[str, Any]:
        """获取数据."""
        try:
            async with async_timeout.timeout(10):
                return await self._fetch_today_history()
        except Exception as err:
            raise UpdateFailed(f"获取数据错误: {err}") from err

    async def _fetch_today_history(self) -> dict[str, Any]:
        """从API获取历史上的今天数据."""
        session = async_get_clientsession(self.hass)
        
        # 获取今天日期
        from datetime import datetime
        today = datetime.now()
        date_str = today.strftime("%m%d")
        
        url = f"{API_URL}{self.api_key}&date={date_str}"
        
        _LOGGER.debug("请求URL: %s", url)
        
        async with session.get(url) as response:
            if response.status != 200:
                raise UpdateFailed(f"API请求失败: {response.status}")
                
            data = await response.json()
            
            # 过滤数据
            filtered_list = self._filter_data(data.get("data", {}).get("list", []))
            
            # 随机选择一条作为今日历史
            import random
            today_item = {}
            if filtered_list:
                today_item = random.choice(filtered_list)
            
            # 缓存过滤后的数据用于滚动显示
            self.filtered_data = filtered_list
            self.current_scroll_index = 0
            
            return {
                "title": "历史上的今天",
                "today_item": today_item,
                "history_list": filtered_list,
                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "current_date": datetime.now().strftime("%Y-%m-%d"),
                "total_count": len(filtered_list)
            }

    def _filter_data(self, data_list: list) -> list:
        """过滤掉包含敏感关键词的数据."""
        filtered = []
        for item in data_list:
            content = item.get("content", "")
            # 检查是否包含过滤关键词
            if not any(keyword in content for keyword in FORBIDDEN_KEYWORDS):
                filtered.append({
                    "title": item.get("title", ""),
                    "year": item.get("year", ""),
                    "month": item.get("month", ""),
                    "day": item.get("day", ""),
                    "content": content
                })
        return filtered

    def get_next_scroll_item(self) -> dict:
        """获取下一条滚动显示的内容."""
        if not self.filtered_data:
            return {
                "title": "暂无数据",
                "content": "请等待数据更新",
                "year": "",
                "month": "",
                "day": ""
            }
        
        item = self.filtered_data[self.current_scroll_index]
        self.current_scroll_index = (self.current_scroll_index + 1) % len(self.filtered_data)
        
        return item
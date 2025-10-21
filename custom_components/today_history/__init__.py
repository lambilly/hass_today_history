"""历史上的今天集成."""
from __future__ import annotations

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import event

from .const import (
    DOMAIN,
    API_URL,
    FORBIDDEN_KEYWORDS,
    DEFAULT_SCROLL_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """设置集成入口."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = TodayHistoryCoordinator(hass, entry)
    
    # 设置定时更新任务 - 每天0:01分更新
    await setup_scheduled_updates(hass, coordinator)
    
    # 立即进行一次数据更新
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def setup_scheduled_updates(hass: HomeAssistant, coordinator) -> None:
    """设置定时更新任务."""
    async def scheduled_update(now=None):
        """定时更新数据."""
        max_retries = 2
        retry_delay = 600  # 10分钟
        
        for attempt in range(max_retries + 1):
            try:
                await coordinator.async_refresh()
                _LOGGER.info("数据更新成功")
                break
            except Exception as err:
                if attempt < max_retries:
                    _LOGGER.warning("数据更新失败，%d分钟后重试: %s", retry_delay // 60, err)
                    await asyncio.sleep(retry_delay)
                else:
                    _LOGGER.error("数据更新失败，已重试%d次: %s", max_retries, err)
    
    # 设置每天0:01分执行更新
    async_track_time = event.async_track_time_change(
        hass, 
        scheduled_update, 
        hour=0, 
        minute=1, 
        second=0
    )
    
    # 存储定时器以便清理
    coordinator._scheduled_update = async_track_time


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成入口."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN][entry.entry_id]
        # 清理定时器
        if hasattr(coordinator, '_scheduled_update'):
            coordinator._scheduled_update()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class TodayHistoryCoordinator(DataUpdateCoordinator):
    """数据更新协调器."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """初始化."""
        # 不再使用配置的更新间隔，改为固定24小时（但实际由定时任务控制）
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=24),
        )
        self.entry = entry
        self.api_key = entry.data["api_key"]
        self.scroll_interval = entry.options.get("scroll_interval", DEFAULT_SCROLL_INTERVAL)
        self.current_scroll_index = 0
        self.filtered_data = []
        self.last_success_time = None

    async def _async_update_data(self) -> dict[str, Any]:
        """获取数据."""
        try:
            async with async_timeout.timeout(15):  # 增加超时时间到15秒
                return await self._fetch_today_history()
        except Exception as err:
            raise UpdateFailed(f"获取数据错误: {err}") from err

    async def _fetch_today_history(self) -> dict[str, Any]:
        """从API获取历史上的今天数据."""
        session = async_get_clientsession(self.hass)
        
        # 获取今天日期
        today = datetime.now()
        date_str = today.strftime("%m%d")
        
        url = f"{API_URL}{self.api_key}&date={date_str}"
        
        _LOGGER.debug("请求URL: %s", url)
        
        async with session.get(url) as response:
            # 记录响应状态和内容类型
            content_type = response.headers.get('Content-Type', '')
            _LOGGER.debug("响应状态: %s, Content-Type: %s", response.status, content_type)
            
            if response.status != 200:
                # 尝试读取错误信息
                error_text = await response.text()
                _LOGGER.error("API请求失败: %s, 响应内容: %s", response.status, error_text[:200])
                raise UpdateFailed(f"API请求失败: {response.status}")
            
            # 检查响应内容类型
            if 'application/json' not in content_type:
                # 如果不是JSON，尝试读取内容并记录
                response_text = await response.text()
                _LOGGER.error("API返回非JSON内容: %s", response_text[:500])
                raise UpdateFailed("API返回格式错误，请检查API密钥是否正确")
                
            try:
                data = await response.json()
            except (aiohttp.ClientError, json.JSONDecodeError) as err:
                # JSON解析失败，记录原始响应
                response_text = await response.text()
                _LOGGER.error("JSON解析失败: %s, 原始响应: %s", err, response_text[:500])
                raise UpdateFailed("数据解析失败") from err
            
            # 检查API返回的数据结构
            if not data or not isinstance(data, dict):
                _LOGGER.error("API返回数据格式错误: %s", data)
                raise UpdateFailed("API返回数据格式错误")
            
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
            
            # 记录成功时间
            success_time = datetime.now()
            self.last_success_time = success_time.strftime("%Y-%m-%d %H:%M:%S")
            
            return {
                "title": "历史上的今天",
                "today_item": today_item,
                "history_list": filtered_list,
                "update_time": self.last_success_time,  # 使用API成功请求的时间
                "current_date": today.strftime("%Y-%m-%d"),
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
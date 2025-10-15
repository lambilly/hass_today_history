"""传感器平台."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers import event

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL, DEFAULT_SCROLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """设置传感器平台."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = [
        TodayHistorySensor(coordinator, entry),
        TodayHistoryScrollSensor(coordinator, entry)
    ]
    
    async_add_entities(entities)


class TodayHistorySensor(CoordinatorEntity, SensorEntity):
    """今日历史传感器."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """初始化传感器."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "今日历史"
        self._attr_unique_id = f"{entry.entry_id}_jin_ri_li_shi"
        self._attr_icon = "mdi:calendar-today"
        self._attr_has_entity_name = True
        
        # 设置设备信息
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "info_query")},
            "name": "信息查询",
            "manufacturer": "lambilly",
            "model": "Today History",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> str:
        """返回传感器状态."""
        return self.coordinator.data.get("update_time", "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回额外属性."""
        data = self.coordinator.data
        return {
            "title": data.get("title", ""),
            "today_item": data.get("today_item", {}),
            "history_list": data.get("history_list", []),
            "total_count": data.get("total_count", 0),
            "update_interval": self.coordinator.entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        }


class TodayHistoryScrollSensor(CoordinatorEntity, SensorEntity):
    """滚动显示传感器."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """初始化滚动传感器."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "滚动历史"
        self._attr_unique_id = f"{entry.entry_id}_gun_dong_li_shi"
        self._attr_icon = "mdi:calendar-text"
        self._attr_has_entity_name = True
        self._current_item = {}
        self._scroll_index = 0
        self._remove_timer = None
        
        # 设置设备信息（与今日历史传感器相同的设备）
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "info_query")},
            "name": "信息查询",
            "manufacturer": "lambilly",
            "model": "Today History",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self) -> str:
        """返回滚动内容 - 修改为返回当天日期."""
        return self.coordinator.data.get("current_date", datetime.now().strftime("%Y-%m-%d"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """返回滚动内容的详细属性."""
        # 删除了scroll_content属性，添加了scroll_interval属性
        return {
            "title": self._current_item.get("title", ""),
            "year": self._current_item.get("year", ""),
            "month": self._current_item.get("month", ""),
            "day": self._current_item.get("day", ""),
            "content": self._current_item.get("content", ""),
            "scroll_index": self._scroll_index,
            "total_items": len(self.coordinator.filtered_data),
            "scroll_interval": self.coordinator.scroll_interval
        }

    async def async_added_to_hass(self) -> None:
        """实体添加到HA时调用."""
        await super().async_added_to_hass()
        # 设置定时更新滚动内容
        self._remove_timer = event.async_track_time_interval(
            self.hass,
            self._update_scroll_content,
            timedelta(seconds=self.coordinator.scroll_interval)
        )

    async def async_will_remove_from_hass(self) -> None:
        """实体从HA移除时调用."""
        if self._remove_timer:
            self._remove_timer()
        await super().async_will_remove_from_hass()

    async def _update_scroll_content(self, now=None) -> None:
        """更新滚动显示的内容."""
        self._current_item = self.coordinator.get_next_scroll_item()
        self._scroll_index = self.coordinator.current_scroll_index
        self.async_write_ha_state()
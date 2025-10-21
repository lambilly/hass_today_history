"""配置流."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_SCROLL_INTERVAL


class TodayHistoryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理配置流."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """处理用户步骤."""
        errors = {}

        if user_input is not None:
            # 验证API密钥
            if await self._test_api_key(user_input["api_key"]):
                return self.async_create_entry(
                    title="历史上的今天",
                    data={
                        "api_key": user_input["api_key"]
                    },
                    options={
                        "scroll_interval": user_input["scroll_interval"]
                    }
                )
            else:
                errors["base"] = "invalid_api_key"

        data_schema = vol.Schema({
            vol.Required("api_key"): str,
            vol.Optional(
                "scroll_interval",
                default=DEFAULT_SCROLL_INTERVAL
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "api_url": "https://www.tanshuapi.com/"
            }
        )

    async def _test_api_key(self, api_key: str) -> bool:
        """测试API密钥是否有效."""
        try:
            from datetime import datetime
            import async_timeout
            
            session = async_get_clientsession(self.hass)
            today = datetime.now()
            date_str = today.strftime("%m%d")
            url = f"https://api.tanshuapi.com/api/today_in_history/v1/index?key={api_key}&date={date_str}"
            
            async with async_timeout.timeout(10):
                async with session.get(url) as response:
                    # 检查响应状态和内容类型
                    if response.status != 200:
                        return False
                    
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' not in content_type:
                        return False
                    
                    # 尝试解析JSON
                    data = await response.json()
                    return isinstance(data, dict) and 'data' in data
        except Exception:
            return False

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """获取选项流."""
        return TodayHistoryOptionsFlow(config_entry)


class TodayHistoryOptionsFlow(config_entries.OptionsFlow):
    """处理选项流."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """初始化."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """管理选项."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "scroll_interval",
                    default=self.config_entry.options.get("scroll_interval", DEFAULT_SCROLL_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300))
            })
        )
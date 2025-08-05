"""
Verilog code generation tools for MCP
"""

import aiohttp
import logging
from typing import Any, Dict

from moatless_mcp.tools.base import MCPTool, ToolResult

logger = logging.getLogger(__name__)


class VerilogGenerateTool(MCPTool):
    """Tool to generate Verilog code using online service"""
    
    def __init__(self, workspace, api_url: str = "http://116.204.110.235:20152/api/generate"):
        super().__init__(workspace)
        self.api_url = api_url
    
    @property
    def name(self) -> str:
        return "verilog_generate"
    
    @property
    def description(self) -> str:
        return "通过在线服务生成Verilog代码，根据问题描述自动生成对应的Verilog模块"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verilog_question_content": {
                    "type": "string",
                    "description": "Verilog问题描述，用于生成对应的Verilog代码"
                },
                "timeout": {
                    "type": "integer",
                    "description": "请求超时时间（秒）",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["verilog_question_content"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            question_content = arguments["verilog_question_content"]
            timeout = arguments.get("timeout", 60)
            
            # 准备请求数据
            payload = {
                "verilog_question_content": question_content
            }
            
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # 发送HTTP请求到Verilog生成服务
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # 提取生成的代码
                        generated_code = result_data.get("code_result", "")
                        
                        if generated_code:
                            message = f"Verilog代码生成成功:\n\n```verilog\n{generated_code}\n```"
                        else:
                            message = "Verilog代码生成成功，但返回的代码为空"
                        
                        return ToolResult(
                            message=message,
                            properties={
                                "question_content": question_content,
                                "generated_code": generated_code,
                                "api_url": self.api_url,
                                "status_code": response.status
                            }
                        )
                    else:
                        error_text = await response.text()
                        return ToolResult(
                            message=f"Verilog代码生成失败 (状态码: {response.status}):\n{error_text}",
                            success=False,
                            properties={
                                "question_content": question_content,
                                "api_url": self.api_url,
                                "status_code": response.status,
                                "error": error_text
                            }
                        )
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP请求错误: {e}")
            return ToolResult(
                message=f"网络请求失败: {str(e)}",
                success=False,
                properties={
                    "question_content": arguments.get("verilog_question_content", ""),
                    "error": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Verilog生成工具执行错误: {e}")
            return self.format_error(e)


class VerilogV2SvgTool(MCPTool):
    """Tool to convert Verilog code to SVG image link"""
    
    def __init__(self, workspace, api_url: str = "http://116.204.110.235:20152/api/v2svg-link"):
        super().__init__(workspace)
        self.api_url = api_url
    
    @property
    def name(self) -> str:
        return "verilog_v2svg_link"
    
    @property
    def description(self) -> str:
        return "将Verilog代码转换为SVG图片链接，生成电路图的SVG格式图片"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "verilog_file_content": {
                    "type": "string",
                    "description": "Verilog代码内容，用于生成对应的SVG电路图"
                },
                "timeout": {
                    "type": "integer",
                    "description": "请求超时时间（秒）",
                    "default": 60,
                    "minimum": 10,
                    "maximum": 300
                }
            },
            "required": ["verilog_file_content"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            verilog_content = arguments["verilog_file_content"]
            timeout = arguments.get("timeout", 60)
            
            # 准备请求数据
            payload = {
                "verilog_file_content": verilog_content
            }
            
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json"
            }
            
            # 发送HTTP请求到Verilog转SVG服务
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    
                    if response.status == 200:
                        result_data = await response.json()
                        
                        # 检查服务返回的成功状态
                        success = result_data.get("success", False)
                        svg_link = result_data.get("svg_link", "")
                        message_text = result_data.get("message", "")
                        
                        if success and svg_link:
                            message = f"SVG图片生成成功!\n\n📊 **SVG图片链接**: {svg_link}\n\n💡 **说明**: {message_text}\n\n🔗 **直接访问**: 点击链接查看生成的电路图"
                        else:
                            error_msg = result_data.get("message", "未知错误")
                            message = f"SVG图片生成失败: {error_msg}"
                            return ToolResult(
                                message=message,
                                success=False,
                                properties={
                                    "verilog_content": verilog_content,
                                    "api_url": self.api_url,
                                    "status_code": response.status,
                                    "error": error_msg
                                }
                            )
                        
                        return ToolResult(
                            message=message,
                            properties={
                                "verilog_content": verilog_content,
                                "svg_link": svg_link,
                                "success": success,
                                "message": message_text,
                                "api_url": self.api_url,
                                "status_code": response.status
                            }
                        )
                    else:
                        error_text = await response.text()
                        return ToolResult(
                            message=f"SVG图片生成失败 (状态码: {response.status}):\n{error_text}",
                            success=False,
                            properties={
                                "verilog_content": verilog_content,
                                "api_url": self.api_url,
                                "status_code": response.status,
                                "error": error_text
                            }
                        )
                        
        except aiohttp.ClientError as e:
            logger.error(f"HTTP请求错误: {e}")
            return ToolResult(
                message=f"网络请求失败: {str(e)}",
                success=False,
                properties={
                    "verilog_content": arguments.get("verilog_file_content", ""),
                    "error": str(e)
                }
            )
        except Exception as e:
            logger.error(f"Verilog转SVG工具执行错误: {e}")
            return self.format_error(e) 
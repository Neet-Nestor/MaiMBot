import asyncio
from datetime import datetime

from src.common.logger import get_logger
from src.llm_models.payload_content.tool_option import ToolParamType
from src.memory_system.Memory_chest import global_memory_chest
from src.plugin_system.base.base_tool import BaseTool
from src.plugin_system.apis.message_api import get_messages_by_time_in_chat, build_readable_messages
from src.llm_models.utils_model import LLMRequest
from src.config.config import model_config
from typing import Any

logger = get_logger("memory")

def parse_datetime_to_timestamp(value: str) -> float:
    """
    接受多种常见格式并转换为时间戳（秒）
    支持示例：
    - 2025-09-29
    - 2025-09-29 00:00:00
    - 2025/09/29 00:00
    - 2025-09-29T00:00:00
    """
    value = value.strip()
    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ]
    last_err = None
    for fmt in fmts:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.timestamp()
        except Exception as e:
            last_err = e
    raise ValueError(f"无法解析时间: {value} ({last_err})")

def parse_time_range(time_range: str) -> tuple[float, float]:
    """
    解析时间范围字符串，返回开始和结束时间戳
    格式: "YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS"
    """
    if " - " not in time_range:
        raise ValueError("时间范围格式错误，应使用 ' - ' 分隔开始和结束时间")
    
    start_str, end_str = time_range.split(" - ", 1)
    start_timestamp = parse_datetime_to_timestamp(start_str.strip())
    end_timestamp = parse_datetime_to_timestamp(end_str.strip())
    
    if start_timestamp > end_timestamp:
        raise ValueError("开始时间不能晚于结束时间")
    
    return start_timestamp, end_timestamp
class GetMemoryTool(BaseTool):
    """获取用户信息"""

    name = "get_memory"
    description = "在记忆中搜索，获取某个问题的答案，可以指定搜索的时间范围或时间点"
    parameters = [
        ("question", ToolParamType.STRING, "需要获取答案的问题", True, None),
        ("time_point", ToolParamType.STRING, "需要获取记忆的时间点，格式为YYYY-MM-DD HH:MM:SS", False, None),
        ("time_range", ToolParamType.STRING, "需要获取记忆的时间范围，格式为YYYY-MM-DD HH:MM:SS - YYYY-MM-DD HH:MM:SS", False, None)
    ]
    
    available_for_llm = True

    async def execute(self, function_args: dict[str, Any]) -> dict[str, Any]:
        """执行记忆搜索

        Args:
            function_args: 工具参数

        Returns:
            dict: 工具执行结果
        """
        question: str = function_args.get("question")  # type: ignore
        time_point: str = function_args.get("time_point")  # type: ignore
        time_range: str = function_args.get("time_range")  # type: ignore

        # 检查是否指定了时间参数
        has_time_params = bool(time_point or time_range)
        
        if has_time_params and not self.chat_id:
            return {"content": f"问题：{question}，无法获取聊天记录：缺少chat_id"}
        
        # 创建并行任务
        tasks = []
        
        # 原任务：从记忆仓库获取答案
        memory_task = asyncio.create_task(
            global_memory_chest.get_answer_by_question(question=question)
        )
        tasks.append(("memory", memory_task))
        
        # 新任务：从聊天记录获取答案（如果指定了时间参数）
        chat_task = None
        if has_time_params:
            chat_task = asyncio.create_task(
                self._get_answer_from_chat_history(question, time_point, time_range)
            )
            tasks.append(("chat", chat_task))
        
        # 等待所有任务完成
        results = {}
        for task_name, task in tasks:
            try:
                results[task_name] = await task
            except Exception as e:
                logger.error(f"任务 {task_name} 执行失败: {e}")
                results[task_name] = None
        
        # 处理结果
        memory_answer = results.get("memory")
        chat_answer = results.get("chat")
        
        # 构建返回内容
        content_parts = []
        
        if memory_answer:
            content_parts.append(f"对问题'{question}'，你回忆的信息是：{memory_answer}")
        
        if chat_answer:
            content_parts.append(f"对问题'{question}'，基于聊天记录的回答：{chat_answer}")
        elif has_time_params:
            if time_point:
                content_parts.append(f"在 {time_point} 的时间点，你没有参与聊天")
            elif time_range:
                content_parts.append(f"在 {time_range} 的时间范围内，你没有参与聊天")
            
        if content_parts:
            retrieval_content = f"问题：{question}" + "\n".join(content_parts)
            return {"content": retrieval_content}
        else:
            return {"content": ""}

    
    async def _get_answer_from_chat_history(self, question: str, time_point: str = None, time_range: str = None) -> str:
        """从聊天记录中获取问题的答案"""
        try:
            # 确定时间范围
            print(f"time_point: {time_point}, time_range: {time_range}")
            
            # 检查time_range的两个时间值是否相同，如果相同则按照time_point处理
            if time_range and not time_point:
                try:
                    start_timestamp, end_timestamp = parse_time_range(time_range)
                    if start_timestamp == end_timestamp:
                        # 两个时间值相同，按照time_point处理
                        time_point = time_range.split(" - ")[0].strip()
                        time_range = None
                        print(f"time_range两个值相同，按照time_point处理: {time_point}")
                except Exception as e:
                    logger.warning(f"解析time_range失败: {e}")
            
            if time_point:
                # 时间点：搜索前后25条记录
                target_timestamp = parse_datetime_to_timestamp(time_point)
                # 获取前后各25条记录，总共50条
                messages_before = get_messages_by_time_in_chat(
                    chat_id=self.chat_id,
                    start_time=0,
                    end_time=target_timestamp,
                    limit=25,
                    limit_mode="latest"
                )
                messages_after = get_messages_by_time_in_chat(
                    chat_id=self.chat_id,
                    start_time=target_timestamp,
                    end_time=float('inf'),
                    limit=25,
                    limit_mode="earliest"
                )
                messages = messages_before + messages_after
            elif time_range:
                # 时间范围：搜索范围内最多50条记录
                start_timestamp, end_timestamp = parse_time_range(time_range)
                messages = get_messages_by_time_in_chat(
                    chat_id=self.chat_id,
                    start_time=start_timestamp,
                    end_time=end_timestamp,
                    limit=50,
                    limit_mode="latest"
                )
            else:
                return "未指定时间参数"
            
            if not messages:
                return "没有找到相关聊天记录"
            
            # 将消息转换为可读格式
            chat_content = build_readable_messages(messages, timestamp_mode="relative")
            
            if not chat_content.strip():
                return "聊天记录为空"
            
            # 使用LLM分析聊天内容并回答问题
            try:
                llm_request = LLMRequest(
                    model_set=model_config.model_task_config.utils_small,
                    request_type="chat_history_analysis"
                )
                
                analysis_prompt = f"""请根据以下聊天记录内容，回答用户的问题。请输出一段平文本，不要有特殊格式。
聊天记录：
{chat_content}

用户问题：{question}

请仔细分析聊天记录，提取与问题相关的信息，并给出准确的答案。如果聊天记录中没有相关信息，无法回答问题，输出"无有效信息"即可，不要输出其他内容。

答案："""
                
                print(f"analysis_prompt: {analysis_prompt}")
                
                
                response, (reasoning, model_name, tool_calls) = await llm_request.generate_response_async(
                    prompt=analysis_prompt,
                    temperature=0.3,
                    max_tokens=256
                )
                
                
                print(f"response: {response}")
                
                if "无有效信息" in response:
                    return ""
                
                return response
                
            except Exception as llm_error:
                logger.error(f"LLM分析聊天记录失败: {llm_error}")
                # 如果LLM分析失败，返回聊天内容的摘要
                if len(chat_content) > 300:
                    chat_content = chat_content[:300] + "..."
                return chat_content
            
        except Exception as e:
            logger.error(f"从聊天记录获取答案失败: {e}")
            return ""

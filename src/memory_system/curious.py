import time
import asyncio
from typing import List, Optional, Tuple
from src.common.logger import get_logger
from src.chat.utils.chat_message_builder import (
    get_raw_msg_before_timestamp_with_chat,
    build_readable_messages_with_id,
)
from src.llm_models.utils_model import LLMRequest
from src.config.config import model_config, global_config
from src.memory_system.questions import global_conflict_tracker
from src.memory_system.memory_utils import parse_md_json

logger = get_logger("curious")


class CuriousDetector:
    """
    好奇心检测器 - 检测聊天记录中的矛盾、冲突或需要提问的内容
    """
    
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.llm_request = LLMRequest(
            model_set=model_config.model_task_config.utils,
            request_type="curious_detector",
        )
    
    async def detect_questions(self, recent_messages: List) -> Optional[str]:
        """
        检测最近消息中是否有需要提问的内容
        
        Args:
            recent_messages: 最近的消息列表
            
        Returns:
            Optional[str]: 如果检测到需要提问的内容，返回问题文本；否则返回None
        """
        try:
            if not recent_messages or len(recent_messages) < 2:
                return None
            
            # 构建聊天内容
            chat_content_block, _ = build_readable_messages_with_id(
                messages=recent_messages,
                timestamp_mode="normal_no_YMD",
                read_mark=0.0,
                truncate=True,
                show_actions=True,
            )
            
            # 检查是否已经有问题在跟踪中
            existing_questions = global_conflict_tracker.get_questions_by_chat_id(self.chat_id)
            if len(existing_questions) > 0:
                logger.debug(f"当前已有{len(existing_questions)}个问题在跟踪中，跳过检测")
                return None
            
            # 构建检测提示词
            prompt = f"""你是一个严谨的聊天内容分析器。请分析以下聊天记录，检测是否存在需要提问的内容。

检测条件：
1. 聊天中存在逻辑矛盾或冲突的信息
2. 有人反对或否定之前提出的信息
3. 存在观点不一致的情况
4. 有模糊不清或需要澄清的概念
5. 有人提出了质疑或反驳

**重要限制：**
- 忽略涉及违法、暴力、色情、政治等敏感话题的内容
- 不要对敏感话题提问
- 只有在确实存在矛盾或冲突时才提问
- 如果聊天内容正常，没有矛盾，请输出：NO

**聊天记录**
{chat_content_block}

请分析上述聊天记录，如果发现需要提问的内容，请用JSON格式输出：
```json
{{
    "question": "具体的问题描述，要完整描述涉及的概念和问题",
    "reason": "为什么需要提问这个问题的理由"
}}
```

如果没有需要提问的内容，请只输出：NO"""

            if global_config.debug.show_prompt:
                logger.info(f"好奇心检测提示词: {prompt}")
            else:
                logger.debug("已发送好奇心检测提示词")

            result_text, _ = await self.llm_request.generate_response_async(prompt, temperature=0.3)
            
            if not result_text:
                return None
            
            result_text = result_text.strip()
            
            # 检查是否输出NO
            if result_text.upper() == "NO":
                logger.debug("未检测到需要提问的内容")
                return None
            
            # 尝试解析JSON
            try:
                questions, reasoning = parse_md_json(result_text)
                if questions and len(questions) > 0:
                    question_data = questions[0]
                    question = question_data.get("question", "")
                    reason = question_data.get("reason", "")
                    
                    if question and question.strip():
                        logger.info(f"检测到需要提问的内容: {question}")
                        logger.info(f"提问理由: {reason}")
                        return question
            except Exception as e:
                logger.warning(f"解析问题JSON失败: {e}")
                logger.debug(f"原始响应: {result_text}")
            
            return None
            
        except Exception as e:
            logger.error(f"好奇心检测失败: {e}")
            return None
    
    async def make_question_from_detection(self, question: str, context: str = "") -> bool:
        """
        将检测到的问题记录到冲突追踪器中
        
        Args:
            question: 检测到的问题
            context: 问题上下文
            
        Returns:
            bool: 是否成功记录
        """
        try:
            if not question or not question.strip():
                return False
            
            # 记录问题到冲突追踪器，并开始跟踪
            await global_conflict_tracker.track_conflict(
                question=question.strip(),
                context=context,
                start_following=False,
                chat_id=self.chat_id
            )
            
            logger.info(f"已记录问题到冲突追踪器: {question}")
            return True
            
        except Exception as e:
            logger.error(f"记录问题失败: {e}")
            return False


async def check_and_make_question(chat_id: str, recent_messages: List) -> bool:
    """
    检查聊天记录并生成问题（如果检测到需要提问的内容）
    
    Args:
        chat_id: 聊天ID
        recent_messages: 最近的消息列表
        
    Returns:
        bool: 是否检测到并记录了问题
    """
    try:
        detector = CuriousDetector(chat_id)
        
        # 检测是否需要提问
        question = await detector.detect_questions(recent_messages)
        
        if question:
            # 记录问题
            success = await detector.make_question_from_detection(question)
            if success:
                logger.info(f"成功检测并记录问题: {question}")
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"检查并生成问题失败: {e}")
        return False

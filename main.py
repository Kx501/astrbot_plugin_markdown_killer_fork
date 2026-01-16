from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import LLMResponse
from astrbot.api import logger
import re

@register("astrbot_plugin_markdown_killer_fork", "Kx501", "移除LLM输出中的Markdown格式", "0.0.5", "https://github.com/Kx501/astrbot_plugin_markdown_killer_fork")
class MarkdownKillerPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        
        # 从配置中读取是否启用移除空行，默认为 False
        self.remove_empty_lines = self.config.get("remove_empty_lines", False)
        
        # 从配置中读取首行缩进设置，默认为 False
        # 如果为 True，则使用两个空格作为缩进
        self.first_line_indent = "  " if self.config.get("first_line_indent", False) else ""
    
    @filter.on_llm_response()
    async def on_llm_resp(self, event: AstrMessageEvent, resp: LLMResponse, *args):
        """
        监听LLM回复，移除Markdown格式
        """
        if not resp or not resp.completion_text:
            return

        original_text = resp.completion_text
        
        cleaned_text = self.remove_markdown(original_text)
        
        if original_text != cleaned_text:
            resp.completion_text = cleaned_text
            # 使用 logger 提醒
            original_preview = original_text[:50].replace('\n', '\\n')
            cleaned_preview = cleaned_text[:50].replace('\n', '\\n')
            log_msg = f"\n[Markdown Killer] --------------------------------------------------\n[Markdown Killer] 检测到Markdown并移除:\n[Markdown Killer] 原文: {original_preview}...\n[Markdown Killer] 处理: {cleaned_preview}...\n[Markdown Killer] --------------------------------------------------"
            logger.warning(log_msg)

    def remove_markdown(self, text: str) -> str:
        """
        移除文本中的Markdown格式
        """
        # 移除代码块 (保留内容)
        # 合并处理: 使用 DOTALL 模式匹配 ```...```，非贪婪匹配
        # 尝试移除语言标识符 (如果后面紧跟空白字符)
        text = re.sub(r"```(?:[a-zA-Z0-9+\-]*\s+)?([\s\S]*?)```", r"\1", text)

        # 移除行内代码 `code` -> code
        text = re.sub(r"`([^`]+)`", r"\1", text)
        
        # 移除粗体/斜体 - 优化以避免误伤数学公式
        # Bold: **text** or __text__
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        
        # Italic: *text* or _text_
        # 严格模式: * 前后不能有空格 (CommonMark 标准)，且 * 必须位于词边界或非单词字符旁
        text = re.sub(r"(^|[^\w\*])\*(?!\s)([^*]+)(?<!\s)\*(?=$|[^\w\*])", r"\1\2", text)
        text = re.sub(r"(^|[^\w_])_(?!\s)([^_]+)(?<!\s)_(?=$|[^\w_])", r"\1\2", text)
        
        # 移除标题 (移除 # 但保留文本)
        text = re.sub(r"^(#{1,6})\s+(.*)", r"\2", text, flags=re.MULTILINE)
        
        # 移除引用 (移除 > 但保留文本)
        text = re.sub(r"^>\s+(.*)", r"\1", text, flags=re.MULTILINE)
        
        # 移除链接 [text](url) -> text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        
        # 移除列表标记 (移除行首的 - 或 *)
        text = re.sub(r"^\s*[-*]\s+(.*)", r"\1", text, flags=re.MULTILINE)
        
        # 如果启用了移除空行功能，则移除空行
        if self.remove_empty_lines:
            # 使用正则表达式移除空行：
            # 1. 将连续的空行（只包含空白字符的行）合并为单个换行符
            # 2. 移除开头和结尾的换行符
            text = re.sub(r'\n\s*\n+', '\n', text)  # 将连续空行合并为单个换行符
            text = re.sub(r'^\n+|\n+$', '', text)   # 移除开头和结尾的换行符
        
        # 如果启用了首行缩进功能，为每个段落的首行添加缩进
        if self.first_line_indent:
            lines = text.split('\n')
            result_lines = []
            
            for i, line in enumerate(lines):
                # 如果当前行不为空，且上一行为空或这是第一行，则这是段落首行
                if line.strip() and (i == 0 or not lines[i-1].strip()):
                    result_lines.append(self.first_line_indent + line)
                else:
                    result_lines.append(line)
            
            text = '\n'.join(result_lines)
        
        return text

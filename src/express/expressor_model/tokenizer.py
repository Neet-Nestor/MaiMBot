import re
from typing import List, Optional, Set

try:
    import jieba
    _HAS_JIEBA = True
except Exception:
    _HAS_JIEBA = False

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
# 匹配纯符号的正则表达式
_SYMBOL_RE = re.compile(r'^[^\w\u4e00-\u9fff]+$')

def simple_en_tokenize(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())

class Tokenizer:
    def __init__(self, stopwords: Optional[Set[str]] = None, use_jieba: bool = True):
        self.stopwords = stopwords or set()
        self.use_jieba = use_jieba and _HAS_JIEBA

    def tokenize(self, text: str) -> List[str]:
        text = (text or "").strip()
        if not text:
            return []
        if self.use_jieba:
            toks = [t.strip().lower() for t in jieba.cut(text) if t.strip()]
        else:
            toks = simple_en_tokenize(text)
        # 过滤掉纯符号和停用词
        return [t for t in toks if t not in self.stopwords and not _SYMBOL_RE.match(t)]
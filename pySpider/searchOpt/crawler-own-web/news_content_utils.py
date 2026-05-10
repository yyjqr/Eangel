import html
import re


PLACEHOLDER_CONTENT_VALUES = {'', 'content', '暂无内容', '暂无摘要'}

# 明显的占位/模板内容前缀（build_article_content 兜底生成的通用句）
_GENERIC_CONTENT_PREFIXES = (
    '这篇科技资讯聚焦',
    '这篇经济资讯聚焦',
    '这篇产品资讯聚焦',
    '这篇资讯聚焦',
)

# 触发 enrichment 的内容长度阈值（字符数）
# 注意：2句话以上且长度 >= 50 即视为充足；低于此值才需要补充
ENRICHMENT_MIN_LENGTH = 50


def clean_plain_text(text: str) -> str:
    if text is None:
        return ''
    text = html.unescape(str(text))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_sentences(text: str):
    cleaned = clean_plain_text(text)
    if not cleaned:
        return []

    # 在中文句末标点后（含紧接无空格的情况）插入分隔，再 split
    spaced = re.sub(r'([。！？!?])(?=[^\s。！？!?\'\"」』])', r'\1 ', cleaned)
    parts = re.split(r'(?<=[。！？!?])\s+|(?<=\.)\s+(?=[A-Z0-9\u4e00-\u9fff])', spaced)
    sentences = []
    seen = set()
    for part in parts:
        part = clean_plain_text(part)
        if not part:
            continue
        lower_part = part.lower()
        if lower_part in seen:
            continue
        seen.add(lower_part)
        sentences.append(part)
    return sentences


def ensure_sentence_end(sentence: str) -> str:
    sentence = clean_plain_text(sentence)
    if not sentence:
        return ''
    if sentence[-1] not in '。！？.!?':
        if re.search(r'[\u4e00-\u9fff]', sentence):
            sentence += '。'
        else:
            sentence += '.'
    return sentence


def needs_content_enrichment(text: str) -> bool:
    cleaned = clean_plain_text(text)
    if cleaned.lower() in PLACEHOLDER_CONTENT_VALUES:
        return True
    # 长度或句子数不够
    sentences = split_sentences(cleaned)
    if len(sentences) < 2 or len(cleaned) < ENRICHMENT_MIN_LENGTH:
        return True
    # 仅有通用占位句
    if cleaned.startswith(_GENERIC_CONTENT_PREFIXES):
        return True
    return False


def build_article_content(title: str, category: str = '', source: str = '', summary: str = '', tags: str = '', keywords: str = '') -> str:
    title = clean_plain_text(title)
    category = clean_plain_text(category) or '资讯'
    source = clean_plain_text(source)
    tags = clean_plain_text(tags)
    keywords = clean_plain_text(keywords)

    sentences = []
    for sentence in split_sentences(summary):
        if len(sentences) >= 4:
            break
        if title and sentence == title:
            continue
        sentence = ensure_sentence_end(sentence)
        if sentence:
            sentences.append(sentence)

    if not sentences and title:
        sentences.append(ensure_sentence_end(f"这篇{category}资讯聚焦于“{title}”的最新进展"))


    return ' '.join(sentences[:4])

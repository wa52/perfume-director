"""Shared ink geometry and drawing for bounded, editable campaign typography."""
import math
import re
from functools import lru_cache

from PIL import ImageDraw, ImageFont


MAX_LINES = 4


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number')
    return value


def validate_style(item, canvas_width):
    """Validate optional text controls; positions and colors remain PosterSpec fields."""
    width = _number(canvas_width, 'canvas_width')
    if width <= 0:
        raise ValueError('canvas_width must be positive')
    size = _number(item['size'], 'size')
    if not 8 <= size <= 240:
        raise ValueError('Text size must be 8..240')
    tracking = _number(item.get('tracking', 0), 'tracking')
    if not -1 <= tracking <= 24:
        raise ValueError('tracking must be between -1 and 24 pixels')
    max_width = _number(item.get('max_width', 0), 'max_width')
    if not 0 <= max_width <= width:
        raise ValueError('max_width must be zero or within canvas width')
    line_height = _number(item.get('line_height', 1.15), 'line_height')
    if not 1 <= line_height <= 2:
        raise ValueError('line_height must be 1..2')
    if item.get('align', 'left') not in ('left', 'center', 'right'):
        raise ValueError('align must be left, center or right')
    if not isinstance(item['text'], str) or len(item['text']) > 2048:
        raise ValueError('text must be a string of at most 2048 characters')
    return item


@lru_cache(maxsize=256)
def _font(path, size):
    return ImageFont.truetype(path, size)


def _line_ops(text, font, tracking):
    # Every glyph shares a baseline. Using anchor='lt' per glyph would lift
    # lowercase letters and punctuation to the height of capitals.
    if not tracking:
        return [(text, 0)] if text else []
    return [(char, round(font.getlength(text[:index + 1]) - font.getlength(char) + index * tracking))
            for index, char in enumerate(text)]


def _ink(ops, font):
    boxes = []
    for text, x in ops:
        mask, offset = font.getmask2(text, anchor='ls')
        box = mask.getbbox()
        if box:
            boxes.append((x + offset[0] + box[0], offset[1] + box[1],
                          x + offset[0] + box[2], offset[1] + box[3]))
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)) if boxes else (0, 0, 0, 0)


def _is_cjk(text):
    return any('\u2e80' <= char <= '\u9fff' or '\uf900' <= char <= '\ufaff' or
               '\u3040' <= char <= '\u30ff' or '\uac00' <= char <= '\ud7af' for char in text)


def _wrap(text, max_width, measure):
    lines = []
    for paragraph in text.split('\n'):
        if not max_width or measure(paragraph) <= max_width:
            lines.append(paragraph)
            continue
        line = ''
        for token in re.findall(r'\S+|\s+', paragraph):
            if token.isspace():
                line += token
                continue
            if measure(line + token) <= max_width:
                line += token
                continue
            if line.strip():
                lines.append(line.rstrip())
                line = ''
            if measure(token) <= max_width:
                line = token
            elif _is_cjk(token):
                # CJK does not require whitespace word boundaries. Never split
                # a Latin word merely to conceal an undersized text frame.
                for part in re.findall(r'[A-Za-z0-9]+|.', token):
                    if measure(part) > max_width:
                        raise ValueError('Unbreakable text exceeds max_width')
                    if line and measure(line + part) > max_width:
                        lines.append(line)
                        line = ''
                    line += part
            else:
                raise ValueError('Unbreakable word exceeds max_width')
        lines.append(line.rstrip())
    if len(lines) > MAX_LINES:
        raise ValueError('Text layout exceeds four lines')
    return lines


def text_layout(item, fallback_font):
    """Return JSON-safe draw operations and their actual ink bounding rectangle.

    x/y denote the top-left of the text frame; max_width=0 keeps one unwrapped
    line unless the copy has explicit newlines. Alignment uses max_width when
    present. The reported bbox is ink, not the empty part of that frame.
    """
    validate_style(item, max(item.get('max_width', 0), 1))
    x, y = round(_number(item['x'], 'x')), round(_number(item['y'], 'y'))
    font_path, size = str(item.get('font', fallback_font)), round(item['size'])
    font = _font(font_path, size)
    tracking = item.get('tracking', 0)
    cache = {}

    def measured(text):
        if text not in cache:
            ops = _line_ops(text, font, tracking)
            cache[text] = (ops, _ink(ops, font))
        return cache[text]

    def width(text):
        box = measured(text)[1]
        return box[2] - box[0]

    lines = _wrap(item['text'], item.get('max_width', 0), width)
    frame_width = item.get('max_width', 0) or max((width(line) for line in lines), default=0)
    align = {'left': 0, 'center': .5, 'right': 1}[item.get('align', 'left')]
    step = size * item.get('line_height', 1.15)
    operations, boxes = [], []
    for index, line in enumerate(lines):
        ops, box = measured(line)
        shift_x = round((frame_width - (box[2] - box[0])) * align) - box[0]
        baseline = round(index * step)
        for text, at in ops:
            operations.append({'text': text, 'xy': [x + shift_x + at, baseline]})
        if box[2] > box[0] and box[3] > box[1]:
            boxes.append([x + shift_x + box[0], baseline + box[1],
                          x + shift_x + box[2], baseline + box[3]])
    if boxes:
        top = min(box[1] for box in boxes)
        for operation in operations:
            operation['xy'][1] += y - top
        bbox = [min(box[0] for box in boxes), y, max(box[2] for box in boxes),
                max(box[3] for box in boxes) + y - top]
    else:
        bbox = [x, y, x, y]
    return {'bbox': bbox, 'lines': lines, 'ops': operations,
            'font_path': font_path, 'font_size': size, 'frame_width': frame_width}


def draw_text(canvas, item, fallback_font):
    """Draw from the same operations used by collision and contrast checks."""
    layout = text_layout(item, fallback_font)
    font = _font(layout['font_path'], layout['font_size'])
    draw = ImageDraw.Draw(canvas)
    for operation in layout['ops']:
        draw.text(tuple(operation['xy']), operation['text'], font=font,
                  fill=item['color'], anchor='ls')
    return layout

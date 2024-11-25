import aiohttp
import base64
import os
import pathlib
from io import BytesIO
from tempfile import NamedTemporaryFile
import asyncio

from plugins.LangBot_Plugin_Text2Image.config import Config
from pkg.core.app import Application

import qrcode
import imgkit
import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.tables import TableExtension
from mdx_math import MathExtension
from charset_normalizer import from_bytes
from pygments.formatters import HtmlFormatter
from pygments.styles.xcode import XcodeStyle

template_html: str = ''
with open(os.path.split(os.path.realpath(__file__))[0] + "/template/template.html", "rb") as f:
    guessed_str = from_bytes(f.read()).best()
    if not guessed_str:
        raise ValueError("无法识别 Markdown 模板 template.html，请检查是否输入有误！")
     # 获取 Pygments 生成的 CSS 样式
    highlight_css = HtmlFormatter(style=XcodeStyle).get_style_defs('.highlight')
    template_html = str(guessed_str).replace("{highlight_css}", highlight_css)


img_path = os.path.split(os.path.realpath(__file__))[0] + "/output.jpg"

class DisableHTMLExtension(markdown.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.deregister('html')
        md.preprocessors.deregister('html_block')


def makeExtension(*args, **kwargs):
    return DisableHTMLExtension(*args, **kwargs)

def md_to_html(text: str) -> str:
    text = text.replace("\n", "  \n")
    extensions = [
        DisableHTMLExtension(),
        MathExtension(enable_dollar_delimiter=True),  # 开启美元符号渲染
        CodeHiliteExtension(linenums=False, css_class='highlight', noclasses=False, guess_lang=True),  # 添加代码块语法高亮
        TableExtension(),
        'fenced_code'
    ]
    md = markdown.Markdown(extensions=extensions)
    h = md.convert(text)
    h = h.replace('&lt;','<')
    h = h.replace('&gt;','>')
    h = h.replace('&ampl','&')
    # 获取 Pygments 生成的 CSS 样式
    css_style = HtmlFormatter(style=XcodeStyle).get_style_defs('.highlight')

    # 将 CSS 样式插入到 HTML 中
    h = f"<style>{css_style}</style>\n{h}"
    return h

async def get_qr_data(text):
    """将 Markdown 文本保存到 Mozilla Pastebin，并获得 URL"""
    async with aiohttp.ClientSession() as session:
        payload = {'expires': '86400', 'format': 'url', 'lexer': '_markdown', 'content': text}
        try:
            async with session.post('https://pastebin.mozilla.org/api/',
                                    data=payload) as resp:
                resp.raise_for_status()
                url = await resp.text()
        except Exception as e:
            url = f"上传失败：{str(e)}"
        image = qrcode.make(url)
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue())
        return "data:image/jpeg;base64," + img_str.decode('utf-8')

async def text2img(text):
    ap: Application
    content = md_to_html(text)
    plugin_path = os.path.split(os.path.realpath(__file__))[0]
    template_folder = os.path.join(plugin_path, "template")
    font_path = os.path.join(plugin_path, Config.font_path)
    html = template_html.replace('{path_texttoimg}', pathlib.Path(template_folder).as_uri()) \
                .replace("{qrcode}", await get_qr_data(text)) \
                .replace("{content}", content) \
                .replace("{font_size_texttoimg}", str(Config.font_size)) \
                .replace("{font_path_texttoimg}", pathlib.Path(font_path).as_uri())
    #imgkit_config = imgkit.config(wkhtmltoimage=True)
    temp_jpg_file = NamedTemporaryFile(mode='w+b', suffix='.png')
    temp_jpg_filename = temp_jpg_file.name
    temp_jpg_file.close()
    try:
        # 调用imgkit将html转为图片
        ok = await asyncio.get_event_loop().run_in_executor(None, imgkit.from_string, html,
                                                                 temp_jpg_filename, {
                                                                    "enable-local-file-access": "",
                                                                    "allow": template_folder,
                                                                    "width": Config.width,  # 图片宽度
                                                                })
                # 调用PIL将图片读取为 JPEG，RGB 格式
        img_base64 = base64.b64encode(open(temp_jpg_filename, 'rb').read()).decode()
        ok = True
    except Exception as e:
        ap.logger.exception(e)
    finally:
        # 删除临时文件
        if os.path.exists(temp_jpg_filename):
            os.remove(temp_jpg_filename)
    return img_base64
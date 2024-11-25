from pkg.plugin.context import register, handler, llm_func, BasePlugin, APIHost, EventContext
from pkg.plugin.events import *  # 导入事件类
from plugins.LangBot_Plugin_Text2Image.text2img import text2img
from pkg.platform.types.message import Image
from plugins.LangBot_Plugin_Text2Image.config import Config


# 注册插件
@register(name="Text2Image", description="根据Markdown模板将LLM返回的信息转成图片", version="0.1", author="Garrise")
class MyPlugin(BasePlugin):

    # 插件加载时触发
    def __init__(self, host: APIHost):
        pass

    # 异步初始化
    async def initialize(self):
        pass

    @handler(NormalMessageResponded)
    async def process(self, ctx: EventContext):
        if Config.open:
            msg = ctx.event.response_text  # 这里的 event 即为 PersonNormalMessageReceived 的对象
            image = await text2img(msg)
            ctx.add_return('reply',[Image(base64=image)])
            ctx.prevent_postorder()
            pass

    # 插件卸载时触发
    def __del__(self):
        pass

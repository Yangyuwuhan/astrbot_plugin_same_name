import aiohttp

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.message.components import Node, Nodes, Plain


class SameNamePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    @filter.command("重名", alias={"samename", "查重名"})
    async def same_name_query(self, event: AstrMessageEvent, name: str):
        """查询全国重名人数和相关信息"""
        try:
            logger.info(f"查询重名: {name}")

            # 获取 API key
            apikey = self.config.get("apikey", "")
            if not apikey:
                yield event.plain_result("请先在插件配置中填写 API 密钥")
                return

            # 获取是否合并转发配置
            merge_forward = self.config.get("merge_forward", False)

            # 获取查询结果
            async with aiohttp.ClientSession() as session:
                url = "https://api-v2.yuafeng.cn/API/name_duplicate_query.php"
                params = {
                    "name": name,
                    "apikey": apikey,
                }
                # 状态码处理
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("code") == 200:
                            result = data.get("data", {})
                            message = await self.format_result(result)
                            if merge_forward:
                                # 使用合并转发方式发送消息
                                bot_id = event.get_self_id()
                                node = Node(
                                    name="重名查询",
                                    uin=bot_id,
                                    content=[Plain(message)],
                                )
                                yield event.chain_result([Nodes(nodes=[node])])
                            else:
                                # 使用普通文本方式发送消息
                                yield event.plain_result(message)
                        else:
                            yield event.plain_result(
                                f"查询失败: {data.get('msg', '未知错误')}"
                            )
                    elif response.status == 403:
                        yield event.plain_result("API 密钥错误或无权限，请检查配置")
                    elif response.status == 429:
                        yield event.plain_result("请求过于频繁，请稍后再试")
                    elif response.status == 404:
                        yield event.plain_result("请求地址错误")
                    elif response.status == 500:
                        yield event.plain_result("服务器内部错误")
                    else:
                        yield event.plain_result(f"请求失败，状态码: {response.status}")
        except Exception as e:
            logger.error(f"重名查询错误: {e}")
            yield event.plain_result(f"查询过程中发生错误: {str(e)}")

    async def format_result(self, data):
        """格式化查询结果"""
        name = data.get("名字", "未知")
        duplicate_count = data.get("全国重名人数", 0)
        duplicate_desc = data.get("重名说明", "")

        # 构建回复消息
        message = "【重名查询结果】\n"
        message += f"名字: {name}\n"
        message += f"全国重名人数: {duplicate_count}\n"
        message += f"{duplicate_desc}\n"

        # 当同名人数为零时，终止下面的解析
        if duplicate_count == 0:
            return message

        # 名字解析
        name_analysis = data.get("名字解析", {})
        comprehensive = name_analysis.get("综合运", "")
        daily = name_analysis.get("日常运", "")
        career = name_analysis.get("事业运", "")
        love = name_analysis.get("爱情运", "")
        hexagram = name_analysis.get("卦象解析", "")

        # 性别占比
        gender_ratio = data.get("性别占比", {})
        male = gender_ratio.get("男性", {})
        female = gender_ratio.get("女性", {})

        # 省份与年龄分布
        province_dist = data.get("省份城市分布", [])
        age_dist = data.get("年龄分布", [])

        # 运势
        message += "\n"
        message += "【名字解析】\n"
        message += f"综合运: {comprehensive}\n"
        message += f"日常运: {daily}\n"
        message += f"事业运: {career}\n"
        message += f"爱情运: {love}\n"
        if hexagram:
            message += f"卦象解析: {hexagram}\n\n"

        message += "【性别占比】\n"
        message += f"男性: {male.get('人数', 0)}人 ({male.get('占比', '0%')})\n"
        message += f"女性: {female.get('人数', 0)}人 ({female.get('占比', '0%')})\n\n"

        if province_dist:
            message += "【省份分布】\n"
            for item in province_dist:
                message += f"{item.get('省份', '未知')}: {item.get('人数', 0)}人\n"
            message += "\n"

        if age_dist:
            message += "【年龄分布】\n"
            for item in age_dist:
                message += f"{item.get('年龄段', '未知')}: {item.get('人数', 0)}人\n"

        return message

    async def terminate(self):
        """插件卸载时的清理工作"""
        pass

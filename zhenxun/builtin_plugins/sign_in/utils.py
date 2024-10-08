import os
import random
from datetime import datetime
from io import BytesIO
from pathlib import Path

import nonebot
import pytz
from nonebot.drivers import Driver

from zhenxun.configs.config import NICKNAME, Config
from zhenxun.configs.path_config import IMAGE_PATH
from zhenxun.models.sign_log import SignLog
from zhenxun.models.sign_user import SignUser
from zhenxun.utils.image_utils import BuildImage
from zhenxun.utils.utils import get_user_avatar

from .config import (
    SIGN_BACKGROUND_PATH,
    SIGN_BORDER_PATH,
    SIGN_RESOURCE_PATH,
    SIGN_TODAY_CARD_PATH,
    level2attitude,
    lik2level,
    lik2relation,
)

driver: Driver = nonebot.get_driver()


@driver.on_startup
async def init_image():
    SIGN_RESOURCE_PATH.mkdir(parents=True, exist_ok=True)
    SIGN_TODAY_CARD_PATH.mkdir(exist_ok=True, parents=True)
    await generate_progress_bar_pic()
    clear_sign_data_pic()


async def get_card(
    user: SignUser,
    nickname: str,
    add_impression: float,
    gold: int | None,
    gift: str,
    is_double: bool = False,
    is_card_view: bool = False,
) -> Path:
    """获取好感度卡片

    参数:
        user: SignUser
        nickname: 用户昵称
        impression: 新增的好感度
        gold: 金币
        gift: 礼物
        is_double: 是否触发双倍.
        is_card_view: 是否展示好感度卡片.

    返回:
        Path: 卡片路径
    """
    user_id = user.user_id
    date = datetime.now().date()
    _type = "view" if is_card_view else "sign"
    file_name = f"{user_id}_{_type}_{date}.png"
    view_name = f"{user_id}_view_{date}.png"
    card_file = Path(SIGN_TODAY_CARD_PATH) / file_name
    if card_file.exists():
        return IMAGE_PATH / "sign" / "today_card" / file_name
    else:
        if add_impression == -1:
            card_file = Path(SIGN_TODAY_CARD_PATH) / view_name
            if card_file.exists():
                return card_file
            is_card_view = True
        return await _generate_card(
            user, nickname, add_impression, gold, gift, is_double, is_card_view
        )


async def _generate_card(
    user: SignUser,
    nickname: str,
    impression: float,
    gold: int | None,
    gift: str,
    is_double: bool = False,
    is_card_view: bool = False,
) -> Path:
    """生成签到卡片

    参数:
        user: SignUser
        nickname: 用户昵称
        impression: 新增的好感度
        gold: 金币
        gift: 礼物
        is_double: 是否触发双倍.
        is_card_view: 是否展示好感度卡片.

    返回:
        Path: 卡片路径
    """
    ava_bk = BuildImage(140, 140, (255, 255, 255, 0))
    ava_border = BuildImage(
        140,
        140,
        background=SIGN_BORDER_PATH / "ava_border_01.png",
    )
    if user.platform == "qq" and (byt := await get_user_avatar(user.user_id)):
        ava = BuildImage(107, 107, background=BytesIO(byt))
    else:
        ava = BuildImage(107, 107, (0, 0, 0))
    await ava.circle()
    await ava_bk.paste(ava, (19, 18))
    await ava_bk.paste(ava_border, center_type="center")
    add_impression = impression
    impression = float(user.impression)
    info_img = BuildImage(250, 150, color=(255, 255, 255, 0), font_size=15)
    level, next_impression, previous_impression = get_level_and_next_impression(
        impression
    )
    interpolation = next_impression - impression
    if level == "9":
        level = "8"
        interpolation = 0
    await info_img.text((0, 0), f"· 好感度等级：{level} [{lik2relation[level]}]")
    await info_img.text((0, 20), f"· {NICKNAME}对你的态度：{level2attitude[level]}")
    await info_img.text((0, 40), f"· 距离升级还差 {interpolation:.2f} 好感度")

    bar_bk = BuildImage(220, 20, background=SIGN_RESOURCE_PATH / "bar_white.png")
    bar = BuildImage(220, 20, background=SIGN_RESOURCE_PATH / "bar.png")
    ratio = 1 - (next_impression - user.impression) / (
        next_impression - previous_impression
    )
    if next_impression == 0:
        ratio = 0
    await bar.resize(width=int(bar.width * ratio) or 1, height=bar.height)
    await bar_bk.paste(bar)
    font_size = 30
    if "好感度双倍加持卡" in gift:
        font_size = 20
    gift_border = BuildImage(
        270,
        100,
        background=SIGN_BORDER_PATH / "gift_border_02.png",
        font_size=font_size,
    )
    await gift_border.text((0, 0), gift, center_type="center")

    bk = BuildImage(
        876,
        424,
        background=SIGN_BACKGROUND_PATH
        / random.choice(os.listdir(SIGN_BACKGROUND_PATH)),
        font_size=25,
    )
    A = BuildImage(876, 274, background=SIGN_RESOURCE_PATH / "white.png")
    line = BuildImage(2, 180, color="black")
    await A.transparent(2)
    await A.paste(ava_bk, (25, 80))
    await A.paste(line, (200, 70))
    nickname_img = await BuildImage.build_text_image(
        nickname, size=50, font_color=(255, 255, 255)
    )
    user_console = await user.user_console
    if user_console and user_console.uid:
        uid = f"{user_console.uid}".rjust(12, "0")
        uid = uid[:4] + " " + uid[4:8] + " " + uid[8:]
    else:
        uid = "XXXX XXXX XXXX"
    uid_img = await BuildImage.build_text_image(
        f"UID: {uid}", size=30, font_color=(255, 255, 255)
    )
    image1 = await bk.build_text_image("Accumulative check-in for", bk.font, size=30)
    image2 = await bk.build_text_image("days", bk.font, size=30)
    sign_day_img = await BuildImage.build_text_image(
        f"{user.sign_count}", size=40, font_color=(211, 64, 33)
    )
    tip_width = image1.width + image2.width + sign_day_img.width + 60
    tip_height = max([image1.height, image2.height, sign_day_img.height])
    tip_image = BuildImage(tip_width, tip_height, (255, 255, 255, 0))
    await tip_image.paste(image1, (0, 7))
    await tip_image.paste(sign_day_img, (image1.width + 7, 0))
    await tip_image.paste(image2, (image1.width + sign_day_img.width + 15, 7))

    lik_text1_img = await BuildImage.build_text_image("当前", size=20)
    lik_text2_img = await BuildImage.build_text_image(
        f"好感度：{user.impression:.2f}", size=30
    )
    watermark = await BuildImage.build_text_image(
        f"{NICKNAME}@{datetime.now().year}", size=15, font_color=(155, 155, 155)
    )
    today_data = BuildImage(300, 300, color=(255, 255, 255, 0), font_size=20)
    if is_card_view:
        today_sign_text_img = await BuildImage.build_text_image("", size=30)
        value_list = (
            await SignUser.annotate()
            .order_by("-impression")
            .values_list("user_id", flat=True)
        )
        index = value_list.index(user.user_id) + 1  # type: ignore
        rank_img = await BuildImage.build_text_image(
            f"* 好感度排名第 {index} 位", size=30
        )
        await A.paste(rank_img, ((A.width - rank_img.width - 32), 20))
        last_log = (
            await SignLog.filter(user_id=user.user_id).order_by("create_time").first()
        )
        last_date = "从未"
        if last_log:
            last_date = last_log.create_time.astimezone(
                pytz.timezone("Asia/Shanghai")
            ).date()
        await today_data.text(
            (0, 0),
            f"上次签到日期：{last_date}",
        )
        await today_data.text((0, 25), f"总金币：{gold}")
        default_setu_prob = (
            Config.get_config("send_setu", "INITIAL_SETU_PROBABILITY") * 100  # type: ignore
        )
        await today_data.text(
            (0, 50),
            f"色图概率：{(default_setu_prob + float(user.impression) if user.impression < 100 else 100):.2f}%",
        )
        await today_data.text((0, 75), f"开箱次数：{(20 + int(user.impression / 3))}")
        _type = "view"
    else:
        await A.paste(gift_border, (570, 140))
        today_sign_text_img = await BuildImage.build_text_image("今日签到", size=30)
        if is_double:
            await today_data.text((0, 0), f"好感度 + {add_impression / 2:.2f} × 2")
        else:
            await today_data.text((0, 0), f"好感度 + {add_impression:.2f}")
        await today_data.text((0, 25), f"金币 + {gold}")
        _type = "sign"
    current_date = datetime.now()
    current_datetime_str = current_date.strftime("%Y-%m-%d %a %H:%M:%S")
    data = current_date.date()
    data_img = await BuildImage.build_text_image(
        f"时间：{current_datetime_str}", size=20
    )
    await bk.paste(nickname_img, (30, 15))
    await bk.paste(uid_img, (30, 85))
    await bk.paste(A, (0, 150))
    # await bk.text((30, 167), "Accumulative check-in for")
    # _x = bk.getsize("Accumulative check-in for")[0] + sign_day_img.width + 45
    # await bk.paste(sign_day_img, (398, 158))
    # await bk.text((_x, 167), "days")
    await bk.paste(tip_image, (10, 167))
    await bk.paste(data_img, (220, 370))
    await bk.paste(lik_text1_img, (220, 240))
    await bk.paste(lik_text2_img, (262, 234))
    await bk.paste(bar_bk, (225, 275))
    await bk.paste(info_img, (220, 305))
    await bk.paste(today_sign_text_img, (550, 180))
    await bk.paste(today_data, (580, 220))
    await bk.paste(watermark, (15, 400))
    await bk.save(SIGN_TODAY_CARD_PATH / f"{user.user_id}_{_type}_{data}.png")
    return IMAGE_PATH / "sign" / "today_card" / f"{user.user_id}_{_type}_{data}.png"


async def generate_progress_bar_pic():
    """
    初始化进度条图片
    """
    bg_2 = (254, 1, 254)
    bg_1 = (0, 245, 246)

    bk = BuildImage(1000, 50)
    img_x = BuildImage(50, 50, color=bg_2)
    await img_x.circle()
    await img_x.crop((25, 0, 50, 50))
    img_y = BuildImage(50, 50, color=bg_1)
    await img_y.circle()
    await img_y.crop((0, 0, 25, 50))
    A = BuildImage(950, 50)
    width, height = A.size

    step_r = (bg_2[0] - bg_1[0]) / width
    step_g = (bg_2[1] - bg_1[1]) / width
    step_b = (bg_2[2] - bg_1[2]) / width

    for y in range(0, width):
        bg_r = round(bg_1[0] + step_r * y)
        bg_g = round(bg_1[1] + step_g * y)
        bg_b = round(bg_1[2] + step_b * y)
        for x in range(0, height):
            await A.point((y, x), fill=(bg_r, bg_g, bg_b))
    await bk.paste(img_y, (0, 0))
    await bk.paste(A, (25, 0))
    await bk.paste(img_x, (975, 0))
    await bk.save(SIGN_RESOURCE_PATH / "bar.png")

    A = BuildImage(950, 50)
    bk = BuildImage(1000, 50)
    img_x = BuildImage(50, 50)
    await img_x.circle()
    await img_x.crop((25, 0, 50, 50))
    img_y = BuildImage(50, 50)
    await img_y.circle()
    await img_y.crop((0, 0, 25, 50))
    await bk.paste(img_y, (0, 0))
    await bk.paste(A, (25, 0))
    await bk.paste(img_x, (975, 0))
    await bk.save(SIGN_RESOURCE_PATH / "bar_white.png")


def get_level_and_next_impression(impression: float) -> tuple[str, int, int]:
    """获取当前好感等级与下一等级的差距

    参数:
        impression: 好感度

    返回:
        tuple[str, int, int]: 好感度等级中文，好感度等级，下一等级好感差距
    """
    if impression == 0:
        return lik2level[10], 10, 0
    keys = list(lik2level.keys())
    for i in range(len(keys)):
        if impression > keys[i]:
            return lik2level[keys[i]], keys[i - 1], keys[i]
    return lik2level[10], 10, 0


def clear_sign_data_pic():
    """
    清空当前签到图片数据
    """
    date = datetime.now().date()
    for file in os.listdir(SIGN_TODAY_CARD_PATH):
        if str(date) not in file:
            os.remove(SIGN_TODAY_CARD_PATH / file)

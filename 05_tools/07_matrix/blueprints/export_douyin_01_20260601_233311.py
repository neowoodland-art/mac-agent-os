# ═══════════════════════════════════════════════
# 录制生成: douyin_01
# 步骤数: 5
# ═══════════════════════════════════════════════

    # 步骤 1: 查看主页
    elif op == "custom_view_profile":
        # 点击坐标 (42, 265)
        await conn.page.mouse.click(42, 265)
        await asyncio.sleep(2)
        result = "clicked"

    # 步骤 2: 点击 (166,200) <DIV.KZM6X94T>
    elif op == "custom_click":
        # 点击坐标 (166, 200)
        await conn.page.mouse.click(166, 200)
        await asyncio.sleep(2)
        result = "clicked"

    # 步骤 3: 页面内容变化 (1 events)
    elif op == "custom_action":
        # TODO: 实现 页面内容变化 (1 events) 的自动化操作
        await asyncio.sleep(2)
        result = f"TODO({at})"

    # 步骤 4: 查看主页
    elif op == "custom_view_profile":
        # 点击坐标 (405, 23)
        await conn.page.mouse.click(405, 23)
        await asyncio.sleep(2)
        result = "clicked"

    # 步骤 5: 点击 (461,26) <SPAN>
    elif op == "custom_click":
        # 点击坐标 (461, 26)
        await conn.page.mouse.click(461, 26)
        await asyncio.sleep(2)
        result = "clicked"

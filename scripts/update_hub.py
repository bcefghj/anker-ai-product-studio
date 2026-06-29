#!/usr/bin/env python3
"""把服务器导航 hub 里的"项目二"占位卡片替换为 Anker 项目的"运行中"卡片。

幂等：已替换则跳过。凭据从环境变量读取（SERVER_HOST/SERVER_USER/SERVER_PASS）。
"""
from __future__ import annotations

import os
import sys

HUB = "/var/www/hub/index.html"

NEW_CARD = """    <div class="proj live">
      <div class="face">◆◇◆</div>
      <span class="badge on">● 运行中</span>
      <h3>Anker AI 原生产品定义系统</h3>
      <div class="desc">让 AI 做超级智囊·用户替身·行业专家，从真实评论端到端跑出产品提案(PR/FAQ)，并量化对比"AI 驱动 vs 经验拍脑袋"。2026 AI 先锋未来人才大赛·安克命题参赛作品。</div>
      <a class="enter" href="/anker/">查看项目 →</a>
      <div class="links">
        <a href="/anker/app/" target="_blank">在线 Demo</a>
        <a href="https://github.com/bcefghj/anker-ai-product-studio" target="_blank">GitHub</a>
      </div>
    </div>"""


def main() -> int:
    import paramiko

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(os.environ["SERVER_HOST"], username=os.environ.get("SERVER_USER", "root"),
                password=os.environ["SERVER_PASS"], timeout=30)
    sftp = cli.open_sftp()
    with sftp.open(HUB, "r") as f:
        html = f.read().decode("utf-8")

    if "/anker/" in html and "Anker AI 原生" in html:
        print("hub 已包含 anker 卡片，跳过。")
        return 0

    anchor = "<h3>项目二</h3>"
    if anchor not in html:
        print("未找到 '项目二' 占位卡片，跳过（请手动检查 hub）。")
        return 1
    pos = html.index(anchor)
    start = html.rindex('<div class="proj soon">', 0, pos)
    end = html.index("</div>", html.index("敬请期待", pos)) + len("</div>")
    end = html.index("</div>", end) + len("</div>")  # 卡片外层闭合
    new_html = html[:start] + NEW_CARD + html[end:]

    with sftp.open(HUB, "w") as f:
        f.write(new_html)
    sftp.close()
    cli.close()
    print(f"hub 已更新：注入 anker 运行中卡片（{len(new_html)} 字节）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

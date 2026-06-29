#!/usr/bin/env python3
"""一键部署到服务器（项目二：anker, 端口 8766），不影响已有项目（小念/xiaonian）。

凭据从环境变量读取（绝不写入仓库）：
    SERVER_HOST, SERVER_USER, SERVER_PASS, [MINIMAX_API_KEY]

用法：
    SERVER_HOST=47.119.112.225 SERVER_USER=root SERVER_PASS=*** \
    MINIMAX_API_KEY=*** python3 scripts/deploy.py

依赖：paramiko（pip install paramiko）。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_URL = "https://github.com/bcefghj/anker-ai-product-studio.git"
APP_DIR = "/opt/projects/anker"
WWW_DIR = "/var/www/anker"
PORT = 8766
NGINX_CONF = "/etc/nginx/sites-available/projects"
# 国内服务器对 PyPI 官方源不稳定，默认走清华镜像（可用 PIP_INDEX 覆盖）
PIP_INDEX = os.environ.get("PIP_INDEX", "https://pypi.tuna.tsinghua.edu.cn/simple")
PROJECT_ROOT = Path(__file__).resolve().parents[1]

NGINX_BLOCK = """    # ---- 项目二：anker (AI 原生产品定义系统) ----
    location = /anker/app { return 301 /anker/app/; }
    location /anker/app/ {
        proxy_pass http://127.0.0.1:8766/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
    location = /anker { return 301 /anker/; }
    location /anker/ {
        alias /var/www/anker/;
        index index.html;
        try_files $uri $uri/ /var/www/anker/index.html;
    }

"""

SYSTEMD_UNIT = """[Unit]
Description=Anker AI Native Product Definition Studio
After=network.target

[Service]
WorkingDirectory=/opt/projects/anker
EnvironmentFile=-/opt/projects/anker/.env
ExecStart=/opt/projects/anker/.venv/bin/python run.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("缺少 paramiko：pip install paramiko")
        return 1

    host = os.environ["SERVER_HOST"]
    user = os.environ.get("SERVER_USER", "root")
    password = os.environ["SERVER_PASS"]
    minimax_key = os.environ.get("MINIMAX_API_KEY", "")

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(host, username=user, password=password, timeout=30)

    def run(cmd: str, quiet: bool = False) -> str:
        stdin, stdout, stderr = cli.exec_command(cmd, timeout=600)
        out = stdout.read().decode("utf-8", "ignore")
        err = stderr.read().decode("utf-8", "ignore")
        rc = stdout.channel.recv_exit_status()
        if not quiet:
            tag = "OK" if rc == 0 else f"RC={rc}"
            print(f"[{tag}] $ {cmd}")
            if out.strip():
                print("  " + out.strip().replace("\n", "\n  ")[:1500])
            if err.strip() and rc != 0:
                print("  ERR: " + err.strip().replace("\n", "\n  ")[:800])
        return out

    def put_file(remote: str, content: str) -> None:
        sftp = cli.open_sftp()
        with sftp.open(remote, "w") as f:
            f.write(content)
        sftp.close()
        print(f"[OK] 写入 {remote} ({len(content)} 字节)")

    print("\n===== 0. 预检（确认不碰已有项目）=====")
    run("systemctl is-active xiaonian.service nginx || true")
    run("ss -ltnp | grep ':8766' || echo '8766 端口空闲'")

    print("\n===== 1. 打包并上传代码（绕过服务器 GitHub 访问不稳定）=====")
    tar_path = Path(tempfile.gettempdir()) / "anker_deploy.tgz"
    # 注意：不要排除名为 assets 的目录，否则会误删源码包 infrastructure/assets/
    # COPYFILE_DISABLE=1：禁止 macOS bsdtar 生成 ._* AppleDouble 伴随文件
    env = {**os.environ, "COPYFILE_DISABLE": "1"}
    subprocess.run(
        ["tar", "czf", str(tar_path),
         "--exclude=.git", "--exclude=.venv", "--exclude=runs",
         "--exclude=__pycache__", "--exclude=.env", "--exclude=node_modules",
         "--exclude=data/processed", "-C", str(PROJECT_ROOT), "."],
        check=True, env=env,
    )
    print(f"[OK] 本地打包 {tar_path} ({tar_path.stat().st_size} 字节)")
    sftp = cli.open_sftp()
    sftp.put(str(tar_path), "/tmp/anker_deploy.tgz")
    sftp.close()
    print("[OK] 上传到 /tmp/anker_deploy.tgz")
    run(f"mkdir -p {APP_DIR} && tar xzf /tmp/anker_deploy.tgz -C {APP_DIR} && "
        f"find {APP_DIR} -name '._*' -delete && ls {APP_DIR} | head")

    print("\n===== 2. venv + 依赖（清华镜像）=====")
    run("which python3 && python3 --version")
    run(f"cd {APP_DIR} && (python3 -m venv .venv || (apt-get update && apt-get install -y python3-venv && python3 -m venv .venv))")
    run(f"cd {APP_DIR} && .venv/bin/pip install -q --upgrade pip -i {PIP_INDEX} && "
        f".venv/bin/pip install -q -r requirements.txt -i {PIP_INDEX} && echo deps-ok")

    print("\n===== 3. 样本数据 =====")
    run(f"cd {APP_DIR} && .venv/bin/python data/make_sample.py | tail -2")

    print("\n===== 4. 写 .env（不入 git）=====")
    env_content = (
        f"ANKER_LLM_PROVIDER=offline\n"
        f"PORT={PORT}\n"
        f"MINIMAX_API_KEY={minimax_key}\n"
        f"MINIMAX_BASE_URL=https://api.minimax.io/v1\n"
        f"MINIMAX_MODEL=MiniMax-M3\n"
    )
    put_file(f"{APP_DIR}/.env", env_content)

    print("\n===== 5. systemd 服务 =====")
    put_file("/etc/systemd/system/anker.service", SYSTEMD_UNIT)
    run("systemctl daemon-reload && systemctl enable anker.service && systemctl restart anker.service")
    run("sleep 2 && systemctl is-active anker.service")

    print("\n===== 6. 落地静态宣传页 =====")
    run(f"mkdir -p {WWW_DIR}")
    landing = (Path(__file__).resolve().parents[1] / "web" / "landing" / "index.html").read_text(encoding="utf-8")
    put_file(f"{WWW_DIR}/index.html", landing)

    print("\n===== 7. nginx 路由（幂等插入）=====")
    conf = run(f"cat {NGINX_CONF}", quiet=True)
    if "/anker/app/" in conf:
        print("  anker 路由已存在，跳过插入。")
    else:
        marker = None
        for cand in ["    # ---- 根导航 hub", "    # ---- 根路径", "    location / {"]:
            if cand in conf:
                marker = cand
                break
        if marker:
            conf = conf.replace(marker, NGINX_BLOCK + marker, 1)
            put_file(NGINX_CONF, conf)
            print(f"  已在 '{marker.strip()}' 之前插入 anker 路由。")
        else:
            print("  !! 未找到根路径标记，未自动插入，请手动检查 nginx 配置。")
    run("nginx -t && systemctl reload nginx")

    print("\n===== 8. 健康检查 =====")
    run("curl -s -o /dev/null -w 'local-app %{http_code}\\n' http://127.0.0.1:8766/api/health")
    run("curl -s -o /dev/null -w 'hub %{http_code}\\n' http://127.0.0.1/")
    run("curl -s -o /dev/null -w 'xiaonian %{http_code}\\n' http://127.0.0.1/xiaonian/")
    run("curl -s -o /dev/null -w 'anker-landing %{http_code}\\n' http://127.0.0.1/anker/")
    run("curl -s -o /dev/null -w 'anker-demo %{http_code}\\n' http://127.0.0.1/anker/app/")
    run("curl -s http://127.0.0.1/anker/app/api/health")

    cli.close()
    print("\n部署完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""在服务器上执行一条命令（运维/诊断用）。凭据从环境变量读取，不写入仓库。

    SERVER_HOST=.. SERVER_USER=root SERVER_PASS=.. python3 scripts/server_exec.py "命令"
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    import paramiko

    cmd = " ".join(sys.argv[1:])
    if not cmd:
        print("用法: server_exec.py '<command>'")
        return 2
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(os.environ["SERVER_HOST"], username=os.environ.get("SERVER_USER", "root"),
                password=os.environ["SERVER_PASS"], timeout=30)
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=600)
    out = stdout.read().decode("utf-8", "ignore")
    err = stderr.read().decode("utf-8", "ignore")
    rc = stdout.channel.recv_exit_status()
    sys.stdout.write(out)
    if err.strip():
        sys.stderr.write("\n[stderr]\n" + err)
    cli.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())

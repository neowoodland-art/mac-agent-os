#!/usr/bin/env python3
"""
SOCKS5 本地转发器
把本地无鉴权 SOCKS5 → 转发到远程有鉴权 SOCKS5
解决 Firefox/Camoufox 不支持 SOCKS5 密码认证的问题

用法:  python socks5_forwarder.py [本地端口]
启动后修改 identity 的 proxy 为 socks5://127.0.0.1:10800
"""
import asyncio, sys, struct, os, signal

# ─── 远程代理（天行） ───
REMOTE_HOST = "36.212.9.145"
REMOTE_PORT = 3570
REMOTE_USER = "iiiaaazh123"
REMOTE_PASS = "wqshyuwftc!@#123"

# ─── 本地监听 ───
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10800

async def socks5_forward(client_reader, client_writer):
    """处理一个 SOCKS5 客户端连接"""
    peer = client_writer.get_extra_info('peername')
    try:
        # ── 1. 握手 ──
        greeting = await client_reader.readexactly(2)
        ver, nmethods = struct.unpack('!BB', greeting)
        methods = await client_reader.readexactly(nmethods)
        # 回应：支持无鉴权
        client_writer.write(struct.pack('!BB', 0x05, 0x00))
        await client_writer.drain()

        # ── 2. 请求 ──
        request = await client_reader.readexactly(4)
        ver, cmd, rsv, atyp = struct.unpack('!BBBB', request)
        if cmd != 0x01:  # 只支持 CONNECT
            client_writer.write(struct.pack('!BBBB', 0x05, 0x07, 0x00, 0x01) + b'\x00' * 6)
            await client_writer.drain()
            return

        if atyp == 0x01:  # IPv4
            addr = await client_reader.readexactly(4)
            dest_host = '.'.join(str(b) for b in addr)
        elif atyp == 0x03:  # 域名
            length = await client_reader.readexactly(1)
            dest_host = (await client_reader.readexactly(length[0])).decode()
        else:
            return

        dest_port = struct.unpack('!H', await client_reader.readexactly(2))[0]

        # ── 3. 连接远程 SOCKS5（带鉴权） ───
        remote_reader, remote_writer = await asyncio.open_connection(REMOTE_HOST, REMOTE_PORT)

        # 远程握手：用户名密码鉴权
        remote_writer.write(struct.pack('!BB', 0x05, 0x02) + struct.pack('BB', 0x00, 0x02))
        await remote_writer.drain()
        auth_resp = await remote_reader.readexactly(2)
        if auth_resp[1] == 0x02:  # 需要用户名密码
            user_bytes = REMOTE_USER.encode()
            pass_bytes = REMOTE_PASS.encode()
            auth_pkt = struct.pack('!B', 0x01) + struct.pack('!B', len(user_bytes)) + user_bytes + struct.pack('!B', len(pass_bytes)) + pass_bytes
            remote_writer.write(auth_pkt)
            await remote_writer.drain()
            auth_result = await remote_reader.readexactly(2)
            if auth_result[1] != 0x00:
                raise Exception("远程鉴权失败")

        # 发送 CONNECT 请求到远程
        if atyp == 0x01:  # IPv4
            req = struct.pack('!BBBB', 0x05, 0x01, 0x00, 0x01) + addr + struct.pack('!H', dest_port)
        elif atyp == 0x03:  # 域名
            host_bytes = dest_host.encode()
            req = struct.pack('!BBBB', 0x05, 0x01, 0x00, 0x03) + struct.pack('!B', len(host_bytes)) + host_bytes + struct.pack('!H', dest_port)

        remote_writer.write(req)
        await remote_writer.drain()
        resp = await remote_reader.readexactly(4)
        if resp[1] != 0x00:
            raise Exception(f"远程连接失败: {resp[1]}")

        # 读取剩余响应
        atyp_resp = resp[3]
        if atyp_resp == 0x01:
            await remote_reader.readexactly(6)
        elif atyp_resp == 0x03:
            length = await remote_reader.readexactly(1)
            await remote_reader.readexactly(length[0] + 2)

        # 回复客户端成功
        client_writer.write(struct.pack('!BBBB', 0x05, 0x00, 0x00, 0x01) + b'\x00' * 6)
        await client_writer.drain()

        # ── 4. 双向转发 ──
        async def forward(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except:
                pass
            finally:
                try: dst.close()
                except: pass

        await asyncio.gather(
            forward(client_reader, remote_writer),
            forward(remote_reader, client_writer),
        )

    except Exception as e:
        print(f"  ⚠️  {peer}: {e}")
    finally:
        try: client_writer.close()
        except: pass

async def main():
    # 打印 PID 方便后续结束进程
    print(f"socks5://{LOCAL_HOST}:{LOCAL_PORT}")
    print(f"  → {REMOTE_HOST}:{REMOTE_PORT} (鉴权转发)")
    print(f"  PID: {os.getpid()}")

    server = await asyncio.start_server(socks5_forward, LOCAL_HOST, LOCAL_PORT)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  ⛔ 转发器已停止")

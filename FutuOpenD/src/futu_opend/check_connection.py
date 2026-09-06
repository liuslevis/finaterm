"""Check connectivity and login state for a running Futu OpenD instance."""

import os
import socket

import futu as ft


def main() -> int:
    host = os.getenv("FUTU_OPEND_HOST", "127.0.0.1")
    port = int(os.getenv("FUTU_OPEND_PORT", "11111"))

    try:
        with socket.create_connection((host, port), timeout=2):
            pass
    except OSError as exc:
        print(f"OpenD is not accepting API connections at {host}:{port}: {exc}")
        print("Complete login in the OpenD GUI and confirm its API port is enabled.")
        return 1

    quote_ctx = ft.OpenQuoteContext(host=host, port=port)

    try:
        ret, state = quote_ctx.get_global_state()
        if ret != ft.RET_OK:
            print(f"OpenD connection check failed: {state}")
            return 1

        print(f"Connected to OpenD at {host}:{port}")
        print(f"Server version: {state.get('server_ver', 'unknown')}")
        print(f"Quote login: {state.get('qot_logined', 'unknown')}")
        print(f"Trade login: {state.get('trd_logined', 'unknown')}")
        return 0
    finally:
        quote_ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())

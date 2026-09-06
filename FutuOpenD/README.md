# Futu OpenD with uv

This project provides an isolated Python environment for the Futu OpenAPI SDK.
OpenD itself runs as the official Windows GUI application and listens on
`127.0.0.1:11111` by default.

## First-time setup

1. Complete the OpenD installer that was launched.
2. Sign in inside the OpenD GUI. Do not save account passwords in this repository.
3. Confirm the GUI shows API access on `127.0.0.1:11111`.
4. Check the connection:

   ```powershell
   uv run futu-check
   ```

## Environment management

Install or refresh the locked environment:

```powershell
uv sync
```

Run a Python file with the managed environment:

```powershell
uv run python .\your_script.py
```

To use another OpenD host or port for the current PowerShell session:

```powershell
$env:FUTU_OPEND_HOST = "127.0.0.1"
$env:FUTU_OPEND_PORT = "11111"
uv run futu-check
```

Keep OpenD bound to localhost unless remote access is explicitly required and
secured according to the official private-key and SSL requirements.

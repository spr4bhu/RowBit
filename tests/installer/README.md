# Installer tests

`setup-toolchain.sh` without installing anything: `python3 -m pytest tests/installer`

| File | What it checks |
|---|---|
| `test_prerequisites.py` | Stops with instructions when Homebrew or Nix is missing. |

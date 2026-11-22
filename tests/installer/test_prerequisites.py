import os
import subprocess

SETUP = os.path.join(os.environ["ROWBIT_ROOT"], "scripts", "setup-toolchain.sh")


def run_setup(path):
    return subprocess.run(["/bin/bash", SETUP], env={"PATH": path, "HOME": os.environ["HOME"]},
                          capture_output=True, text=True)


def test_stops_when_homebrew_missing():
    result = run_setup("/usr/bin:/bin")
    assert result.returncode == 1
    assert "error: Homebrew not found" in result.stderr


def test_stops_when_nix_missing():
    result = run_setup("/opt/homebrew/bin:/usr/bin:/bin")
    assert result.returncode == 1
    assert "error: Nix not found" in result.stderr

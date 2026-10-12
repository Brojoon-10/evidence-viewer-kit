# -*- coding: utf-8 -*-
"""지금 띄운 근거를 이름 붙여 저장하고, 다시 띄운다.

  python -m evkit.pointer_log --project P save <이름>   → state_dir/history/<이름>.json + state_dir/evidence_log.md 에 표
  python -m evkit.pointer_log --project P show <이름>   → 저장한 근거를 다시 근거 화면에
  python -m evkit.pointer_log --project P list

같은 초안 키가 여러 기록에 있으면, 묶음 보기(근거 화면 '고른 묶음')는 가장 최근에 저장한 기록을 쓴다."""
import argparse
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from evkit.project import find_project, read_json, write_json, KEY  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["save", "show", "list"])
    ap.add_argument("name", nargs="?")
    ap.add_argument("--project")
    a = ap.parse_args()
    P = find_project(a.project)
    if a.cmd == "list":
        for h in P.histories():
            print("%-40s %3d곳  %s" % (h["name"], len(h["marks"]), h["msg"]))
        return
    if not a.name or not re.match(r"^[\w.-]+$", a.name, re.UNICODE):
        raise SystemExit("이름은 글자·숫자·_-. 만 (띄어쓰기 없이)")
    path = os.path.join(P.history_dir, a.name + ".json")
    if a.cmd == "save":
        p = read_json(P.pointer_file, {"marks": []})
        write_json(path, p)
        docs = P.cfg["docs"]
        rows = ["## %s" % a.name, "",
                "저장 %s · %s · 다시 보기: `python -m evkit.pointer_log show %s`" % (time.strftime("%Y-%m-%d %H:%M"), p.get("msg", ""), a.name), "",
                "| 초안 키 | 내용 | 근거 문서 | 쪽 |", "|---|---|---|---|"]
        for m in p.get("marks", []):
            note = m.get("note", "")
            r = KEY.match(note)
            key, txt = (r.group(1), note[r.end():].strip()) if r else ("", note)
            rows.append("| %s | %s | %s | %s |" % (key, txt.replace("|", "/"), docs.get(m["doc"], {}).get("name", m["doc"]), m["page"]))
        md = os.path.join(P.state, "evidence_log.md")
        old = open(md, encoding="utf-8").read() if os.path.exists(md) else "# 근거 기록\n\n초안 줄(키)과 원문 근거 위치.\n\n"
        old = re.sub(r"## %s\n.*?(?=\n## |\Z)" % re.escape(a.name), "", old, flags=re.S).rstrip() + "\n\n"
        with open(md, "w", encoding="utf-8") as f:
            f.write(old + "\n".join(rows) + "\n")
        print("saved", a.name, len(p.get("marks", [])))
    else:
        p = read_json(path, None)
        if p is None:
            raise SystemExit("없음: " + a.name)
        cur = read_json(P.pointer_file, {"seq": 0})
        p["seq"] = cur.get("seq", 0) + 1
        p["time"] = time.strftime("%H:%M:%S")
        write_json(P.pointer_file, p)
        print("shown", a.name)


if __name__ == "__main__":
    main()

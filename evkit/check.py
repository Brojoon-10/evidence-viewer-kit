"""Check a project: every draft bullet has a key, every key has saved evidence, every saved mark is sane.

  python -m evkit.check --project P [--fix-list out.json]

Reports (exit 1 if any problem):
  - draft bullet lines with no {@key}   -> clicking them shows nothing; every bullet must link to evidence
  - draft keys with no saved evidence (lines marked {todo} are excused)
  - saved marks whose key is not in any draft (stale)
  - marks that cover the whole page, or span both columns on a two-column page
  - marks whose doc/page is out of range
  - marks saved before `spec` was recorded (cannot be re-pointed automatically)
Run it after every `pointer_log save`. A clean check means the user can click any line and see its evidence.
"""
import argparse, glob, json, os, re, sys

import pymupdf

from evkit.point import spans_columns
from evkit.project import find_project


def main():
    ap = argparse.ArgumentParser(description="초안·근거 검사")
    ap.add_argument("--project")
    ap.add_argument("--fix-list")
    a = ap.parse_args()
    P = find_project(a.project)
    problems = []

    # draft keys
    keys_in_draft, todo_keys = {}, set()
    for d in P.cfg["drafts"]:
        path = P.abs(d["file"])
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            if line.lstrip().startswith("<!--"):  # 설명 주석의 {@키} 예시는 무시
                continue
            if re.match(r"^\s*[-*] ", line) and "{@" not in line:  # 본문 줄(글머리표)은 모두 키가 있어야 클릭 시 근거가 뜬다
                problems.append(("키 없는 줄", d["file"] + ":" + str(i), line.strip()[:40]))
            for k in re.findall(r"\{@([\w.-]+)\}", line):
                keys_in_draft[k] = (d["file"], i)
                if "{todo}" in line:
                    todo_keys.add(k)

    # saved marks
    have = {}
    docs = {}
    nospec = 0
    for h in sorted(glob.glob(os.path.join(P.state, "history", "*.json"))):
        H = json.load(open(h, encoding="utf-8"))
        hname = os.path.basename(h)
        for m in H["marks"]:
            key = (re.match(r"^\[([\w.-]+)\]", m.get("note", "")) or [None, None])[1]
            if not key:
                problems.append(("키 없음", hname, m.get("note", "")[:40])); continue
            have.setdefault(key, []).append(hname)
            if m["doc"] not in P.cfg["docs"]:
                problems.append(("문서키 없음", hname, key, m["doc"])); continue
            if m["doc"] not in docs:
                docs[m["doc"]] = pymupdf.open(P.doc_path(m["doc"]))
            D = docs[m["doc"]]
            if not (1 <= m["filepage"] <= len(D)):
                problems.append(("쪽 범위 밖", hname, key, m["doc"], m["filepage"])); continue
            pg = D[m["filepage"] - 1]
            spec = m.get("spec", "")
            for r in m["rects"]:
                w, hgt = r[2] - r[0], r[3] - r[1]
                if w > 0.9 * pg.rect.width and hgt > 0.9 * pg.rect.height:
                    problems.append(("쪽 전체", hname, key, m["doc"], m["page"]))
                elif (spec.partition("=")[0] in ("find", "para", "word", "after", "before", "") and spans_columns(pg, r)
                      and not spec.startswith("box=") and not (m["filepage"] == 1 and r[3] < 0.3 * pg.rect.height)):  # 1쪽 상단 제목은 원래 넓음
                    # spec 없는 옛 기록(빈 문자열)은 칼럼 걸침이면 의심으로 표시
                    problems.append(("칼럼 걸침", hname, key, m["doc"], m["page"], "spec 없음" if not spec else spec[:30]))
            if not spec:
                nospec += 1

    for k, (f, i) in sorted(keys_in_draft.items()):
        if k not in have and k not in todo_keys:
            problems.append(("근거 없음", f + ":" + str(i), k))
    for k in sorted(have):
        if k not in keys_in_draft:
            problems.append(("초안에 없는 키", ",".join(sorted(set(have[k]))), k))

    from collections import Counter
    c = Counter(p[0] for p in problems)
    print("초안 키 %d개 (todo %d), 근거 있는 키 %d개, 저장 묶음 %d개" % (len(keys_in_draft), len(todo_keys), len(have),
          len(glob.glob(os.path.join(P.state, "history", "*.json")))))
    print("spec 없는 옛 기록(재생성 불가, 정보): %d" % nospec)
    for kind, n in c.items():
        print("- %s: %d" % (kind, n))
    for p in problems:
        print("  ", " | ".join(str(x) for x in p))
    if a.fix_list:
        json.dump(problems, open(a.fix_list, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

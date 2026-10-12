# -*- coding: utf-8 -*-
"""근거 위치를 찍어 근거 화면에 띄운다(에이전트·사람 모두 사용).

사용:
  python -m evkit.point --project P --msg "설명" "문서키|쪽|위치|메모" ["문서키|쪽|위치|메모" ...]
  python -m evkit.point --project P --clear          지금 표시 지우기
  python -m evkit.point --project P --show-user      사람이 근거 화면에서 그린 상자 읽기
  python -m evkit.point --project P --check ...      표시와 함께 확인용 그림(state_dir/check/*.png)도 만듦

위치:
  find=글자     그 글자가 들어 있는 줄 전체 (;; 로 여러 글자를 이으면 그 줄들을 한 상자로)
  para=글자     그 글자가 들어 있는 문단 전체
  sec=제목글자   그 제목부터 같은 단계의 다음 제목 전까지
  after=글자    그 줄 바로 아래 그림·수식
  before=글자   그 줄 바로 위 그림·수식(그림 제목으로 그림 잡기)
  fig=캡션글자   캡션 위 그림 + 캡션
  word=글자     찾은 글자 조각만
  box=x0,y0,x1,y1  쪽을 0~1로 본 비율 좌표
  page          쪽 전체

메모를 "[초안키] 설명" 으로 쓰면 초안의 {@초안키} 줄과 이어진다.
쪽은 원본 쪽 번호(project.json 의 first_page 기준)."""
import argparse
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from evkit.project import find_project, read_json, write_json  # noqa: E402

LETTERS = re.compile(r"[^\W\d_]", re.UNICODE)


def union(rects):
    return [min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)]


def page_items(pg, clip, skip):
    """쪽 안의 글 줄과 그림·수식 덩어리. 글자가 거의 없는 줄은 수식·기호로 본다."""
    lines, objs = [], []
    for b in pg.get_text("dict")["blocks"]:
        bb = list(b["bbox"])
        if bb[3] < clip[1] + 1 or bb[1] > clip[3]:
            continue
        if b["type"] == 1:
            objs.append(bb)
            continue
        for l in b["lines"]:
            text = "".join(s["text"] for s in l["spans"]).strip()
            if not text:
                continue
            if skip and skip.search(text):
                continue
            (lines.append({"bbox": list(l["bbox"]), "text": text}) if len(LETTERS.findall(text)) >= 2
             else objs.append(list(l["bbox"])))
    for dr in pg.get_drawings():  # 벡터 그림(차트·도형)도 그림 덩어리로. 가는 선(표 테두리 등)은 뺀다
        r = dr["rect"]
        if r.width > 20 and r.height > 20 and r.y1 > clip[1] and r.y0 < clip[3]:
            objs.append([r.x0, r.y0, r.x1, r.y1])
    lines.sort(key=lambda x: (round(x["bbox"][1] / 4), x["bbox"][0]))
    merged = []  # 같은 높이 조각(수식 때문에 끊긴 줄)을 한 줄로
    for ln in lines:
        if merged:
            p = merged[-1]["bbox"]
            cy = (ln["bbox"][1] + ln["bbox"][3]) / 2
            if p[1] - 1 <= cy <= p[3] + 1:
                merged[-1] = {"bbox": union([p, ln["bbox"]]), "text": merged[-1]["text"] + " " + ln["text"]}
                continue
        merged.append(ln)
    merged.sort(key=lambda x: x["bbox"][1])
    return merged, objs


def lines_hit(pg, lines, needle):
    hits = pg.search_for(needle)
    out = []
    for ln in lines:
        lb = ln["bbox"]
        for h in hits:
            cy = (h.y0 + h.y1) / 2
            if lb[1] - 1 <= cy <= lb[3] + 1 and h.x1 > lb[0] and h.x0 < lb[2]:
                out.append(ln)
                break
    if not out:  # 양쪽 맞춤 등으로 못 찾으면 띄어쓰기를 빼고 줄 단위로 비교
        key = re.sub(r"\s+", "", needle)
        out = [ln for ln in lines if key and key in re.sub(r"\s+", "", ln["text"])]
    return out, hits


HEAD_NUM = re.compile(r"^(\d+(\.\d+)+\.?|\d+\)|[A-Z]\.)\s")


def level(text):
    """제목 줄 단계(작을수록 큰 제목). 제목이 아니면 None"""
    if HEAD_NUM.match(text):
        return 0
    if text.startswith(("○", "■", "□")):
        return 1
    if re.match(r"^[-–•] ", text):
        return 2
    if text.startswith("·"):
        return 3
    return None


def locate(pg, clip, where, skip=None):
    lines, objs = page_items(pg, clip, skip)
    kind, _, needle = where.partition("=")
    if kind == "box":
        x0, y0, x1, y1 = [float(v) for v in needle.split(",")]
        return [[x0 * pg.rect.width, y0 * pg.rect.height, x1 * pg.rect.width, y1 * pg.rect.height]], ""
    if kind == "page" or not needle:
        return [list(clip)], ""
    hit, raw = [], []
    for part in needle.split(";;"):
        h, r = lines_hit(pg, lines, part)
        hit += [x for x in h if x not in hit]
        raw += r
    if kind == "word":
        return ([[r.x0 - 2, r.y0 - 2, r.x1 + 2, r.y1 + 2] for r in raw] or [list(clip)]), ("" if raw else "글자를 찾지 못함")
    if not hit:
        return [list(clip)], "글자를 찾지 못해 쪽 전체로 표시함: " + needle
    if kind == "find":
        r = union([l["bbox"] for l in hit])
        if len(hit) > 1:
            r = union([r] + [o for o in objs if o[1] >= r[1] - 2 and o[3] <= r[3] + 2])
        return [[r[0] - 3, r[1] - 3, r[2] + 3, r[3] + 3]], ""
    if kind == "sec":
        heads = [l for l in hit if level(l["text"]) is not None] or hit
        start = heads[0]
        lv = level(start["text"])
        y0 = start["bbox"][1]
        ends = [l["bbox"][1] for l in lines if l["bbox"][1] > y0 + 4 and level(l["text"]) is not None
                and (lv is None or level(l["text"]) <= lv)]
        y1 = min(ends) - 3 if ends else clip[3]
        inside = [l["bbox"] for l in lines if y0 - 2 <= l["bbox"][1] and l["bbox"][3] <= y1 + 3]
        inside += [o for o in objs if o[1] >= y0 - 2 and o[3] <= y1 + 3]
        r = union(inside or [start["bbox"]])
        return [[r[0] - 4, r[1] - 4, r[2] + 4, r[3] + 4]], ""
    if kind == "fig":
        y1 = min(l["bbox"][1] for l in hit) + 2
        above = [l["bbox"][3] for l in lines if l["bbox"][3] < y1 - 4 and len(l["text"]) >= 4]
        y0 = max(above) if above else clip[1]
        inside = [o for o in objs if o[1] >= y0 - 3 and o[3] <= y1 + 3 and (o[2] - o[0]) > 3]
        r = union(inside + [[x.x0, x.y0, x.x1, x.y1] for x in raw] or [l["bbox"] for l in hit])
        return [[r[0] - 5, r[1] - 5, r[2] + 5, r[3] + 5]], ("" if inside else "그림을 찾지 못해 제목만 표시함")
    if kind == "para":
        idx = [i for i, l in enumerate(lines) if l in hit]
        a, b = idx[0], idx[-1]
        step = 1.9 * (lines[a]["bbox"][3] - lines[a]["bbox"][1])
        while a > 0 and lines[a]["bbox"][1] - lines[a - 1]["bbox"][1] < step and level(lines[a]["text"]) is None:
            a -= 1
        while b + 1 < len(lines) and lines[b + 1]["bbox"][1] - lines[b]["bbox"][1] < step and level(lines[b + 1]["text"]) is None:
            b += 1
        r = union([l["bbox"] for l in lines[a:b + 1]])
        return [[r[0] - 4, r[1] - 4, r[2] + 4, r[3] + 4]], ""
    if kind in ("after", "before"):
        if kind == "after":
            y0 = max(l["bbox"][3] for l in hit) - 2
            below = [l["bbox"][1] for l in lines if l["bbox"][1] > y0 + 4 and len(l["text"]) >= 4]
            y1 = min(below) if below else clip[3]
        else:
            y1 = min(l["bbox"][1] for l in hit) + 2
            above = [l["bbox"][3] for l in lines if l["bbox"][3] < y1 - 4 and len(l["text"]) >= 4]
            y0 = max(above) if above else clip[1]
        inside = [o for o in objs if o[1] >= y0 - 3 and o[3] <= y1 + 3 and (o[2] - o[0]) > 3]
        if not inside:
            return [union([l["bbox"] for l in hit])], "그 줄 %s에 그림·수식이 없어 줄만 표시함" % ("아래" if kind == "after" else "위")
        r = union(inside)
        return [[r[0] - 5, r[1] - 5, r[2] + 5, r[3] + 5]], ""
    return [list(clip)], "알 수 없는 위치 형식: " + where


def main():
    ap = argparse.ArgumentParser(description="근거 위치 표시")
    ap.add_argument("marks", nargs="*", help='"문서키|쪽|위치|메모"')
    ap.add_argument("--project")
    ap.add_argument("--msg", default="")
    ap.add_argument("--clear", action="store_true")
    ap.add_argument("--check", action="store_true", help="확인용 그림 만들기")
    ap.add_argument("--show-user", action="store_true")
    a = ap.parse_args()
    P = find_project(a.project)

    if a.show_user:
        u = read_json(P.user_file, {"marks": []})
        print("지금 보는 곳:", u.get("view") or "-")
        for m in u.get("marks", []):
            print("- 사람%d | %s %s쪽 | 메모: %s" % (m["id"], m["doc_name"], m["page"], m.get("note") or "(없음)"))
            print("    글:", (m.get("text") or "(글자 없음. 그림 확인)").replace("\n", " / ")[:300])
            print("    그림:", m.get("crop"))
        return

    old = read_json(P.pointer_file, {"seq": 0})
    out = {"seq": old.get("seq", 0) + 1, "time": time.strftime("%H:%M:%S"), "msg": a.msg, "marks": []}
    if not a.clear:
        import pymupdf
        info = P.docs_info()
        skip = re.compile(P.cfg["skip_line_regex"]) if P.cfg.get("skip_line_regex") else None
        for n, spec in enumerate(a.marks, start=1):
            parts = spec.split("|")
            if parts and parts[0] in ("L", "R"):  # 예전 형식(쪽|문서|…) 호환
                parts = parts[1:]
            key, page, where, note = (parts + ["", "", ""])[:4]
            if key not in info:
                raise SystemExit("모르는 문서키: %s (project.json docs 에 있는 키: %s)" % (key, ", ".join(info)))
            fp = P.file_page(key, page)
            doc = pymupdf.open(P.doc_path(key))
            pg = doc[fp - 1]
            clip = info[key]["clips"][fp - 1]
            rects, warn = locate(pg, clip, where, skip)
            rects = [[round(max(clip[0], r[0]), 1), round(max(clip[1], r[1]), 1),
                      round(min(clip[2], r[2]), 1), round(min(clip[3], r[3]), 1)] for r in rects]
            out["marks"].append({"n": n, "doc": key, "page": int(page), "filepage": fp, "rects": rects, "note": note})
            print("표시 %d: %s %s쪽 | %s%s" % (n, key, page, where, (" | 주의: " + warn) if warn else ""))
            if a.check:
                for r in rects:
                    pg.draw_rect(pymupdf.Rect(*r), color=(0.48, 0.18, 0.75), width=2)
                u = union(rects)
                view = pymupdf.Rect(clip[0], max(clip[1], u[1] - 60), clip[2], min(clip[3], u[3] + 60))
                png = os.path.join(P.state, "check", "mark_%d.png" % n)
                pg.get_pixmap(dpi=80, clip=view).save(png)
                print("    확인 그림:", os.path.relpath(png, P.root))
            doc.close()
    write_json(P.pointer_file, out)
    print("seq", out["seq"])


if __name__ == "__main__":
    main()

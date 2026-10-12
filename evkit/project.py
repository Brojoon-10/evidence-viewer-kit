# -*- coding: utf-8 -*-
"""프로젝트 설정(project.json)과 상태 파일 위치.

project.json (경로는 이 파일이 있는 폴더 기준):
{
  "title": "화면 제목",
  "docs": {                                  근거로 쓸 PDF 목록
    "spec": {"name": "사양서 v2", "path": "docs/spec.pdf",
             "unit": "쪽",                    (선택) 쪽 번호 뒤에 붙일 말
             "first_page": 1,                (선택) 화면에 보일 첫 쪽 번호(원본에서 일부만 뽑은 PDF일 때)
             "crop": [x0, y0, x1, y1]}       (선택) 모든 쪽에서 잘라 보일 범위(pt)
  },
  "drafts": [{"label": "보고서 초안", "file": "drafts/report.md"}],
  "state_dir": ".evkit",                     근거 기록·캐시가 쌓이는 곳
  "port": 8765,
  "page_dpi": 150,                           실시간 화면 쪽 그림 해상도
  "skip_line_regex": "",                     (선택) 머리말·꼬리말처럼 상자 계산에서 뺄 줄
  "math": false                              (선택) 미리보기에서 $...$ 수식(MathJax CDN)
}
"""
import json
import os
import re

DEFAULTS = {"title": "근거 뷰어", "docs": {}, "drafts": [], "state_dir": ".evkit", "port": 8765,
            "page_dpi": 150, "skip_line_regex": "", "math": False}


class Project:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.root = os.path.dirname(self.path)
        with open(self.path, encoding="utf-8") as f:
            cfg = json.load(f)
        self.cfg = dict(DEFAULTS, **cfg)
        self.state = self.abs(self.cfg["state_dir"])
        for d in ("history", "cache", "marks", "check"):
            os.makedirs(os.path.join(self.state, d), exist_ok=True)

    # ---- 경로
    def abs(self, rel):
        return os.path.normpath(os.path.join(self.root, rel))

    def inside(self, path):
        """프로젝트 폴더 밖 파일은 내주지 않는다."""
        p = os.path.normpath(path)
        return p == self.root or p.startswith(self.root + os.sep)

    @property
    def pointer_file(self):
        return os.path.join(self.state, "pointer.json")

    @property
    def user_file(self):
        return os.path.join(self.state, "user.json")

    @property
    def history_dir(self):
        return os.path.join(self.state, "history")

    # ---- 근거 문서
    def doc_path(self, key):
        d = self.cfg["docs"].get(key)
        if not d:
            return None
        p = self.abs(d["path"])
        return p if self.inside(p) and os.path.exists(p) else None

    def docs_info(self):
        """화면에 보낼 문서 정보: 쪽 수, 쪽별 자르기 범위(clips), 쪽 번호 대응(map). PDF가 바뀔 때만 다시 계산."""
        cache = os.path.join(self.state, "cache", "docs.json")
        old = read_json(cache, {})
        out, changed = {}, False
        for key, d in self.cfg["docs"].items():
            p = self.doc_path(key)
            if not p:
                continue
            stamp = "%d:%d:%s" % (os.path.getmtime(p), os.path.getsize(p), json.dumps(d.get("crop")))
            if old.get(key, {}).get("stamp") == stamp:
                info = old[key]
            else:
                import pymupdf
                doc = pymupdf.open(p)
                clips = [list(d["crop"]) if d.get("crop") else [round(v, 1) for v in pg.rect] for pg in doc]
                doc.close()
                info = {"stamp": stamp, "pages": len(clips), "clips": clips}
                changed = True
            first = int(d.get("first_page", 1))
            e = dict(info, name=d.get("name", key), unit=d.get("unit", ""))
            if first != 1:
                e["map"] = {str(first + i): i + 1 for i in range(info["pages"])}
            out[key] = e
        if changed or set(out) != set(old):
            write_json(cache, {k: {kk: v[kk] for kk in ("stamp", "pages", "clips")} for k, v in out.items()})
        return out

    def file_page(self, key, page):
        """원본 쪽 번호 → PDF 안 쪽 번호"""
        first = int(self.cfg["docs"][key].get("first_page", 1))
        return int(page) - first + 1

    def orig_page(self, key, filepage):
        first = int(self.cfg["docs"][key].get("first_page", 1))
        return int(filepage) + first - 1

    # ---- 초안
    def draft(self, i):
        ds = self.cfg["drafts"]
        if not ds:
            return None
        return ds[max(0, min(int(i), len(ds) - 1))]

    # ---- 근거 기록
    def evidence_index(self):
        """저장된 근거 기록 전체 → 초안 키별 근거 목록. 같은 키는 가장 최근에 저장한 기록이 이긴다."""
        hd = self.history_dir
        files = sorted((os.path.join(hd, f) for f in os.listdir(hd) if f.endswith(".json")), key=os.path.getmtime)
        idx, src = {}, {}
        for f in files:
            per = {}
            for m in read_json(f, {}).get("marks", []):
                k = key_of(m)
                if k:
                    per.setdefault(k, []).append(m)
            for k, v in per.items():
                idx[k], src[k] = v, os.path.basename(f)[:-5]
        return {"keys": idx, "src": src}

    def histories(self):
        hd = self.history_dir
        out = []
        for f in sorted(os.listdir(hd)):
            if f.endswith(".json"):
                d = read_json(os.path.join(hd, f), {})
                out.append({"name": f[:-5], "msg": d.get("msg", ""), "marks": d.get("marks", [])})
        return out


KEY = re.compile(r"^\[([\w.-]+)\]")


def key_of(mark):
    r = KEY.match(mark.get("note", "") or "")
    return r.group(1) if r else None


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def find_project(arg=None):
    """--project 인자 → 환경변수 EVKIT_PROJECT → 현재 폴더의 project.json 순서로 찾는다."""
    cand = arg or os.environ.get("EVKIT_PROJECT") or "project.json"
    if os.path.isdir(cand):
        cand = os.path.join(cand, "project.json")
    if not os.path.exists(cand):
        raise SystemExit("project.json 을 찾지 못함: %s (--project 로 지정하거나 EVKIT_PROJECT 설정)" % cand)
    return Project(cand)

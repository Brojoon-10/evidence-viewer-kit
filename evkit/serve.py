# -*- coding: utf-8 -*-
"""실시간 작업 서버. 이 PC 안에서만 열린다(127.0.0.1).

  python -m evkit.serve --project examples/demo
  → http://127.0.0.1:8765/        왼쪽 초안 미리보기 | 오른쪽 근거 화면

경로
  /                작업 화면(좌우)          /preview?d=N    초안 N 미리보기
  /pointer         근거 화면                 /page/<문서>/<쪽>.png, /doc/<문서>.pdf, /assets/<경로>
  /api/docs        문서 정보(쪽 수·자르기 범위)
  /api/drafts      초안 목록                 /api/version?d=N  초안 N 수정 시각(자동 새로고침용)
  /api/state       {pointer, select, user, docs_ver}
  /api/viewers     {age}: 마지막 폴링 후 경과 초 (열린 화면이 있는지 판단, 없으면 null)
  /api/evidence    저장된 근거 기록 전체를 초안 키별로
  /api/histories   저장된 근거 기록 목록
  POST /api/select {group, keys, key, label}   초안에서 줄을 누름 → 묶음 보기
  POST /api/mode   {mode: "agent"|"group"}      보기 전환(초안·근거 화면이 함께)
  POST /api/user   {type: "mark"|"clear"|"delete", ...}  사람이 근거 화면에서 그린 상자
"""
import argparse
import importlib
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse, parse_qs

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from evkit import preview  # noqa: E402
from evkit.project import find_project, read_json, write_json  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
LOCK = threading.Lock()
SELECT = {"seq": 0}  # 초안에서 고른 묶음(서버 메모리: 창이 여러 개여도 함께 움직임)
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".svg": "image/svg+xml",
        ".webp": "image/webp", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}


LAST_POLL = {"t": None}  # time of the last /api/state poll: an open viewer polls every second


def make_handler(P):
    class H(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype, cache="no-store"):
            data = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            try:
                self.wfile.write(data)
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                pass

        def _file(self, path, ctype, cache="no-store"):
            with open(path, "rb") as f:
                self._send(200, f.read(), ctype, cache)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

        def _404(self):
            self._send(404, "not found", "text/plain; charset=utf-8")

        def do_GET(self):
            u = urlparse(self.path)
            path, q = unquote(u.path), parse_qs(u.query)
            d = int((q.get("d") or ["0"])[0] or 0)
            try:
                if path in ("/", "/work"):
                    self._file(os.path.join(WEB, "work.html"), "text/html; charset=utf-8")
                elif path in ("/pointer", "/pointer/"):
                    self._file(os.path.join(WEB, "pointer.html"), "text/html; charset=utf-8")
                elif path == "/preview":
                    importlib.reload(preview)  # preview.py 를 고쳐도 재시작 없이
                    self._send(200, preview.build(P, d), "text/html; charset=utf-8")
                elif path == "/api/version":
                    self._send(200, preview.version(P, d), "text/plain; charset=utf-8")
                elif path == "/api/drafts":
                    self._json([{"label": x.get("label", x["file"]), "i": i} for i, x in enumerate(P.cfg["drafts"])])
                elif path == "/api/docs":
                    self._json({"title": P.cfg["title"], "docs": P.docs_info()})
                elif path == "/api/viewers":
                    t = LAST_POLL["t"]
                    self._json({"age": None if t is None else round(time.time() - t, 1)})
                elif path == "/api/state":
                    LAST_POLL["t"] = time.time()
                    info = P.docs_info()
                    self._json({"pointer": read_json(P.pointer_file, {"seq": 0, "marks": []}),
                                "user": read_json(P.user_file, {"marks": []}), "select": SELECT,
                                "docs_ver": "|".join(k + ":" + v["stamp"] for k, v in sorted(info.items()))})
                elif path == "/api/evidence":
                    self._json(P.evidence_index())
                elif path == "/api/histories":
                    self._json(P.histories())
                elif path.startswith("/page/") and path.endswith(".png"):
                    key, num = path[6:-4].split("/")
                    p = P.doc_path(key)
                    if not p:
                        return self._404()
                    num = int(num)
                    info = P.docs_info()[key]
                    dpi = int(P.cfg["page_dpi"])
                    png = os.path.join(P.state, "cache", "%s_%03d_%d.png" % (key, num, dpi))
                    if not os.path.exists(png) or os.path.getmtime(png) < os.path.getmtime(p):
                        import pymupdf
                        doc = pymupdf.open(p)
                        doc[num - 1].get_pixmap(dpi=dpi, clip=pymupdf.Rect(*info["clips"][num - 1])).save(png)
                        doc.close()
                    self._file(png, "image/png", cache="max-age=3600")
                elif path.startswith("/doc/") and path.endswith(".pdf"):
                    p = P.doc_path(path[5:-4])
                    self._file(p, "application/pdf", cache="max-age=600") if p else self._404()
                elif path.startswith("/assets/"):
                    p = P.abs(path[len("/assets/"):])
                    if P.inside(p) and os.path.isfile(p):
                        self._file(p, MIME.get(os.path.splitext(p)[1].lower(), "application/octet-stream"), cache="max-age=60")
                    else:
                        self._404()
                else:
                    self._404()
            except Exception:
                self._send(500, "<pre>" + traceback.format_exc() + "</pre>", "text/html; charset=utf-8")

        def do_POST(self):
            path = unquote(urlparse(self.path).path)
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                now = time.strftime("%H:%M:%S")
                if path == "/api/select":
                    with LOCK:
                        seq = SELECT.get("seq", 0) + 1
                        SELECT.clear()
                        SELECT.update({"seq": seq, "mode": "group", "group": body.get("group"), "keys": body.get("keys") or [],
                                       "key": body.get("key"), "label": body.get("label", ""), "time": now})
                    return self._json({"ok": True})
                if path == "/api/mode":
                    with LOCK:
                        SELECT["seq"] = SELECT.get("seq", 0) + 1
                        SELECT["mode"] = "agent" if body.get("mode") == "agent" else "group"
                        SELECT["time"] = now
                    return self._json({"ok": True})
                if path == "/api/user":
                    with LOCK:
                        st = read_json(P.user_file, {"marks": []})
                        st.setdefault("marks", [])
                        kind = body.get("type")
                        if kind == "clear":
                            st["marks"] = []
                        elif kind == "delete":
                            st["marks"] = [m for m in st["marks"] if m.get("id") != body.get("id")]
                        elif kind == "mark":
                            key, fp = body["doc"], int(body["filepage"])
                            p = P.doc_path(key)
                            if not p:
                                return self._json({"error": "unknown doc"}, 400)
                            import pymupdf
                            rect = pymupdf.Rect(*[float(v) for v in body["rect"]])
                            doc = pymupdf.open(p)
                            page = doc[fp - 1]
                            text = page.get_text("text", clip=rect).strip()
                            used = set(m.get("id", 0) for m in st["marks"])
                            mid = 1
                            while mid in used:
                                mid += 1
                            crop = os.path.join(P.state, "marks", "mark_%d.png" % mid)
                            page.get_pixmap(dpi=150, clip=(rect + (-12, -12, 12, 12)) & page.rect).save(crop)
                            doc.close()
                            st["marks"].append({"id": mid, "doc": key, "doc_name": P.cfg["docs"][key].get("name", key),
                                                "page": P.orig_page(key, fp), "filepage": fp, "rect": [round(v, 1) for v in rect],
                                                "text": text, "note": (body.get("note") or "").strip(),
                                                "crop": os.path.relpath(crop, P.root).replace("\\", "/"), "time": now})
                        write_json(P.user_file, st)
                    return self._json({"ok": True})
                self._404()
            except Exception:
                self._send(500, traceback.format_exc(), "text/plain; charset=utf-8")

        def log_message(self, fmt, *args):
            pass
    return H


def main():
    ap = argparse.ArgumentParser(description="근거 작업 서버")
    ap.add_argument("--project")
    ap.add_argument("--port", type=int)
    a = ap.parse_args()
    P = find_project(a.project)
    port = a.port or int(P.cfg["port"])
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(P))
    print("작업 화면: http://127.0.0.1:%d/   (프로젝트: %s)" % (port, P.path), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""지금 상태(초안·근거 문서·근거 기록)를 HTML 파일 하나로 묶는다. 서버 없이 더블클릭으로 열린다.

  python -m evkit.build_viewer --project examples/demo [--out 경로.html] [--dpi 96] [--quality 60]

원리: 근거 문서 모든 쪽을 JPEG(base64)로 넣고, 초안·근거 화면을 srcdoc iframe 으로 넣은 뒤
각 화면 <head> 맨 앞에 web/shim.js 를 넣는다. shim 이 /api/* 요청을 부모 페이지 데이터로 대신 응답하므로
실시간 화면 코드를 고치지 않고 그대로 쓴다. 스냅샷이므로 초안이 바뀌면 다시 빌드한다.
주의: 결과 파일에는 근거 문서 쪽 그림이 통째로 들어간다. 받을 사람을 정해서 전달할 것."""
import argparse
import base64
import io
import json
import os
import re
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from evkit import preview  # noqa: E402
from evkit.project import find_project, read_json  # noqa: E402

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def js_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def image_data_uri(path, max_w=1600, quality=82):
    from PIL import Image
    with Image.open(path) as im:
        if im.mode in ("P", "RGBA", "LA"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def with_shim(doc_html):
    tag = "<script>%s</script>" % open(os.path.join(WEB, "shim.js"), encoding="utf-8").read()
    if re.search(r"<head[^>]*>", doc_html):
        return re.sub(r"<head([^>]*)>", lambda m: "<head%s>%s" % (m.group(1), tag), doc_html, count=1)
    return tag + doc_html


def inline_assets(h, P):
    def img(m):
        p = P.abs(m.group(1))
        return 'src="%s"' % (image_data_uri(p) if P.inside(p) and os.path.isfile(p) else "/assets/" + m.group(1))
    return re.sub(r'src="/assets/([^"]+)"', img, h)


def render_pages(P, info, dpi, q):
    import pymupdf
    pages, total = {}, 0
    for key, d in info.items():
        doc = pymupdf.open(P.doc_path(key))
        arr = []
        for n in range(1, d["pages"] + 1):
            b = doc[n - 1].get_pixmap(dpi=dpi, clip=pymupdf.Rect(*d["clips"][n - 1])).tobytes("jpeg", jpg_quality=q)
            total += len(b)
            arr.append("data:image/jpeg;base64," + base64.b64encode(b).decode())
        pages[key] = arr
        doc.close()
        print("  %-12s %3d쪽" % (key, d["pages"]), flush=True)
    print("쪽 그림 합계 %.1f MB" % (total / 1e6))
    return pages


def main():
    ap = argparse.ArgumentParser(description="단일 파일 근거 뷰어 만들기")
    ap.add_argument("--project")
    ap.add_argument("--out")
    ap.add_argument("--dpi", type=int, default=96)
    ap.add_argument("--quality", type=int, default=60)
    a = ap.parse_args()
    P = find_project(a.project)
    t0 = time.time()
    info = P.docs_info()
    print("근거 문서 %d종 %d쪽" % (len(info), sum(d["pages"] for d in info.values())))
    state = {
        "title": P.cfg["title"],
        "docs": {k: {kk: vv for kk, vv in v.items() if kk != "stamp"} for k, v in info.items()},
        "pages": render_pages(P, info, a.dpi, a.quality),
        "evidence": P.evidence_index(),
        "histories": P.histories(),
        "pointer": read_json(P.pointer_file, {"seq": 1, "marks": []}),
        "drafts": [{"label": x.get("label", x["file"]), "i": i} for i, x in enumerate(P.cfg["drafts"])],
    }
    left = [{"label": x.get("label", x["file"]), "html": with_shim(inline_assets(preview.build(P, i), P))}
            for i, x in enumerate(P.cfg["drafts"])]
    pointer = with_shim(open(os.path.join(WEB, "pointer.html"), encoding="utf-8").read())
    out = open(os.path.join(WEB, "shell.html"), encoding="utf-8").read()
    for k, v in {"__TITLE__": P.cfg["title"], "__TIME__": time.strftime("%Y-%m-%d %H:%M"),
                 "__STATE__": js_json(state), "__LEFT__": js_json(left), "__POINTER__": js_json(pointer)}.items():
        out = out.replace(k, v)
    dst = a.out or os.path.join(P.state, "dist", re.sub(r"[\\/:*?\"<>|\s]+", "_", P.cfg["title"]) + ".html")
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(out)
    print("완성: %s (%.1f MB, %.0f초)" % (dst, os.path.getsize(dst) / 1e6, time.time() - t0))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""데모 만들기: 가상의 근거 PDF 2개를 만들고, 초안 줄마다 근거를 찍어 저장한다.

  python examples/demo/make_demo.py
  python -m evkit.serve --project examples/demo      → http://127.0.0.1:8765/

내용은 모두 지어낸 예시(가상의 자전거 도로 시범 사업)이다."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
DOCS = os.path.join(HERE, "docs")


def make_pdf(path, pages):
    import pymupdf
    doc = pymupdf.open()
    for blocks in pages:
        pg = doc.new_page(width=595, height=842)
        y = 70
        for kind, text in blocks:
            if kind == "h":
                pg.insert_text((60, y), text, fontsize=14, fontname="hebo"); y += 26
            elif kind == "p":
                for ln in text.split("\n"):
                    pg.insert_text((60, y), ln, fontsize=10.5, fontname="helv"); y += 16
                y += 8
            elif kind == "fig":
                pg.draw_rect(pymupdf.Rect(150, y, 445, y + 120), color=(0.3, 0.3, 0.3), width=1)
                pg.draw_line((170, y + 100), (430, y + 30), color=(0.1, 0.4, 0.8), width=2)
                pg.draw_line((170, y + 100), (430, y + 85), color=(0.8, 0.3, 0.1), width=2)
                y += 138
                pg.insert_text((190, y), text, fontsize=9.5, fontname="helv"); y += 26
        pg.insert_text((290, 815), "- %d -" % (doc.page_count), fontsize=9, fontname="helv")
    doc.save(path)


SURVEY = [
    [("h", "1. Field Survey Results"),
     ("p", "1.1 Cyclist counts. Weekday cyclist counts on Oak Avenue were taken for four weeks\n"
           "before and four weeks after the pilot lane opened. The average weekday count rose\n"
           "from 310 to 455 riders per day."),
     ("p", "1.2 Safety. Near-miss reports submitted through the city app dropped by about one third\n"
           "(from 42 to 28 reports). Most remaining reports were at the Elm Street intersection,\n"
           "where turning vehicles cross the lane."),
     ("fig", "Figure 1. Weekday cyclist counts before and after the pilot")],
    [("h", "2. Resident Feedback"),
     ("p", "2.1 Survey. 412 residents answered the door-to-door survey. 68 % supported keeping\n"
           "the lane after the pilot, 21 % opposed, and 11 % had no opinion."),
     ("p", "2.2 Concerns. The most common concern was the loss of 14 on-street parking spaces\n"
           "between 3rd and 5th Street. Delivery drivers also asked for a loading zone.")],
]
GUIDE = [
    [("h", "3. Lane Dimensions"),
     ("p", "3.1 Scope. This section applies to painted and buffered bicycle lanes on city streets."),
     ("p", "3.2 Width. A one-way bicycle lane shall be at least 1.8 m wide, with a buffer of at\n"
           "least 0.6 m between the lane and parked or moving vehicles."),
     ("p", "3.3 Pilots. Temporary pilot lanes may be narrower (minimum 1.5 m) for up to one year.")],
    [("h", "4. Intersections"),
     ("p", "4.1 Protected corners. Where turning traffic crosses a bicycle lane, a protected corner\n"
           "with a refuge island should be provided (see Figure 2)."),
     ("fig", "Figure 2. Protected corner layout")],
]

# 초안 키 → 근거 위치 (문서|쪽|위치|메모)
EVIDENCE = {
    "g1_findings": ["survey|1|find=from 310 to 455|[g1-1] 평일 자전거 통행량 310 → 455",
                    "survey|1|fig=Figure 1.|[g1-1] 그림 1 통행량 변화",
                    "survey|1|find=dropped by about one third|[g1-2] 아차사고 신고 약 1/3 감소",
                    "survey|1|find=Most remaining reports|[g1-3] 남은 신고는 Elm St. 교차로"],
    "g2_feedback": ["survey|2|find=68 % supported|[g2-1] 주민 68 % 유지 찬성",
                    "survey|2|find=loss of 14 on-street parking|[g2-2] 주차면 14개 감소 우려"],
    "g3_recommend": ["guide|1|para=3.2 Width|[g3-1] 폭 1.8 m, 완충 0.6 m (지침 3.2)",
                     "guide|2|find=4.1 Protected corners|[g3-2] 교차로 보호 코너 (지침 4.1)",
                     "guide|2|fig=Figure 2.|[g3-2] 그림 2 보호 코너 배치",
                     "guide|1|find=minimum 1.5 m|[t1] 시범 차로 최소 1.5 m (지침 3.3)",
                     "guide|1|find=at least 1.8 m|[t2] 기준 1.8 m (지침 3.2)"],
}


def run(*args):
    subprocess.run([sys.executable, "-m"] + list(args) + ["--project", HERE], cwd=KIT, check=True)


if __name__ == "__main__":
    os.makedirs(DOCS, exist_ok=True)
    make_pdf(os.path.join(DOCS, "survey.pdf"), SURVEY)
    make_pdf(os.path.join(DOCS, "guide.pdf"), GUIDE)
    print("근거 PDF 2개 만듦:", DOCS)
    for name, marks in EVIDENCE.items():
        run("evkit.point", "--msg", "데모 근거: " + name, *marks)
        run("evkit.pointer_log", "save", name)
    run("evkit.pointer_log", "show", "g1_findings")
    print("\n다음: python -m evkit.serve --project examples/demo  → http://127.0.0.1:8765/")

# AGENTS.md — 근거 기반 문서 작업 규칙 (AI 에이전트용)

> **EN** — Instructions for an AI agent working with a human through evidence-viewer-kit.
> Core rules: reuse source wording, back every detail with a located source, move the cursor whenever you mention
> a source, let the human decide, verify and save evidence group by group. Commands are at the bottom.

이 문서는 사람과 함께 문서를 쓰거나 검토하는 AI 에이전트가 따를 규칙입니다. 프로젝트 지침 파일(CLAUDE.md, AGENTS.md 등)에 그대로 넣거나 링크하세요.

## 1. 작업 원칙

1. **원문 문장을 그대로 쓴다.**
   초안의 제목·항목·문장은 근거 문서의 말을 가져온다. 에이전트가 새 문장, 새 소제목, 새 표, 새 용어를 만들지 않는다.
   꼭 필요한 연결 문장은 `{todo}…{/todo}` 처럼 표시해서 사람이 알아보게 한다.
2. **세부 하나까지 근거.**
   한 줄 안의 숫자, 날짜·기한, 상태("완료", "진행 중"), 범위 같은 세부도 각각 원문 위치에 연결한다. 줄을 고쳐 세부를 옮기면 근거도 같이 옮긴다.
   근거가 없으면 없다고 쓴다. 추정이면 추정이라고 쓴다. 근거 없는 완료 시기·수치는 쓰지 않는다.
3. **말할 때마다 커서를 옮긴다.**
   문서 내용을 언급하는 답에는 묻지 말고 `point` 로 그 위치를 찍는다. 사람은 화면을 보며 바로 확인한다.
   답이 먼저, 표시는 그 뒤에 명령 한 번으로.
4. **결정은 사람이 한다.**
   사람의 질문("~해도 되는 거 아니야?")을 결정으로 받아 기록하지 않는다. 사람이 "그렇게 하자"고 한 뒤에만 결정으로 기록하고, 결정 기록에 근거 문서·쪽을 함께 적는다. 반대 근거가 있으면 그것도 적는다.
   의견을 물으면 근거와 함께 짧게 답하되, 고르는 것은 사람이다.
5. **한 번에 하나씩.**
   묶음(○ 항목) 단위로 근거를 같이 보고 넘어간다. 여러 주제를 한꺼번에 꺼내지 않는다.
6. **하기 전에 말하고, 승인받고 한다.**
   파일을 고치거나, 사람이 보는 앱(한글·엑셀·브라우저)을 조작하기 전에 무엇을 할지 한 줄로 말한다. 원본 파일은 복사본에서 작업한다.
7. **"틀렸다"와 "지금과 다르다"를 구분해서 말한다.** 최신 자료와 충돌하는 부분만 최신을 따른다. 옛 자료가 틀린 것은 아니다.
8. **완료·진행 중·예정을 구분한다.** 미완료를 완료처럼 쓰지 않는다.
9. **사람이 보는 앱 안에서 일한다.** 한글·엑셀·파워포인트는 COM으로 열린 창을 직접 고치고(고치는 자리로 화면 이동), 브라우저 화면은 헤드리스 Chrome·CDP로 캡처·클릭해서 확인한다. "됐다"고 말하기 전에 저장 파일·PDF·캡처로 실제 모양을 본다. 자세히: [docs/WORKFLOW_TIPS.md](docs/WORKFLOW_TIPS.md)

## 2. 근거 찍기 요령

- 메모는 반드시 `[초안키] 짧은 설명 (문서 쪽)` 으로 시작한다. 그래야 초안 줄과 이어진다.
- 줄 하나에 근거가 둘 이상이면 같은 키로 여러 개 찍는다(번호가 `#3-1`, `#3-2`).
- 처음 찍는 위치, 그림, 표는 `--check` 로 확인 그림을 열어 본다. 글자 조각만 잡히거나 상자가 쪼개지면 사람이 못 알아본다.
- 같은 문단에 여러 줄이 걸리면 `para=` 보다 `find=` 로 줄을 좁힌다.
- 한 묶음을 사람이 확인하면 `pointer_log save <이름>` 으로 저장한다. 이름은 나중에 다시 부를 수 있게(예: `2장_A1`, `별첨_표3`).
- 사람이 "여기", "이거", "사람3" 이라고 하면 먼저 `point --show-user` 로 사람이 그린 상자를 읽고 답한다.

## 3. 명령 요약

```bash
# 서버(사람이 보는 화면)
python -m evkit.serve --project P                      # http://127.0.0.1:8765/

# 근거 찍기
python -m evkit.point --project P --msg "무엇을 보여 주는지" \
  "spec|12|find=원문 글자|[k3] 설명 (사양서 12쪽)" \
  "notes|7|para=문단 첫 글자|[k4] 설명"
python -m evkit.point --project P --check ...           # 확인 그림 .evkit/check/
python -m evkit.point --project P --show-user           # 사람이 Shift+끌기로 그린 상자
python -m evkit.point --project P --clear

# 저장·다시 보기
python -m evkit.pointer_log --project P save 이름
python -m evkit.pointer_log --project P show 이름
python -m evkit.pointer_log --project P list

# 배포용 단일 파일
python -m evkit.build_viewer --project P
```

위치 형식: `find=` 줄, `para=` 문단, `sec=` 절, `fig=` 캡션+그림, `after=`/`before=` 아래/위 그림·수식, `word=` 글자 조각, `box=x0,y0,x1,y1`(0~1 비율), `page`.
쪽 번호는 원본 쪽 번호(project.json 의 `first_page` 기준).

## 4. 원문 찾기

- PDF 글은 `python -c "import pymupdf; d=pymupdf.open('docs/x.pdf'); print(d[11].get_text())"` 로 바로 읽을 수 있다.
- 자료가 많으면 PDF·HWP·PPT·XLS를 미리 텍스트로 뽑아 두고(`ref/_text/` 같은 곳) 검색하면 빠르다.
- 큰 검색·대조는 하위 에이전트에게 맡기고, 대화하는 에이전트는 사람에게 빠르게 답하는 데 집중한다.

## 5. 기록

- 결정은 결정 기록(예: `analysis/decisions.md`)에 "무엇을 · 사람이 한 말 · 근거 위치" 로 남긴다.
- 진행 상황은 진행 파일(예: `PROGRESS.md`)에 단계마다 갱신한다. 대화가 길어져 요약될 때 다시 이어 가는 기준이 된다.

# 작업 방식 — 사용자가 지켜보며 같이 일하는 환경 만들기 (COM · CDP)

> **EN** — The goal is an *observable, interactive* workspace: the agent does its work **inside the apps the user
> already has open**, so the user watches each change happen and can steer at any moment ("stop", "not there",
> "this one"). Pick the channel by task: **COM** for Office/HWP documents (Windows), **CDP** for anything in a
> browser, and **evkit** for pointing at evidence in source PDFs. The agent then confirms results from what the
> user would actually see (saved file, PDF, screenshot).

## 왜 이렇게 하나

에이전트가 뒤에서 파일을 고치고 "다 했습니다"라고 보고하면, 사용자는 결과를 처음부터 다시 열어 확인해야 합니다. 그 사이에 엉뚱한 곳이 고쳐져도 늦게 압니다.

대신 **사용자가 이미 열어 둔 창 안에서 에이전트가 움직이게** 합니다.
- 사용자는 바뀌는 자리를 **실시간으로 봅니다.** 에이전트는 고치기 전에 그 자리로 화면을 옮깁니다.
- 보다가 바로 끼어들 수 있습니다. "멈춰", "거기 말고", "이 줄"처럼요.
- 사용자도 같은 화면에서 가리킬 수 있습니다. 근거 화면에서 Shift+끌기를 하거나 창에서 직접 고치면 에이전트가 그걸 읽습니다.
- 대화가 "설명"이 아니라 "같은 화면을 보며 하는 작업"이 됩니다.

## 작업마다 쓰는 통로

| 작업 | 사용자가 보는 곳 | 에이전트가 쓰는 통로 | 에이전트가 하는 일 |
|---|---|---|---|
| 보고서·서식 채우기 (한글, 워드) | 열어 둔 문서 창 | **COM** (`pyhwpx`, `pywin32`) | 고칠 자리로 이동 → 글·표·서식 수정 → 저장 |
| 표·시트 채우기 (엑셀) | 열어 둔 통합문서 | **COM** | 셀 선택(화면 이동) → 값·색·행 높이 → 저장 |
| 그림·슬라이드 (파워포인트) | 열어 둔 발표자료 | **COM** | 말하는 슬라이드로 이동, 작업본 슬라이드만 수정 |
| 웹 화면(미리보기, 근거 화면, 웹 서비스) | 사용자의 브라우저 창 | **CDP** (사용자 브라우저에 연결) | 탭 열기, 클릭·입력, 페이지 값 읽기 |
| 화면이 제대로 나오는지 확인 | (사용자 화면과 별개) | 헤드리스 Chrome / CDP | 캡처·DOM 뽑기로 모양 확인 |
| 원문 근거 짚기 | 근거 화면 | **evkit** (`evkit.point`) | 근거 위치에 상자 + 초안 줄에 같은 번호 |

어느 통로든 규칙은 같습니다. **원본은 복사본으로 지키고, 하기 전에 한 줄로 말하고, 고치는 자리를 보여 주고, 끝나면 사용자가 보는 모양으로 확인합니다.**

---

## 1. COM — 사용자가 열어 둔 문서 창 안에서 고치기 (Windows)

**흐름**
1. 원본은 복사본으로 만들어 두고, 복사본을 **보이는 창**으로 연다.
2. 에이전트는 실행 중인 앱에서 **그 문서 경로로 창을 찾아** 붙는다(아무 창에나 붙지 않게).
3. 고치기 전에 그 자리로 이동(찾기, 셀 선택, 슬라이드 이동)한 뒤 고친다. 사람은 화면으로 따라본다.
4. 저장한 뒤에는 **저장된 파일**(hwpx XML, PDF 내보내기)로 결과를 확인한다.
5. 끝나도 첫 페이지로 돌리지 않는다. 마지막으로 고친 자리에 둔다.

**앱별 진입점**

```python
import win32com.client as wc
xl = wc.GetActiveObject("Excel.Application")        # 열려 있는 엑셀에 붙기
wb = [b for b in xl.Workbooks if "작업본" in b.Name][0]
ws = wb.Worksheets("총괄(working)"); ws.Range("D16").Select(); ws.Range("D16").Value = "A-1"; wb.Save()

pp = wc.GetActiveObject("PowerPoint.Application")    # 파워포인트: 말하는 슬라이드로 이동
pres = [p for p in pp.Presentations if "working" in p.Name][0]
pp.ActiveWindow.View.GotoSlide(12)
```

한글은 실행 중 객체 목록(ROT)에서 문서 경로로 찾아 붙습니다. 코드와 함정은 [HWP_COM_NOTES.md](HWP_COM_NOTES.md)에 있습니다.

**지켜야 할 것**
- 앱 전체를 끄는 `Quit()`, 프로세스 강제 종료는 쓰지 않는다. 사람이 연 다른 창까지 닫힌다.
- 확인 전 값은 색(예: 빨강)으로 표시하고, 사람이 확인하면 바꾼다.
- 스크립트가 도는 동안 사람이 그 창에 타이핑하면 엉뚱한 곳이 고쳐진다. 미리 알려 둔다.
- 파워포인트 그림 작업은 "원본 슬라이드(숨김)와 작업본 슬라이드를 짝으로 두는" 작업 파일을 따로 만들면, 사람이 원본과 나란히 비교하며 고칠 수 있다.

## 2. CDP — 사용자 브라우저 안에서 같이 보고, 누르고, 읽기

CDP(Chrome DevTools Protocol)는 Chrome을 원격으로 조종하는 통로입니다. 두 가지로 씁니다.
- **같이 일하기**: 사용자가 보고 있는 Chrome 창에 에이전트가 붙어서 탭을 열고 누릅니다(2-2 끝 '사람이 보고 있는 브라우저에 붙기'). 사용자는 그 창에서 움직임을 그대로 봅니다.
- **확인하기**: 사용자 화면과 따로, 미리보기 표가 넘치는지, 번호가 맞는지, 뷰어가 비지 않는지 캡처로 확인합니다(2-1, 2-2).

### 2-1. 확인용: 헤드리스 Chrome 명령줄

```bash
# 화면 캡처
chrome --headless=new --disable-gpu --hide-scrollbars --window-size=1100,900 \
       --virtual-time-budget=8000 --screenshot=shot.png http://127.0.0.1:8765/
# 스크립트가 다 돈 뒤의 DOM 뽑기(페이지 안 값 확인용)
chrome --headless=new --virtual-time-budget=8000 --dump-dom http://127.0.0.1:8765/preview
```

- Windows 경로는 보통 `C:\Program Files\Google\Chrome\Application\chrome.exe` 입니다.
- `--user-data-dir=<임시폴더>` 를 주면 사람이 쓰는 브라우저 프로필과 섞이지 않습니다.
- **주의:** `--virtual-time-budget` 은 페이지 시간을 빨리 감습니다. 그래서 바깥(서버)에서 상태가 바뀌기를 기다리는 동작은 잡히지 않습니다. 예를 들어 "다른 프로세스가 /api/select 를 보낸 뒤 화면이 바뀌는지"는 확인할 수 없습니다. 이럴 때는 2-2처럼 CDP로 직접 클릭합니다.

### 2-2. 같이 일하기·클릭 확인: CDP (Playwright 사용)

CDP는 Chrome을 원격으로 조종하는 프로토콜입니다. Playwright·Puppeteer가 내부에서 이것을 씁니다.

```bash
pip install playwright && playwright install chromium
```

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1100, "height": 900})
    pg.goto("http://127.0.0.1:8765/")
    left = pg.frame_locator("#fl")                       # 왼쪽 초안 iframe
    left.locator('.ln[data-k="g1-2"]').click()           # 초안 줄 클릭 → 묶음 보기
    pg.wait_for_timeout(1500)
    print(pg.frame_locator("#fr").locator("#msg").inner_text())   # 근거 화면 상단 메시지
    pg.screenshot(path="group.png")
    b.close()
```

**사람이 보고 있는 브라우저에 붙기**: Chrome을 `--remote-debugging-port=9222 --user-data-dir=<작업용 프로필>` 로 띄우면, 에이전트가 `p.chromium.connect_over_cdp("http://127.0.0.1:9222")` 로 그 창에 붙어 탭을 열고 누를 수 있습니다. 사람은 같은 창에서 움직임을 봅니다.
- 원격 디버깅 포트가 열린 브라우저는 그 PC의 다른 프로그램도 조종할 수 있습니다. **작업용 프로필로만, 127.0.0.1 에서만** 쓰고 끝나면 닫으세요. 평소 쓰는 로그인 프로필로는 열지 마세요.

## 3. 확인은 "사람이 보는 모양"으로

| 무엇을 | 어떻게 |
|---|---|
| 한글·워드 문서 모양 | PDF로 내보내 쪽 그림으로 보고, 필요하면 표 선 좌표를 재서 비교(예: 캡션 가운데 vs 표 가운데) |
| 엑셀 행 높이·줄바꿈 | 범위를 PDF로 내보내 그림으로 확인 |
| 근거 상자 | `evkit.point --check` 확인 그림 |
| 브라우저 화면 | 헤드리스 캡처 또는 CDP 캡처 |
| 두 판의 차이 | 글자 대조(문단 diff)에 더해, PDF 쪽을 좌우로 놓고 바뀐 줄에 상자 치기 |

"됐다"고 말하기 전에 위 방법 중 하나로 실제 모양을 본다. 못 본 것은 못 봤다고 말한다.

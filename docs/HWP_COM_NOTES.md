# 한글(HWP)·엑셀 COM 자동화 메모 (Windows)

사람이 열어 둔 한글·엑셀 창을 에이전트가 COM(pyhwpx, pywin32)으로 직접 고치면, 사람이 화면을 보며 실시간으로 확인할 수 있습니다.
아래는 그렇게 작업하며 실제로 겪은 함정과 해결입니다.

## 공통 원칙

- **원본은 건드리지 않는다.** 복사본(`…_작업본.hwpx`, 엑셀은 원본 시트를 두고 `(working)` 시트를 새로 만들기)에서 작업한다.
- **작업하는 자리로 화면을 옮긴다.** 고치기 전에 찾기로 그 위치로 이동하고, 끝나도 첫 페이지로 돌리지 않는다. 사람이 무엇이 바뀌었는지 볼 수 있어야 한다.
- **검증은 저장된 파일로.** 창에서 읽은 값과 저장 파일이 다를 수 있다. hwpx는 XML(zip)을 열어 보거나 PDF로 뽑아 확인한다.
- **"확인 전" 값은 색으로 표시한다**(예: 빨간 글씨). 사람이 확인하면 검정으로 바꾼다.

## 한글(HWP/HWPX)

| 함정 | 해결 |
|---|---|
| 한글 프로세스 하나를 강제 종료하면 **다른 한글 창까지 모두** 꺼질 수 있음 | 프로세스 강제 종료 금지 |
| `Quit()` 은 그 문서가 아니라 **한글 앱 전체**를 닫음 | 문서만 닫기: `XHwpDocuments.Item(i).Close(False)` |
| `Hwp()` 로 붙으면 **아무 한글 창**에나 붙음 | ROT(실행 중 객체 목록)에서 문서 경로로 찾아 붙고, `assert` 로 경로를 확인한 뒤 수정 (아래 코드) |
| 숨김 창으로 열면 보안·복구 대화상자에 걸려 멈춤 | 보이는 창으로 열고 `SetMessageBoxMode(0x00020011)` |
| `find()` 로 찾은 뒤 `insert_text()` 하면 **선택 영역이 바뀌지 않고 뒤에 덧붙음**. 이어서 `Delete` 하면 커서 뒤 한 글자만 지워짐 | 바꾸기는 찾아 바꾸기(`find_replace_all`)로. **찾을 글을 문서에서 한 번만 나오게** 앞뒤 글을 붙여서 |
| pyhwpx `find_replace_all` 기본값 `SeveralWords=1` 은 **쉼표를 '여러 단어 찾기' 구분자**로 읽음 → 쉼표가 든 글을 바꾸면 엉망이 됨 | `SeveralWords=0, AutoSpell=0, AllWordForms=0` 을 꼭 지정 |
| 표 칸 안 글을 통째로 바꾸기 | 칸 안으로 이동 → `MoveListBegin` → `MoveSelListEnd` → `Delete` → `insert_text` + `BreakPara` 로 줄마다. 글자색은 `CharShape` 액션으로 |
| 변경 내용 추적(검토) 수락 | `HAction.Run("TrackChangeApplyAll")`. 반환값이 False여도 수락되는 경우가 있으니 저장본 XML에서 `insertBegin/deleteBegin` 개수로 확인 |
| 표를 본문보다 넓게 하고 가운데 맞추기 | 표 폭은 `set_col_width([mm…], as_="mm")`. 표가 든 문단의 왼·오른 여백을 음수로, 첫 줄 들여쓰기 0, 가운데 정렬. **본문 영역 자체가 쪽 가운데가 아닐 수 있으니 캡션 가운데와 표 가운데를 PDF로 재서** 맞춘다(여백 보정량의 절반만큼 움직임) |
| hwpx 문단 여백·탭 값이 **2배 값**으로 저장되고 위/아래 간격 배율이 들쭉날쭉 | 큰 간격은 빈 줄로. 값은 PDF로 뽑아 실측 |
| 표 칸 높이는 저장 시 갱신되지 않음 | 칸 안 줄 위치(`linesegarray`)로 실제 높이 계산 |
| 수식 | `EquationCreate` + 한글 수식 스크립트(LaTeX 변환: `\frac`→`over`, `\sum\limits`→`sum from{} to{}` 등) |
| 확인용 PDF | `SaveAs(경로, "PDF", "")` — 문서 경로는 바뀌지 않음 |
| 작업 중 사람이 그 창에 타이핑 | 선택 영역이 바뀌어 엉뚱한 곳이 고쳐짐. 실행 중에는 그 창에 입력하지 않도록 안내 |

문서 경로로 한글 창 찾기:

```python
import pythoncom, win32com.client
from pyhwpx import Hwp

def find_disp(key):
    rot = pythoncom.GetRunningObjectTable(); ctx = pythoncom.CreateBindCtx(0)
    for m in rot.EnumRunning():
        if m.GetDisplayName(ctx, None).startswith("!HwpObject"):
            d = win32com.client.Dispatch(rot.GetObject(m).QueryInterface(pythoncom.IID_IDispatch))
            if key in (d.Path or ""):
                return d
    raise SystemExit("문서 창을 찾지 못함: " + key)

hwp = Hwp()
hwp.hwp = find_disp("작업본")
assert "작업본" in hwp.Path
```

## 엑셀

| 함정 | 해결 |
|---|---|
| 엑셀 앱 전체를 끄면 사람이 연 다른 통합문서도 닫힘 | `Workbook.Close(False)` 로 그 통합문서만 |
| 서식 예시 행을 지우면 합계 수식 범위가 줄어듦 | 원본 시트는 그대로 두고 `Sheet.Copy` 로 작업 시트를 만들어 거기서. 행은 예시 행 아래(합계 행 위)에 `Insert` |
| **병합 칸·한글은 `AutoFit` 이 행 높이를 덜 잡음**(글이 눌림) | 칸 폭(ColumnWidth)과 글자 수로 줄 수를 계산해 `RowHeight` 를 직접 지정. 대략 한글 1자 ≈ 1.95, 영문·숫자 ≈ 1.05, 공백 ≈ 0.55 폭 단위, 11pt 한 줄 ≈ 16.5pt |
| 같은 값을 여러 칸에 | 셀마다 `Select()` 한 뒤 쓰면 사람이 화면에서 따라볼 수 있음(조금 느림) |
| 확인 | 범위를 `ExportAsFixedFormat(0, pdf)` 로 뽑아 그림으로 본다 |

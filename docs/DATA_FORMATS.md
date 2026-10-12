# 데이터 형식

모든 상태는 프로젝트의 `state_dir`(기본 `.evkit/`) 안에 JSON으로 있습니다. 사람이 열어 봐도 되고, 다른 도구가 써도 됩니다.

## 근거 표시 (`pointer.json`) · 근거 기록 (`history/<이름>.json`)

```json
{
  "seq": 12,
  "time": "14:03:51",
  "msg": "무엇을 보여 주는지",
  "marks": [
    {"n": 1, "doc": "spec", "page": 12, "filepage": 12,
     "rects": [[60.0, 120.5, 540.0, 168.2]],
     "note": "[k3] 설명 (사양서 12쪽)"}
  ]
}
```

| 필드 | 뜻 |
|---|---|
| `seq` | 바뀔 때마다 1씩 커짐. 화면은 이 값이 바뀌면 새 표시로 이동 |
| `doc` | project.json `docs` 의 키 |
| `page` / `filepage` | 원본 쪽 번호 / PDF 안 쪽 번호 |
| `rects` | 상자들. PDF 좌표(pt, 왼쪽 위가 원점) |
| `note` | `[초안키]` 로 시작하면 초안 줄과 이어짐 |

근거 기록은 `pointer.json` 을 그대로 복사한 것입니다. 묶음 보기는 `history/` 의 모든 기록을 **수정 시각 순서로** 읽어 키별로 모으고, 같은 키는 나중 기록이 이깁니다.

## 사람 표시 (`user.json`)

```json
{"marks": [{"id": 1, "doc": "spec", "doc_name": "사양서 v2", "page": 12, "filepage": 12,
            "rect": [70.2, 300.0, 320.5, 340.8], "text": "상자 안 글", "note": "이거 맞아?",
            "crop": ".evkit/marks/mark_1.png", "time": "14:05:10"}]}
```

## 서버 API

| 경로 | 내용 |
|---|---|
| `GET /api/docs` | `{title, docs: {키: {name, unit, pages, clips, map?, stamp}}}` |
| `GET /api/drafts` | `[{label, i}]` |
| `GET /api/state` | `{pointer, user, select, docs_ver}` |
| `GET /api/evidence` | `{keys: {초안키: [mark…]}, src: {초안키: 기록이름}}` |
| `GET /api/histories` | `[{name, msg, marks}]` |
| `GET /api/version?d=N` | 초안 N 파일 수정 시각(바뀌면 미리보기가 새로고침) |
| `POST /api/select` | `{group, keys, key, label}` — 초안 줄 클릭 |
| `POST /api/mode` | `{mode: "agent" \| "group"}` |
| `POST /api/user` | `{type: "mark", doc, filepage, rect, note}` / `{type: "clear"}` / `{type: "delete", id}` |
| `GET /page/<문서>/<쪽>.png` | 쪽 그림(캐시) |
| `GET /doc/<문서>.pdf` | 원본 PDF |
| `GET /assets/<경로>` | 프로젝트 폴더 안 파일(초안 그림) |

단일 파일 뷰어에서는 `web/shim.js` 가 위 GET/POST 를 같은 형식으로 대신 응답합니다.

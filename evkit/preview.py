# -*- coding: utf-8 -*-
"""초안(.md) → 미리보기 HTML. 줄마다 근거 키 배지, 묶음 클릭, 근거 번호 표시가 들어간다.

초안 문법 (README 'Draft syntax' 참고)
  # 제목 / ## 절 / ### 소절
  ○ 큰 항목      - 중간 항목      · 작은 항목      (앞 공백은 들여쓰기 그대로)
  줄 끝 {@키}     그 줄의 근거 키. 근거 기록 메모 "[키] …" 와 이어짐
  **굵게**  {red}빨강{/red}  {chg}초록(수정 표시){/chg}  {todo}노랑(확인 필요){/todo}
  | 표 | 칸 |     마크다운 표(구분 줄 |---| 포함)
  ![캡션](그림경로)   프로젝트 폴더 기준 경로
  $수식$          project.json "math": true 일 때 MathJax(CDN)
  <!-- 주석 -->   미리보기에 안 나옴

묶음: '○' 줄이나 제목(#~###)이 묶음을 시작하고, 다음 '○'/제목 전까지가 한 묶음.
줄을 누르면 그 묶음의 키 전체를 서버(/api/select)에 알리고, 근거 화면이 묶음의 근거를 모아 보여 준다."""
import html
import os
import re

BUL = re.compile(r"^(\s*)(○|■|□|-|·|\*|•)\s+(.*)$")
KEYRE = re.compile(r"\s*\{@([\w.-]+)\}\s*$")
LEVEL = {"○": 1, "■": 1, "□": 1, "-": 2, "•": 2, "*": 2, "·": 3}


def inline(s, math=False):
    t = html.escape(s, quote=False)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    for tag, cls in (("red", "c-red"), ("chg", "c-chg"), ("todo", "c-todo")):
        t = re.sub(r"\{%s\}(.*?)\{/%s\}" % (tag, tag), r'<span class="%s">\1</span>' % cls, t)
    if not math:
        t = t.replace("$", "&#36;")
    return t


def render(text, math=False):
    """→ (본문 HTML, 묶음 목록)"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.split("\n")
    out, groups, gid, i = [], [], -1, 0

    def new_group(label):
        nonlocal gid
        gid += 1
        groups.append({"id": gid, "label": label, "keys": []})

    def line(cls, body, key, extra=""):
        if gid < 0:
            new_group("")
        if key:
            groups[gid]["keys"].append(key)
        k = ' data-k="%s"' % key if key else ""
        badge = '<span class="badge" title="근거 키 %s">◀</span>' % key if key else ""
        out.append('<div class="ln %s" data-g="%d"%s%s>%s%s<span class="lab"></span></div>' % (cls, gid, k, extra, body, badge))

    while i < len(lines):
        raw = lines[i].rstrip()
        i += 1
        if not raw.strip():
            out.append('<div class="gap"></div>')
            continue
        if raw.lstrip().startswith("|"):  # 표
            rows = [raw]
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i].rstrip())
                i += 1
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
            cells = [r for r in cells if not all(re.fullmatch(r":?-{2,}:?", c) for c in r)]
            h = ['<table class="tbl">']
            for r_i, r in enumerate(cells):
                tag = "th" if r_i == 0 else "td"
                tds = []
                for c in r:
                    m = KEYRE.search(c)
                    key = m.group(1) if m else None
                    c2 = KEYRE.sub("", c)
                    if key and gid >= 0:
                        groups[gid]["keys"].append(key)
                    attrs = (' class="ln cell" data-g="%d" data-k="%s"' % (max(gid, 0), key)) if key else ""
                    badge = '<span class="badge">◀</span><span class="lab"></span>' if key else ""
                    tds.append("<%s%s>%s%s</%s>" % (tag, attrs, inline(c2, math).replace("&lt;br&gt;", "<br/>"), badge, tag))
                h.append("<tr>%s</tr>" % "".join(tds))
            h.append("</table>")
            out.append("".join(h))
            continue
        m = KEYRE.search(raw)
        key = m.group(1) if m else None
        body = KEYRE.sub("", raw)
        hm = re.match(r"^(#{1,3})\s+(.*)$", body)
        if hm:
            lv = len(hm.group(1))
            new_group(re.sub(r"\{/?\w+\}|\*\*", "", hm.group(2)))
            line("h%d" % lv, inline(hm.group(2), math), key)
            continue
        im = re.match(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$", body)
        if im:
            cap, src = im.group(1), im.group(2)
            if not re.match(r"^(https?:|data:|/)", src):
                src = "/assets/" + src
            line("fig", '<img src="%s" alt=""/><div class="cap">%s</div>' % (html.escape(src), inline(cap, math)), key)
            continue
        bm = BUL.match(body)
        if bm:
            ind, b, rest = bm.groups()
            lv = LEVEL.get(b, 2)
            if lv == 1:
                new_group(re.sub(r"\{/?\w+\}|\*\*", "", rest))
            pad = len(ind.replace("\t", "  "))
            line("b%d" % lv, '<span class="bul">%s</span><span class="tx">%s</span>' % (html.escape(b), inline(rest, math)),
                 key, ' style="--ind:%dch"' % pad)
            continue
        line("p", inline(body, math), key)
    return "\n".join(out), groups


CSS = r"""
:root{--paper:#fff;--ink:#111;--muted:#666;--bg:#8a8a8a}
html,body{margin:0;background:var(--bg)}
body{font:14px/1.75 "Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;color:var(--ink)}
#bar{position:sticky;top:0;z-index:9;background:#2b2b2b;color:#eee;font-size:12px;padding:4px 10px;display:flex;gap:12px;align-items:center;white-space:nowrap;overflow:hidden}
#bar b{display:none} /* title already shown in the outer select */
#bar span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;color:#aaa}
#bar label{cursor:pointer}
.paper{background:var(--paper);width:min(820px,94vw);margin:16px auto 40px;padding:36px 70px 48px 48px;box-shadow:0 1px 6px rgba(0,0,0,.4);box-sizing:border-box;position:relative}
.ln{position:relative;border-radius:3px;padding:0 4px;cursor:pointer}
.ln:hover{background:#f3f0ff}
.h1{font-size:22px;font-weight:bold;margin:6px 0 10px}
.h2{font-size:18px;font-weight:bold;margin:14px 0 6px}
.h3{font-size:15.5px;font-weight:bold;margin:10px 0 4px}
.b1,.b2,.b3{display:flex;padding-left:calc(var(--ind,0ch) + 4px)}
.b2{margin-left:1.2em}.b3{margin-left:2.4em}
.bul{flex:none;width:1.4em}
.tx{flex:1}
.b1{font-weight:bold;margin-top:6px}
.gap{height:8px}
.fig{text-align:center;margin:8px 0}.fig img{max-width:100%}.fig .cap{font-size:12.5px;color:#333}
.tbl{border-collapse:collapse;margin:8px auto;font-size:13px}
.tbl th,.tbl td{border:1px solid #444;padding:3px 8px;vertical-align:middle}
.tbl th{background:#eee}
.tbl td.ln{cursor:pointer}
.badge{color:#b07000;font-size:11px;margin-left:4px;cursor:pointer}
body.hide-ev .badge{display:none}
.c-red{color:#d00}.c-chg{color:#0a0}.c-todo{background:#fff2a8}
.lab{display:none;position:absolute;right:-62px;top:2px;font:bold 11px/16px "Malgun Gothic",sans-serif;color:#222;padding:0 6px;border-radius:3px;white-space:nowrap}
.ln.has-lab{outline:2px solid var(--lc);outline-offset:1px}
.ln.has-lab>.lab{display:block;background:var(--lc)}
td.ln.has-lab>.lab{right:auto;left:100%;margin-left:4px}
.ln.sel-group{background:#f7f4ff}
/* the evidence being viewed (chip clicked on the right) must stand out from the rest of its group:
   declared after .sel-group so it wins, with a thicker, darker outline */
.ln.focus{background:#fff6c7}
.ln.has-lab.focus{outline:3px solid color-mix(in srgb,var(--lc) 60%,#fff);outline-offset:1px} /* same color as the highlighter on the right */
/* the active line's label keeps its pastel chip color: the outline alone marks it, quietly */
"""

JS = r"""
var DRAFT=__DRAFT__, PAL=["#f2a7a7","#9fd6a8","#9fc3ef","#f6c08f","#c9b2ee","#8fd3cb","#f1afd6","#d9c09a","#e7b0b0","#aab6e8","#d3d48c","#f0d080"];
function col(n){return PAL[(n-1)%PAL.length];}
function $all(q){return [].slice.call(document.querySelectorAll(q));}
var GROUPS=__GROUPS__, mode="agent", ptrSeq=-1, selSeq=null, ptr={marks:[]}, sel=null, ev=null;
function keyOf(m){var r=/^\[([\w.-]+)\]/.exec(m.note||"");return r?r[1]:null;}
function clearLabs(){$all(".ln").forEach(function(e){e.classList.remove("has-lab","sel-group");var l=e.querySelector(".lab");if(l){l.textContent="";}});}
function putLab(k,text,c){$all('.ln[data-k="'+k+'"]').forEach(function(e){e.classList.add("has-lab");e.style.setProperty("--lc",c);var l=e.querySelector(".lab");if(l){l.textContent=text;}});}
function paint(){
  clearLabs();
  if(mode==="agent"){var order=[],seen={};(ptr.marks||[]).forEach(function(m){var k=keyOf(m);if(k&&!seen[k]){seen[k]=1;order.push(k);}});
    order.forEach(function(k,i){putLab(k,"#"+(i+1),col(i+1));});}
  else if(sel&&ev){var g=GROUPS[sel.group]; if(!g)return; $all('.ln[data-g="'+sel.group+'"]').forEach(function(e){e.classList.add("sel-group");});
    var n=0; (g.keys||[]).forEach(function(k){if((ev.keys[k]||[]).length){n++;putLab(k,"근거 "+n,col(n));}});}
}
function focusKey(k){$all(".ln.focus").forEach(function(e){e.classList.remove("focus");});
  var e=document.querySelector('.ln[data-k="'+k+'"]'); if(e){e.classList.add("focus");e.scrollIntoView({block:"center",behavior:"smooth"});}}
window.addEventListener("message",function(e){if(e.data&&e.data.type==="ptr"&&e.data.key){focusKey(e.data.key);}});
document.addEventListener("click",function(e){
  var ln=e.target.closest(".ln"); if(!ln)return;
  var g=+ln.dataset.g, grp=GROUPS[g]; if(!grp)return;
  var key=ln.dataset.k||(grp.keys||[])[0]||null;
  fetch("/api/select",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({group:g,keys:grp.keys,key:key,label:grp.label})});
  if(key){try{parent.postMessage({type:"draft",key:key},"*");}catch(x){}}
  $all(".ln.focus").forEach(function(x){x.classList.remove("focus");}); ln.classList.add("focus");
});
function loadEv(cb){fetch("/api/evidence?t="+Date.now()).then(function(r){return r.json();}).then(function(d){ev=d;cb&&cb();}).catch(function(){});}
function poll(){
  fetch("/api/state?t="+Date.now()).then(function(r){return r.json();}).then(function(s){
    var p=s.pointer||{marks:[]}, se=s.select||{seq:0};
    if(p.seq!==ptrSeq){var first=ptrSeq===-1;ptrSeq=p.seq;ptr=p;if(!first){mode="agent";}paint();}
    if(selSeq===null){selSeq=se.seq;}
    else if(se.seq!==selSeq){selSeq=se.seq; if(se.mode==="agent"){mode="agent";paint();} else {sel=se;mode="group";loadEv(paint);}}
  }).catch(function(){});
}
poll(); setInterval(poll,1000);
// 초안 파일이 바뀌면 다시 불러온다(스크롤 위치 유지)
var ver=null;
setInterval(function(){fetch("/api/version?d="+DRAFT+"&t="+Date.now()).then(function(r){return r.text();}).then(function(v){
  if(ver===null){ver=v;} else if(v!==ver){try{sessionStorage.setItem("evk-scroll-"+DRAFT,String(window.scrollY));}catch(x){} location.reload();}}).catch(function(){});},1500);
try{var y=sessionStorage.getItem("evk-scroll-"+DRAFT); if(y){window.scrollTo(0,+y);}}catch(x){}
var hb=document.getElementById("hide-ev"); hb.onchange=function(){document.body.classList.toggle("hide-ev",hb.checked);};
"""


def build(project, i=0):
    d = project.draft(i)
    if not d:
        return "<!doctype html><meta charset='utf-8'><p>project.json 의 drafts 가 비어 있습니다.</p>"
    path = project.abs(d["file"])
    text = open(path, encoding="utf-8").read() if os.path.exists(path) else "(초안 파일 없음: %s)" % d["file"]
    math = bool(project.cfg.get("math"))
    body, groups = render(text, math)
    import json
    js = JS.replace("__DRAFT__", str(int(i))).replace("__GROUPS__", json.dumps(groups, ensure_ascii=False).replace("</", "<\\/"))
    mj = ('<script>window.MathJax={tex:{inlineMath:[["$","$"]]}};</script>'
          '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>') if math else ""
    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"/><title>%s</title><style>%s</style>%s</head><body>"
            "<div id=\"bar\"><b>%s</b><span>줄을 누르면 근거가 오른쪽에 뜹니다</span>"
            "<label><input type=\"checkbox\" id=\"hide-ev\"/> 근거 키(◀) 숨기기</label></div>"
            "<div class=\"paper\">%s</div><script>%s</script></body></html>") % (
        html.escape(d.get("label", "초안")), CSS, mj, html.escape(d.get("label", "초안")), body, js)


def version(project, i=0):
    d = project.draft(i)
    if not d:
        return "0"
    p = project.abs(d["file"])
    return str(os.path.getmtime(p)) if os.path.exists(p) else "0"

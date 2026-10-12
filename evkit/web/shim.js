/* 단일 파일 뷰어용 shim.
 * 실시간 서버가 응답하던 주소(/api/*)를 부모 페이지의 데이터(window.parent.__VSTATE)로 대신 응답한다.
 * build_viewer.py 가 각 화면 <head> 맨 앞에 넣는다. 그래서 화면 코드는 서버판과 같은 것을 그대로 쓴다.
 */
(function () {
  var S = window.parent.__VSTATE;
  function route(m, url, body) {
    url = String(url).split("?")[0];
    if (url === "/api/version") return "static";
    if (url === "/api/state") return {pointer: S.pointer, user: {marks: []}, select: S.select, docs_ver: "static"};
    if (url === "/api/evidence") return S.evidence;
    if (url === "/api/histories") return S.histories;
    if (url === "/api/docs") return {title: S.title, docs: S.docs};
    if (url === "/api/drafts") return S.drafts;
    if (url === "/api/user") return {ok: true};
    if (url === "/api/select") {
      var b = JSON.parse(body || "{}");
      S.select = {seq: S.select.seq + 1, mode: "group", group: b.group, keys: b.keys || [], key: b.key, label: b.label || ""};
      return {ok: true};
    }
    if (url === "/api/mode") {
      var c = JSON.parse(body || "{}"), s = {};
      for (var k in S.select) { s[k] = S.select[k]; }
      s.seq = S.select.seq + 1; s.mode = c.mode === "agent" ? "agent" : "group"; S.select = s;
      return {ok: true};
    }
    return null;
  }
  function txt(r) { return typeof r === "string" ? r : JSON.stringify(r); }
  var of = window.fetch;
  window.fetch = function (u, o) {
    var r = route((o && o.method) || "GET", u, o && o.body);
    if (r === null) { return of.apply(this, arguments); }
    return Promise.resolve({ok: true, status: 200,
      json: function () { return Promise.resolve(JSON.parse(txt(r))); },
      text: function () { return Promise.resolve(txt(r)); }});
  };
})();

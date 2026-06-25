# -*- coding: utf-8 -*-
"""
MBO 성과 AI - Render 배포용 서버 (더미 데이터)
공개 인터넷에 올라가므로: (1) 데이터는 더미만 사용 (2) 접속 비밀번호로 보호
키와 비번은 Render 환경변수에서만 읽습니다 (코드/깃허브에 없음).

환경변수:
  ANTHROPIC_API_KEY  = sk-ant-...   (필수)
  APP_PASSWORD       = 접속 비밀번호 (없으면 기본값 etoos2026)
  PORT               = Render가 자동 주입
"""

import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from anthropic import Anthropic
except ImportError:
    print("[설치 필요] pip install anthropic")
    sys.exit(1)

HERE = os.path.dirname(os.path.abspath(__file__))

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
if not API_KEY.startswith("sk-ant-"):
    print("[오류] 환경변수 ANTHROPIC_API_KEY 가 없거나 형식이 이상합니다.")
    sys.exit(1)

APP_PASSWORD = os.environ.get("APP_PASSWORD", "etoos2026").strip()
AUTH_USER = "etoos"  # 비번만 맞으면 됨 (아이디는 고정)

client = Anthropic(api_key=API_KEY)

with open(os.path.join(HERE, "dummy_data.json"), encoding="utf-8") as f:
    DB = json.load(f)
PEOPLE = DB["person"]
ORG = DB["org"]
NAMES = ", ".join(p["name"] for p in PEOPLE)

SYSTEM_PROMPT = f"""당신은 이투스에듀 인사팀의 조직·성과 분석 AI입니다(데모, 모든 데이터는 가명 더미).
두 종류의 데이터를 가지고 있습니다.

[개인 데이터] 인사팀 팀원 {len(PEOPLE)}명({NAMES})의 26년 MBO·중간점검·25년 인사평가.
[전사 데이터] 26년 MBO 본부별 집계(9개 본부): 정량/정성 비율, 업무구분(기본·중점·개선), 지표수 분포.

먼저 질문이 '개인/팀'인지 '전사/본부'인지 스스로 판단(scope)한 뒤, 해당 데이터만 근거로 답하세요.
반드시 아래 JSON 하나로만 응답합니다(앞뒤 설명·마크다운펜스 금지, 순수 JSON):

{{
 "scope": "personal | org",
 "headline": "한 줄 핵심 결론",
 "subline": "1~2문장 보조 설명",
 "blocks": [ 블록 배열 - 아래 종류 중 선택 ],
 "narrative": "추가 분석. ### 소제목으로 2~3단락, **굵게**는 핵심만, [[핵심수치]] 강조. 마지막은 ### 다음 할 일.",
 "related": ["방금 답과 같은 범위에서 더 깊이 들어가는 후속질문 3개. 짧은 질문체."],
 "recommended": ["다른 범위로 넓히는 추천질문 2개. personal이면 전사/본부 질문, org면 개인/팀 질문. 짧은 질문체."]
}}

[블록 종류]
- 진척 카드: {{"type":"progress","items":[{{"title":"목표명(짧게)","note":"요약(25자 이내)","pct":정수,"status":"정상|주의|목표미달","badge":"선택"}}]}}
- KPI 카드: {{"type":"kpi","items":[{{"k":"라벨","v":"값","unit":"단위(선택)"}}]}}
- 도넛: {{"type":"donut","centerB":"가운데 큰값","centerS":"가운데 라벨","parts":[{{"name":"이름","val":비율수,"cnt":건수,"color":"#hex"}}]}}
- 가로 막대(누적): {{"type":"hbars","segs":["정량","정성"],"rows":[{{"name":"본부","vals":{{"정량":55,"정성":45}},"tot":611}}]}}
- 랭킹: {{"type":"rank","rows":[{{"name":"이름","val":69.8}}]}}

[색상] 정량/기본 #5BA8FF · 정성 #A78BFA · 중점 #2DD4BF · 개선 #E8B14C

[규칙]
- 개인 진척 -> progress. status: pct<40 목표미달, 40~59 주의, 60+ 정상. pct는 데이터 값 그대로.
- 여러 팀원 비교/순위 -> rank(개인별 평균 진척률). 전사 비율/구성 -> donut+hbars, 순위 -> rank, 요약 -> kpi+donut.
- related 3개·recommended 2개 항상. 개인답이면 recommended=전사, 전사답이면 recommended=개인/팀.
- 데이터에 없으면 "기록 없음" 명시, 추측 금지. 한국어로 간결하게. blocks 수치는 데이터 실제 값만.

[개인 데이터]
{json.dumps(PEOPLE, ensure_ascii=False)}

[전사 데이터]
{json.dumps(ORG, ensure_ascii=False)}"""


def avg_progress(p):
    s = w = 0
    for g in p.get("y2026", {}).get("중간점검", {}).get("goals", []):
        pct = g.get("진척률") or 0
        ww = g.get("가중치") or 0
        s += pct * ww
        w += ww
    return round(s / w) if w else 0


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json", extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _authed(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            user, pw = base64.b64decode(h[6:]).decode("utf-8").split(":", 1)
        except Exception:
            return False
        return pw == APP_PASSWORD

    def _ask_login(self):
        self._send(401, "로그인이 필요합니다.", "text/plain",
                   {"WWW-Authenticate": 'Basic realm="MBO AI"'})

    def do_GET(self):
        if not self._authed():
            return self._ask_login()
        if self.path == "/meta":
            meta = {
                "teamName": "인사팀",
                "people": len(PEOPLE),
                "orgUnits": ORG.get("total", {}).get("본부수"),
                "orgTotal": ORG.get("total", {}).get("총건수"),
            }
            return self._send(200, json.dumps(meta, ensure_ascii=False))
        path = "index.html" if self.path in ("/", "/index.html") else os.path.basename(self.path)
        full = os.path.join(HERE, path)
        if os.path.exists(full) and full.endswith(".html"):
            with open(full, "rb") as f:
                return self._send(200, f.read(), "text/html")
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._authed():
            return self._ask_login()
        if self.path != "/ask":
            return self._send(404, json.dumps({"error": "unknown path"}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            question = (payload.get("question") or "").strip()
            history = payload.get("history") or []
            if not question:
                return self._send(400, json.dumps({"error": "empty question"}))
            messages = history + [{"role": "user", "content": question}]
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2200,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            self._send(200, json.dumps({"reply": text}, ensure_ascii=False))
        except Exception as e:
            print("[ERROR]", repr(e))
            self._send(500, json.dumps({"error": str(e)}, ensure_ascii=False))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"MBO AI (더미) 서버 실행 · 포트 {port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

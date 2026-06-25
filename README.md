# MBO 성과 AI (데모)

개인·팀·전사 MBO 성과를 자연어 질문으로 분석하는 AI 챗봇.
질문하면 진척 카드 / 도넛 / 막대 / 랭킹 차트와 분석을 생성하고,
연관·추천 질문으로 개인↔전사 탐색을 이어줍니다.

- **데이터:** 전부 가명 더미 (개인 4명 + 전사 9개 본부)
- **스택:** Python(표준 http.server) + Anthropic Claude API + 단일 HTML(SVG/CSS 차트)
- **보안:** HTTP 기본 인증(접속 비밀번호)

> 이투스에듀 인사팀 재직 중 개인 설계 프로젝트. 실데이터는 사내망에서만 운영.

## 로컬 실행
```
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...   (Windows)
python app.py
```
http://localhost:8000  (아이디 etoos / 비번 기본 etoos2026)

## 환경변수
- `ANTHROPIC_API_KEY` : Anthropic API 키
- `APP_PASSWORD` : 접속 비밀번호 (미설정 시 etoos2026)

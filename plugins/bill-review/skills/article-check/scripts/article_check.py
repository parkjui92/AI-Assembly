#!/usr/bin/env python3
"""조문 대조 검문소 — 검토보고서 초안의 인용 조문과 신구조문대비표를 조문 원장과 기계로 맞춘다.

쓰는 법
  python3 article_check.py --list  의안원문.md [초안.md ...]        # 원장에 넣을 조문 목록
  python3 article_check.py 초안.md --ledger 03b_조문원장 --bill 의안원문.md [--date 2023-02-16]
  python3 article_check.py --selftest

종료코드  0 통과 · 1 불통과(✕ 1건 이상 — 산출 보류) · 2 실행 오류(파일 없음·원장 형식 오류)
표준 라이브러리만 쓴다. 조문을 조회하지 않는다 — 조회는 사람이(또는 조사관이 법령 도구로) 하고,
이 스크립트는 '조회해 둔 원문'과 '초안이 쓴 글자'가 같은지만 본다.
"""
import argparse
import datetime as _dt
import os
import re
import sys
import tempfile
import unicodedata

VERSION = "0.1.1"

# ---------------------------------------------------------------- 글자 맞추기
_DOTS = "ㆍ·⋅･・•∙"
_MARKERS = re.compile(
    r"<\s*(?:개정|신설|전문개정|타법개정|본조신설|제목개정|종전|삭제)[^<>]*?\d{4}[^<>]*>"
    r"|\[\s*(?:본조신설|전문개정|제목개정|종전|시행일)[^\[\]]*\]"
)


def norm(text):
    """비교용 정규화 — 공백을 모두 지우고 같은 뜻의 다른 글자를 하나로 모은다."""
    t = unicodedata.normalize("NFC", text or "")
    t = _MARKERS.sub("", t)
    t = t.replace("<br>", "").replace("<br/>", "").replace("<br />", "")
    for ch in _DOTS:
        t = t.replace(ch, "·")
    t = (t.replace("“", '"').replace("”", '"').replace("″", '"')
          .replace("‘", "'").replace("’", "'")
          .replace("｢", "「").replace("｣", "」")
          .replace("∼", "~").replace("～", "~").replace("〜", "~"))
    t = re.sub(r"\*\*|__", "", t)
    # 조문 머리의 괄호 제목: 법령 도구는 항이 없는 조문을 '제23조 권한의 위임'으로 준다 → 양쪽 모두 괄호를 걷는다
    t = re.sub(r"(제\s*\d+\s*조(?:\s*의\s*\d+)?)\s*\(([^()]{1,40})\)", r"\1\2", t)
    return re.sub(r"\s+", "", t)


def flat(text):
    return re.sub(r"\s+", "", text or "")


# ---------------------------------------------------------------- 조문 번호
_ART = r"제\s*(\d+)\s*조(?:\s*의\s*(\d+))?"
_PARA = r"(?:\s*제\s*(\d+)\s*항)?"
_ITEM = r"(?:\s*제\s*(\d+)\s*호(?:\s*의\s*(\d+))?)?"
ART_REF = re.compile(_ART + _PARA + _ITEM)
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def art_key(num, sub):
    return f"제{int(num)}조" + (f"의{int(sub)}" if sub else "")


def ref_label(m):
    num, sub, para, item, itemsub = m.groups()[:5]
    s = art_key(num, sub)
    if para:
        s += f"제{int(para)}항"
    if item:
        s += f"제{int(item)}호" + (f"의{int(itemsub)}" if itemsub else "")
    return s


LAW_SUFFIX = re.compile(r"(법|법률|시행령|시행규칙|규칙|규정|령|조례|헌법|협정|협약|조약)$")


def is_law_name(name):
    n = flat(name)
    if not n or n.endswith("안") or n.endswith("법률안") or "보고서" in n or "교재" in n:
        return False
    return bool(LAW_SUFFIX.search(n))


# ---------------------------------------------------------------- 조문 원장
class Law:
    def __init__(self, name, date, path):
        self.name, self.date, self.path = name, date, path
        self.scope = ""            # '전문' 또는 조문 나열
        self.missing = set()       # 조회했으나 없다고 확인된 조문
        self.deleted = set()       # 원장 본문에 '삭제 <날짜>'로 온 조문
        self.target = False
        self.records = []
        self.body = ""
        self.articles = {}         # 제22조 -> 본문

    # 조문 머리 — 법령 도구는 세 모양으로 준다(2026-10 실측, korean-law-mcp 4.15):
    #   '제22조(자전거의 등록 등) ① …'   항이 있는 조문(앞 줄에 '제22조 자전거의 등록 등'도 온다)
    #   '제23조 권한의 위임'              항이 없는 조문 — 괄호 없이 제목만, 본문은 다음 줄
    #   '제15조' + '삭제 <2009.12.29>'    삭제된 조문
    HEAD = re.compile(r"(?m)^[ \t]*" + _ART + r"(?:\s*\(|[ \t]+(?P<title>[^\n]{1,40})$|[ \t]*$)")
    TOOL_LINE = re.compile(r"^\s*(법령명|공포일|시행일|⚠️|ℹ️|💡|📍)")

    def index(self):
        heads = []
        for h in self.HEAD.finditer(self.body):
            title = h.group("title")
            # 본문 문장이 '제5조에 따라 …'로 시작하는 줄을 머리로 잘못 읽지 않게: 제목은 마침표·조사로 끝나지 않는다
            if title and (title.rstrip().endswith((".", "다", "다.")) or re.search(r"(에|를|을|의|에서|따라|따른)\s", title + " ") and len(title) > 25):
                continue
            heads.append(h)
        for i, h in enumerate(heads):
            key = art_key(h.group(1), h.group(2))
            end = heads[i + 1].start() if i + 1 < len(heads) else len(self.body)
            chunk = self.body[h.start():end]
            # 같은 조문을 두 번 조회했으면(또는 머리줄이 두 번 오면) 긴 쪽을 쓴다
            if len(chunk) > len(self.articles.get(key, "")):
                self.articles[key] = chunk
        # 삭제 조문: 머리 다음 줄이 '삭제 <날짜>'뿐이면 그 시점에 없는 조문으로 친다
        for key, chunk in list(self.articles.items()):
            lines = [l.strip() for l in chunk.strip().splitlines()[1:] if l.strip() and not self.TOOL_LINE.match(l)]
            if lines and all(re.fullmatch(r"삭제\s*(<[^<>]*>)?", l) for l in lines):
                self.missing.add(key)
                self.deleted.add(key)
                del self.articles[key]

    @property
    def full(self):
        return "전문" in self.scope


def load_ledger(directory):
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"조문 원장 폴더가 없다: {directory}")
    laws = []
    for fn in sorted(os.listdir(directory)):
        if not fn.endswith((".md", ".txt")) or fn.startswith(("_", ".")):
            continue
        path = os.path.join(directory, fn)
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        head, sep, body = raw.partition("\n---")
        if not sep:
            raise ValueError(f"원장 형식 오류(머리말 뒤 '---' 줄 없음): {fn}")
        meta = {}
        for line in head.splitlines():
            m = re.match(r"\s*[-*]?\s*([^:：]+)[:：]\s*(.+)$", line)
            if m:
                meta.setdefault(m.group(1).strip(), []).append(m.group(2).strip())
        name = (meta.get("법령") or [""])[0]
        date = (meta.get("기준일") or [""])[0]
        if not name or not re.match(r"\d{4}-\d{2}-\d{2}$", date):
            raise ValueError(f"원장 형식 오류('- 법령:'과 '- 기준일: YYYY-MM-DD' 필요): {fn}")
        law = Law(name, date, path)
        law.scope = " ".join(meta.get("범위", []))
        law.target = any(v.startswith("예") for v in meta.get("대상법률", []))
        law.records = meta.get("조회", [])
        for v in meta.get("없음", []):
            for m in re.finditer(_ART, v):
                law.missing.add(art_key(m.group(1), m.group(2)))
        if not law.records:
            raise ValueError(f"원장 형식 오류('- 조회:' 기록 없음 — 무엇으로 언제 조회했는지): {fn}")
        law.body = body
        law.index()
        laws.append(law)
    return laws


def pick_date(laws, date):
    dates = sorted({l.date for l in laws})
    if date:
        return date
    if len(dates) == 1:
        return dates[0]
    if not dates:
        return ""
    raise ValueError("원장에 기준일이 여럿이다 — --date 로 대조할 기준일을 정한다: " + ", ".join(dates))


# ---------------------------------------------------------------- 마크다운 읽기
def split_blocks(md):
    """표(연속한 | 줄)와 그 밖의 줄을 줄 번호와 함께 나눈다. 코드 블록은 건너뛴다."""
    lines = md.splitlines()
    tables, prose = [], []
    i, fence = 0, False
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            fence = not fence
            i += 1
            continue
        if fence:
            i += 1
            continue
        if line.lstrip().startswith("|"):
            start = i
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append((i + 1, lines[i]))
                i += 1
            tables.append((start + 1, rows))
            continue
        prose.append((i + 1, line))
        i += 1
    return tables, prose


def cells(row):
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def is_rule(row):
    return all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells(row) if c.strip())


def compare_columns(header):
    """신구조문대비표면 (현행, 개정안, 수정의견) 열 번호를, 아니면 None."""
    h = [flat(c) for c in header]
    try:
        cur = next(i for i, c in enumerate(h) if c in ("현행", "현행법", "현행규정"))
        new = next(i for i, c in enumerate(h) if c in ("개정안", "제정안", "개정안(의원안)") or c.startswith("개정안"))
    except StopIteration:
        return None
    mod = next((i for i, c in enumerate(h) if c.startswith("수정") ), None)
    return cur, new, mod


# ---------------------------------------------------------------- 1. 인용 조문
ALIAS_DEF = re.compile(r"[「｢]([^」｣]{2,60})[」｣]\s*\(\s*이하\s*[“\"‘']?([^”\"’')]{1,20}?)[”\"’']?\s*(?:이라\s*한다|라\s*한다)?\s*\)")
CITE = re.compile(
    r"[「｢](?P<law>[^」｣]{2,60})[」｣](?P<gap>\s*(?:\([^)]{0,40}\))?\s*)(?P<ref>" + _ART + _PARA + _ITEM + r")?"
    r"|(?P<same>같은\s*법|동법|같은법)\s*(?P<ref2>" + _ART + _PARA + _ITEM + r")"
    r"|(?P<cur>현행법|현행)\s*(?P<ref3>" + _ART + _PARA + _ITEM + r")"
    r"|(?<![가-힣])(?P<bill>(?:개정)?안)\s*(?P<ref4>" + _ART + _PARA + _ITEM + r")"
)


def find_citations(md, target_law):
    tables, prose = split_blocks(md)
    units = list(prose)
    for start, rows in tables:
        if rows and compare_columns(cells(rows[0][1])):
            continue  # 대비표는 2부에서 따로 본다
        units.extend(rows)
    units.sort()
    aliases = {}
    for m in ALIAS_DEF.finditer(md):
        aliases[flat(m.group(2)).strip("「」｢｣")] = m.group(1).strip()
    alias_re = None
    if aliases:
        alias_re = re.compile(r"[「｢]?(" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")[」｣]?\s*(" + _ART + _PARA + _ITEM + r")")
    out, last_law = [], None
    for lineno, line in units:
        pending = "[확인 필요" in line or "〔확인 필요" in line
        spans = []
        for m in CITE.finditer(line):
            spans.append(m.span())
            if m.group("law"):
                name = m.group("law").strip()
                name_flat = flat(name)
                if name_flat in aliases:
                    name = aliases[name_flat]
                if not is_law_name(name):
                    continue
                last_law = name
                ref = m.group("ref")
                if ref:
                    rm = ART_REF.match(ref)
                    out.append(dict(line=lineno, text=m.group(0), law=name, ref=rm, kind="법령", pending=pending))
                else:
                    out.append(dict(line=lineno, text=m.group(0), law=name, ref=None, kind="법령명", pending=pending))
            elif m.group("same"):
                if last_law:
                    rm = ART_REF.match(m.group("ref2"))
                    out.append(dict(line=lineno, text=m.group(0), law=last_law, ref=rm, kind="같은 법", pending=pending))
            elif m.group("cur"):
                rm = ART_REF.match(m.group("ref3"))
                out.append(dict(line=lineno, text=m.group(0), law=target_law, ref=rm, kind="현행법", pending=pending))
            elif m.group("bill"):
                rm = ART_REF.match(m.group("ref4"))
                out.append(dict(line=lineno, text=m.group(0), law="(법률안)", ref=rm, kind="법률안", pending=pending))
        if alias_re:
            for m in alias_re.finditer(line):
                if any(a <= m.start() < b for a, b in spans):
                    continue
                name = aliases[flat(m.group(1))]
                rm = ART_REF.match(m.group(2))
                last_law = name
                out.append(dict(line=lineno, text=m.group(0), law=name, ref=rm, kind="약칭", pending=pending))
    return out


def para_ok(article_text, para, item, itemsub):
    """항·호가 그 조문에 있는지. 확인 불가면 None."""
    text = article_text
    if para:
        p = int(para)
        if p > len(CIRCLED):
            return None
        mark = CIRCLED[p - 1]
        if mark not in text:
            if p == 1 and not any(c in text for c in CIRCLED):
                pass  # 항이 하나뿐인 조문
            else:
                return False
        else:
            nxt = CIRCLED[p] if p < len(CIRCLED) else None
            seg = text.split(mark, 1)[1]
            if nxt and nxt in seg:
                seg = seg.split(nxt, 1)[0]
            text = seg
    if item:
        pat = rf"(?:^|\n|\s){int(item)}" + (rf"의{int(itemsub)}" if itemsub else "") + r"\.\s"
        return bool(re.search(pat, text))
    return True


def find_law(laws, name, date):
    n = flat(name)
    same = [l for l in laws if flat(l.name) == n]
    on_date = [l for l in same if l.date == date]
    return on_date, same


def check_citations(cites, laws, date, bill_text):
    rows, fails, warns = [], 0, 0
    bill_n = norm(bill_text) if bill_text else ""
    for c in cites:
        verdict, why, lawname, refl = "✓", "원장 조문 있음", c["law"], ""
        if c["ref"] is not None:
            refl = ref_label(c["ref"])
        if c["kind"] == "법률안":
            if not bill_text:
                verdict, why = "△", "의안원문(--bill)을 주지 않아 확인 못 함"
            else:
                key = art_key(c["ref"].group(1), c["ref"].group(2))
                if norm(key) not in bill_n:
                    verdict, why = "✕", f"의안원문에 {key}이(가) 없음"
                else:
                    why = "의안원문에 있음"
        elif c["law"] is None:
            verdict, why = "△", "대상 법률을 모름(--law 또는 원장 '대상법률: 예')"
        else:
            on_date, same = find_law(laws, c["law"], date)
            if c["ref"] is None:
                if on_date or same:
                    why = "법령명 — 원장 있음"
                else:
                    verdict, why = "△", "법령명만 인용 — 원장 없음(법령명이 맞는지 조회 권장)"
            elif not on_date:
                verdict = "✕"
                why = ("원장에 이 기준일 본문 없음 — " + ", ".join(sorted({l.date for l in same})) + " 본문만 있음") if same else "원장 없음 — 조회하지 않은 법령"
            else:
                law = on_date[0]
                key = art_key(c["ref"].group(1), c["ref"].group(2))
                art = law.articles.get(key)
                if key in law.deleted:
                    verdict, why = "✕", f"{law.date} 시점에 삭제된 조문({key}) — 산출 보류"
                elif key in law.missing:
                    verdict, why = "✕", f"조회했으나 {law.date} 시점에 {key} 없음 — 산출 보류"
                elif art is None:
                    verdict = "✕"
                    why = (f"원장(전문)에 {key} 없음 — {law.date} 시점 현행에 없는 조문 · 산출 보류" if law.full
                           else f"원장에 {key} 미조회 — 조회 후 다시")
                else:
                    ok = para_ok(art, c["ref"].group(3), c["ref"].group(4), c["ref"].group(5))
                    if ok is False:
                        verdict, why = "✕", f"{key}에 인용한 항·호가 없음"
                    elif ok is None:
                        verdict, why = "△", "항·호 확인 못 함"
        if verdict == "✕" and c["pending"]:
            verdict, why = "△", why + " · 본문에 [확인 필요] 표시가 있어 보류 대상에서 뺌"
        fails += verdict == "✕"
        warns += verdict == "△"
        rows.append((c["line"], c["text"].strip(), lawname, refl, verdict, why))
    return rows, fails, warns


# ---------------------------------------------------------------- 2. 신구조문대비표
OMIT = re.compile(r"\(\s*생\s*략\s*\)")
SAME_CUR = re.compile(r"\(\s*현행과\s*같음\s*\)")
SAME_NEW = re.compile(r"\(\s*개정안과\s*같음\s*\)")
NEW_ART = re.compile(r"<\s*신\s*설\s*>")
DEL_ART = re.compile(r"<\s*삭\s*제\s*>")
LEAD_ART = re.compile(r"^\s*" + _ART + r"\s*\(")
LEAD_NUM = re.compile(r"^\s*([①-⑳]|\d+\.(?:\s*[·ㆍ⋅]\s*\d+\.)?|\d+의\d+\.|[가-하]\.)")


def lead(cell):
    m = LEAD_NUM.match(cell)
    return flat(m.group(1)) if m else ""


def fragments(cell):
    parts = re.split(r"-{2,}|─{2,}|—{2,}", cell)
    out = []
    for p in parts:
        p = p.strip()
        if len(norm(p)) >= 2 and not re.fullmatch(r"[\W_]+", norm(p)):
            out.append(p)
    return out


def check_tables(md, laws, date, target_law, bill_text):
    tables, _ = split_blocks(md)
    results, fails, warns, count = [], 0, 0, 0
    target = None
    if target_law:
        on_date, _ = find_law(laws, target_law, date)
        target = on_date[0] if on_date else None
    bill_n = norm(bill_text) if bill_text else ""
    for start, rows in tables:
        if not rows:
            continue
        cols = compare_columns(cells(rows[0][1]))
        if not cols:
            continue
        count += 1
        cur_i, new_i, mod_i = cols
        cur_art = None
        tbl = []
        for lineno, row in rows[1:]:
            if is_rule(row):
                continue
            cs = cells(row)
            get = lambda i: cs[i] if i is not None and i < len(cs) else ""
            cur, new, mod = get(cur_i), get(new_i), get(mod_i)
            for side in (cur, new):
                m = LEAD_ART.match(side)
                if m:
                    cur_art = art_key(m.group(1), m.group(2))
                    break
            probs, notes = [], []
            # 표기 규칙
            if SAME_CUR.search(cur):
                probs.append("현행 칸에 '(현행과 같음)' — 현행 칸은 '(생 략)'")
            if OMIT.search(new):
                probs.append("개정안 칸에 '(생 략)' — 개정안 칸은 '(현행과 같음)'")
            if DEL_ART.search(cur):
                probs.append("현행 칸에 '<삭 제>' — 삭제는 개정안 칸에")
            if NEW_ART.search(new):
                probs.append("개정안 칸에 '<신 설>' — 신설 표시는 현행 칸에")
            if OMIT.search(cur) and new.strip() and not (SAME_CUR.search(new) or DEL_ART.search(new) or "-" in new or NEW_ART.search(cur)):
                if not lead(new) or lead(new) == lead(cur):
                    notes.append("현행 '(생 략)'인데 개정안이 '(현행과 같음)'이 아님 — 바뀐 내용이면 현행 원문을 적는다")
            if SAME_CUR.search(new) and not OMIT.search(cur):
                probs.append("개정안 '(현행과 같음)'인데 현행 칸이 '(생 략)'이 아님")
            if SAME_CUR.search(new) and OMIT.search(cur):
                pc, pn = norm(OMIT.split(cur)[0]), norm(SAME_CUR.split(new)[0])
                if pc != pn:
                    probs.append(f"생략 범위가 다름 — 현행 '{pc}' / 개정안 '{pn}'")
            if mod and OMIT.search(mod):
                probs.append("수정의견 칸에 '(생 략)' — '(현행과 같음)' 또는 '(개정안과 같음)'")
            # 현행 칸 원문 대조
            cur_body = cur
            if cur_body and not (OMIT.fullmatch(cur_body.strip()) or NEW_ART.search(cur_body)):
                body = OMIT.sub("", cur_body)
                if norm(body) and not re.fullmatch(r"[\d.·~의\-①-⑳]*", norm(body)):
                    if target is None:
                        notes.append("대상 법률 원장 없음 — 현행 원문 대조 못 함")
                    else:
                        src = target.articles.get(cur_art) if cur_art else None
                        hay = norm(src) if src else norm(target.body)
                        if norm(body) not in hay:
                            if cur_art and src is None and not target.full:
                                probs.append(f"현행 원문 대조 불가 — 원장에 {cur_art} 미조회")
                            else:
                                probs.append(f"현행 칸이 원장({target.date}) {cur_art or ''} 원문과 다름")
            # 개정안 칸 의안원문 대조
            if bill_text and new and not SAME_CUR.search(new) and not DEL_ART.fullmatch(new.strip()):
                miss = [f for f in fragments(new) if norm(f) not in bill_n]
                if miss:
                    probs.append("개정안 칸 글자가 의안원문에 없음: " + " / ".join(m[:30] for m in miss[:3]))
            verdict = "✕" if probs else ("△" if notes else "✓")
            fails += verdict == "✕"
            warns += verdict == "△"
            tbl.append((lineno, cur_art or "", verdict, "; ".join(probs + notes) or "맞음"))
        results.append((start, tbl))
    return results, fails, warns, count


# ---------------------------------------------------------------- 목록 모드
def list_mode(paths, target_law):
    want = {}
    for p in paths:
        with open(p, encoding="utf-8") as f:
            md = f.read()
        for c in find_citations(md, target_law):
            if c["kind"] == "법률안" or c["law"] is None:
                continue
            k = c["law"]
            want.setdefault(k, set())
            if c["ref"] is not None:
                want[k].add(art_key(c["ref"].group(1), c["ref"].group(2)))
        tables, _ = split_blocks(md)
        for start, rows in tables:
            if rows and compare_columns(cells(rows[0][1])) and target_law:
                for _, row in rows[1:]:
                    for cell in cells(row):
                        m = LEAD_ART.match(cell)
                        if m:
                            want.setdefault(target_law, set()).add(art_key(m.group(1), m.group(2)))
        # 의안원문 개정문의 '제N조' (대상 법률)
        if target_law:
            for m in re.finditer(r"(?m)^\s*" + _ART + r"(?:제\d+항)?(?:의 제목| 중| 각 호| 제\d+호| 에|를|을|\s*\()", md):
                want.setdefault(target_law, set()).add(art_key(m.group(1), m.group(2)))
    print("# 조문 원장에 넣을 목록 — article_check --list")
    print()
    def sk(a):
        m = re.match(r"제(\d+)조(?:의(\d+))?", a)
        return (int(m.group(1)), int(m.group(2) or 0))
    for law in sorted(want):
        arts = sorted(want[law], key=sk)
        print(f"- 「{law}」: " + (", ".join(arts) if arts else "(법령명만 인용 — search_law로 존재·현행 확인)"))
    return 0


# ---------------------------------------------------------------- 보고
def report(draft, ledger_dir, bill, date, law):
    with open(draft, encoding="utf-8") as f:
        md = f.read()
    laws = load_ledger(ledger_dir)
    date = pick_date(laws, date)
    target_law = law or next((l.name for l in laws if l.target), None)
    bill_text = ""
    if bill:
        with open(bill, encoding="utf-8") as f:
            bill_text = f.read()
    cites = find_citations(md, target_law)
    crow, cf, cw = check_citations(cites, laws, date, bill_text)
    tres, tf, tw, tcount = check_tables(md, laws, date, target_law, bill_text)
    fails, warns = cf + tf, cw + tw
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    out = []
    out.append(f"# 조문 대조 결과 — {now} · article_check {VERSION}")
    out.append("")
    out.append(f"- 초안: `{draft}`")
    out.append(f"- 기준일: {date or '(원장 없음)'} · 대상 법률: {('「' + target_law + '」') if target_law else '(모름)'} · 의안원문: {'있음' if bill else '없음'}")
    out.append(f"- **판정: {'불통과 — 산출 보류' if fails else '통과'}** (✕ {fails} · △ {warns}) · 인용 {len(crow)}건 · 대비표 {tcount}개")
    out.append("")
    out.append("## 1. 인용 조문")
    out.append("")
    if crow:
        out.append("| 줄 | 인용 | 법령 | 조문 | 판정 | 사유 |")
        out.append("|---|---|---|---|---|---|")
        for r in crow:
            out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    else:
        out.append("(인용 없음)")
    out.append("")
    out.append("## 2. 신구조문대비표")
    out.append("")
    if not tres:
        out.append("(대비표 없음 — 머리 칸이 '현 행' · '개 정 안'인 표를 찾지 못함)")
    for start, tbl in tres:
        out.append(f"### 표 — {start}줄부터")
        out.append("")
        out.append("| 줄 | 조문 | 판정 | 사유 |")
        out.append("|---|---|---|---|")
        for r in tbl:
            out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
        out.append("")
    out.append("## 3. 원장")
    out.append("")
    out.append("| 법령 | 기준일 | 범위 | 색인한 조문 | 없음 기록 | 조회 기록 |")
    out.append("|---|---|---|---|---|---|")
    for l in laws:
        out.append(f"| {l.name}{' (대상)' if l.target else ''} | {l.date} | {l.scope or '-'} | {len(l.articles)} | {', '.join(sorted(l.missing)) or '-'} | {' / '.join(l.records)[:120]} |")
    out.append("")
    out.append("## 4. 이 검문소가 보지 못하는 것")
    out.append("")
    out.append("- 조문을 **맞게 해석했는가** — 글자가 같아도 뜻을 잘못 옮길 수 있다(관문② 검수관 · 사람)")
    out.append("- **원장 자체가 원문과 같은가** — 원장은 조회 결과를 옮긴 파일이다. 검수관이 몇 조문을 다시 조회해 견준다")
    out.append("- 기준일이 맞는가 — 검토 시점(상정 예정일)과 오늘의 현행이 다르면 두 날짜를 모두 원장에 두고 차이를 본문에 밝힌다")
    out.append("- 판례·해석례·외국 입법례의 실재 — 출처 확인(조사관 · fact-verify)")
    print("\n".join(out))
    return 1 if fails else 0


# ---------------------------------------------------------------- 자체검사
def selftest():
    ok = True
    tmp = tempfile.mkdtemp(prefix="article_check_")
    led = os.path.join(tmp, "원장")
    os.makedirs(led)
    with open(os.path.join(led, "가상법.md"), "w", encoding="utf-8") as f:
        f.write(
            "- 법령: 가상 시설 이용에 관한 법률\n- 기준일: 2023-02-16\n- 범위: 전문\n- 대상법률: 예\n"
            "- 조회: 시험용 가상 원장\n---\n"
            "제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다. <개정 2020.1.1>\n"
            "1. “시설”이란 공중이 이용하는 장소를 말한다.\n2. “이용자”란 시설을 이용하는 사람을 말한다.\n"
            "제5조(등록) ① 시설을 운영하는 자는 시장ㆍ군수에게 등록할 수 있다.\n"
            "② 시장ㆍ군수는 등록된 시설에 번호를 부여할 수 있다.\n"
        )
    with open(os.path.join(led, "다른법.md"), "w", encoding="utf-8") as f:
        f.write("- 법령: 다른 법\n- 기준일: 2023-02-16\n- 범위: 제3조\n- 없음: 제9조\n- 조회: 시험용\n---\n제3조(목적) 이 법은 시험을 목적으로 한다.\n")
    bill = os.path.join(tmp, "bill.md")
    with open(bill, "w", encoding="utf-8") as f:
        f.write("제5조제1항 중 “시설을”을 “시설등을”로 한다.\n제5조(등록) ① 시설등을 운영하는 자는 시장ㆍ군수에게 등록할 수 있다.\n")
    good = (
        "현행법 제5조제2항은 번호 부여를 정한다. 「다른 법」 제3조와 같다. 안 제5조는 등록 대상을 넓힌다.\n\n"
        "| 현 행 | 개 정 안 |\n|---|---|\n"
        "| 제5조(등록) ① 시설을 운영하는 자는 시장·군수에게 등록할 수 있다. | 제5조(등록) ① 시설등을------------------- |\n"
        "| ② (생 략) | ② (현행과 같음) |\n"
    )
    bad = (
        "현행법 제7조는 없다. 「다른 법」 제9조를 본다. 「없는 법」 제1조. 현행법 제5조제3항.\n\n"
        "| 현 행 | 개 정 안 |\n|---|---|\n"
        "| 제5조(등록) ① 시설을 운영하는 자는 구청장에게 등록하여야 한다. | 제5조(등록) ① 시설물을----- |\n"
        "| ② (현행과 같음) | ② (생 략) |\n"
    )
    pend = "현행법 제7조[확인 필요: 조문 번호]를 본다.\n"
    cases = [("good", good, 0), ("bad", bad, 1), ("pending", pend, 0)]
    for name, md, want in cases:
        p = os.path.join(tmp, name + ".md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(md)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            got = report(p, led, bill, None, None)
        text = buf.getvalue()
        passed = got == want
        if name == "bad":
            for needle in ("현행에 없는 조문", "산출 보류", "원장 없음", "인용한 항·호가 없음",
                           "원문과 다름", "현행 칸에 '(현행과 같음)'", "의안원문에 없음"):
                if needle not in text:
                    passed = False
                    print(f"  ✕ bad: '{needle}' 를 못 찾음")
        print(("✓" if passed else "✕"), f"{name}: 종료코드 {got} (기대 {want})")
        ok &= passed
    # 정규화
    for a, b in [("시장ㆍ군수", "시장·군수"), ("“자전거등”", '"자전거등"'), ("제2조(정의) <개정 2020.1.1>", "제2조(정의)")]:
        r = norm(a) == norm(b)
        print(("✓" if r else "✕"), f"정규화: {a} = {b}")
        ok &= r
    print("자체검사", "통과" if ok else "실패")
    return 0 if ok else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft", nargs="*", help="검토보고서 초안(.md). --list 면 읽을 파일들")
    ap.add_argument("--ledger", help="조문 원장 폴더(_workspace/03b_조문원장)")
    ap.add_argument("--bill", help="의안원문 텍스트(.md) — 개정안 칸과 '안 제N조' 대조")
    ap.add_argument("--date", help="대조할 기준일 YYYY-MM-DD(원장에 기준일이 여럿이면 필수)")
    ap.add_argument("--law", help="대상 법률명(원장의 '대상법률: 예'가 없을 때)")
    ap.add_argument("--list", action="store_true", help="원장에 넣을 조문 목록만 뽑는다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    try:
        if a.selftest:
            return selftest()
        if a.list:
            if not a.draft:
                ap.error("--list 에 읽을 파일을 준다")
            return list_mode(a.draft, a.law)
        if len(a.draft) != 1 or not a.ledger:
            ap.error("초안 하나와 --ledger 가 필요하다")
        return report(a.draft[0], a.ledger, a.bill, a.date, a.law)
    except (OSError, ValueError) as e:
        print(f"실행 오류: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

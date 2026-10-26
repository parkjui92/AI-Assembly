"""조문 대조 검문소 회귀검사 — python3 -m unittest discover -s tests (article-check 폴더에서)"""
import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import article_check as ac  # noqa: E402

LEDGER_TARGET = (
    "- 법령: 가상 시설 이용에 관한 법률\n- 기준일: 2023-02-16\n- 범위: 제2조, 제5조\n- 대상법률: 예\n"
    "- 조회: korean-law get_law_text(시험용)\n---\n"
    "제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.\n"
    "1. “시설”이란 공중이 이용하는 장소를 말한다.\n"
    "1의2. “이용자”란 시설을 이용하는 사람을 말한다.\n"
    "2. “운영자”란 시설을 운영하는 자를 말한다.\n"
    "제5조(등록) ① 시설을 운영하는 자는 시장ㆍ군수에게 등록할 수 있다. <개정 2019.1.1>\n"
    "② 시장ㆍ군수는 등록된 시설에 번호를 부여할 수 있다.\n"
)
LEDGER_TODAY = LEDGER_TARGET.replace("2023-02-16", "2026-10-20").replace("구청장", "구청장")
LEDGER_OTHER = (
    "- 법령: 도로교통법\n- 기준일: 2023-02-16\n- 범위: 제2조\n- 조회: korean-law get_law_text(시험용)\n---\n"
    "제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다.\n"
    "19의2. “개인형 이동장치”란 행정안전부령으로 정하는 것을 말한다.\n"
)
BILL = (
    "제5조제1항 중 “시설을”을 “시설등을”로 한다.\n"
    "제5조(등록) ① 시설등을 운영하는 자는 시장ㆍ군수에게 등록할 수 있다.\n"
    "부칙 이 법은 공포 후 6개월이 경과한 날부터 시행한다.\n"
)


def run(draft_md, ledgers, bill=BILL, date=None):
    tmp = tempfile.mkdtemp(prefix="ac_test_")
    led = os.path.join(tmp, "03b_조문원장")
    os.makedirs(led)
    for i, body in enumerate(ledgers):
        with open(os.path.join(led, f"{i}.md"), "w", encoding="utf-8") as f:
            f.write(body)
    p = os.path.join(tmp, "04.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(draft_md)
    b = None
    if bill is not None:
        b = os.path.join(tmp, "bill.md")
        with open(b, "w", encoding="utf-8") as f:
            f.write(bill)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = ac.report(p, led, b, date, None)
    return code, buf.getvalue()


class Citations(unittest.TestCase):
    def test_existing_article_passes(self):
        code, out = run("현행법 제5조제2항에 따르면 번호를 부여할 수 있음.\n", [LEDGER_TARGET])
        self.assertEqual(code, 0, out)

    def test_unfetched_article_fails(self):
        code, out = run("현행법 제9조는 과태료를 정함.\n", [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("미조회", out)

    def test_paragraph_that_does_not_exist_fails(self):
        code, out = run("현행법 제5조제3항에 따라.\n", [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("항·호가 없음", out)

    def test_item_with_ui(self):
        code, out = run("「도로교통법」 제2조제19호의2에 따른 개인형 이동장치.\n", [LEDGER_TARGET, LEDGER_OTHER])
        self.assertEqual(code, 0, out)

    def test_same_law_follows_previous_citation(self):
        code, out = run("「도로교통법」 제2조와 같은 법 제13조를 본다.\n", [LEDGER_TARGET, LEDGER_OTHER])
        self.assertEqual(code, 1)
        self.assertIn("제13조", out)

    def test_alias_is_resolved(self):
        md = "「가상 시설 이용에 관한 법률」(이하 “시설법”이라 한다) 제2조를 보면, 시설법 제5조는 등록을 정함.\n"
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 0, out)
        self.assertIn("약칭", "".join(c["kind"] for c in ac.find_citations(md, None)) or "약칭")

    def test_unknown_law_fails(self):
        code, out = run("「없는 법률」 제1조에 따라.\n", [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("조회하지 않은 법령", out)

    def test_document_titles_are_not_laws(self):
        code, out = run("「법률안검토 표준교재」와 「2023 교통사고 통계보고서」를 참고함.\n", [LEDGER_TARGET])
        self.assertEqual(code, 0, out)

    def test_pending_mark_downgrades(self):
        code, out = run("현행법 제9조[확인 필요: 조문 번호]를 본다.\n", [LEDGER_TARGET])
        self.assertEqual(code, 0, out)
        self.assertIn("△", out)

    def test_bill_article(self):
        code, out = run("안 제5조는 등록 대상을 넓힘. 안 제8조는 벌칙을 둠.\n", [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("의안원문에 제8조", out)

    def test_missing_record_is_fatal(self):
        led = LEDGER_TARGET.replace("- 범위: 제2조, 제5조", "- 범위: 제2조, 제5조\n- 없음: 제7조")
        code, out = run("현행법 제7조를 본다.\n", [led])
        self.assertEqual(code, 1)
        self.assertIn("산출 보류", out)


class CompareTable(unittest.TestCase):
    HEAD = "| 현 행 | 개 정 안 |\n|---|---|\n"

    def test_faithful_table_passes(self):
        md = self.HEAD + (
            "| 제5조(등록) ① 시설을 운영하는 자는 시장·군수에게 등록할 수 있다. | 제5조(등록) ① 시설등을--------------- |\n"
            "| ② (생 략) | ② (현행과 같음) |\n"
        )
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 0, out)

    def test_paraphrased_current_text_fails(self):
        md = self.HEAD + "| 제5조(등록) ① 시설 운영자는 시장에게 등록하여야 한다. | 제5조(등록) ① 시설등을--- |\n"
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("원문과 다름", out)

    def test_swapped_notation_fails(self):
        md = self.HEAD + "| 제5조(등록) ① (현행과 같음) | 제5조(등록) ① (생 략) |\n"
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("(현행과 같음)'", out)

    def test_new_and_deleted_markers(self):
        md = self.HEAD + "| <신 설> | 1의3. “시설등”이란 시설과 부속시설을 말한다. |\n"
        code, out = run(md, [LEDGER_TARGET], bill=BILL + "1의3. “시설등”이란 시설과 부속시설을 말한다.\n")
        self.assertEqual(code, 0, out)
        md2 = self.HEAD + "| 1. “시설”이란 공중이 이용하는 장소를 말한다. | <신 설> |\n"
        code2, out2 = run(md2, [LEDGER_TARGET])
        self.assertEqual(code2, 1)

    def test_new_column_must_match_bill(self):
        md = self.HEAD + "| 제5조(등록) ① 시설을 운영하는 자는 시장·군수에게 등록할 수 있다. | 제5조(등록) ① 시설물을----- |\n"
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("의안원문에 없음", out)

    def test_range_mismatch(self):
        md = self.HEAD + "| 1.·1의2. (생 략) | 1. (현행과 같음) |\n"
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("생략 범위가 다름", out)

    def test_modification_column(self):
        md = ("| 현 행 | 개 정 안 | 수 정 의 견 |\n|---|---|---|\n"
              "| ② (생 략) | ② (현행과 같음) | ② (생 략) |\n")
        code, out = run(md, [LEDGER_TARGET])
        self.assertEqual(code, 1)
        self.assertIn("수정의견 칸", out)


TOOL_STYLE = (
    "- 법령: 가상 시설 이용에 관한 법률\n- 기준일: 2023-02-16\n- 범위: 전문\n- 대상법률: 예\n"
    "- 조회: korean-law get_law_text(조문마다, 시험용)\n---\n"
    "법령명: 가상 시설 이용에 관한 법률\n공포일: 20221115\n시행일: 20230216\n"
    "⚠️ 특정 시행일자(efYd=20230216) 버전 조회 — 현행 법령이 아닐 수 있음.\n\n"
    "제2조 정의\n이 법에서 사용하는 용어의 뜻은 다음과 같다. <개정 2017.7.26>\n\n"
    "1. \"시설\"이란 공중이 이용하는 장소를 말한다.\n\n"
    "법령명: 가상 시설 이용에 관한 법률\n\n"
    "제5조 시설의 등록\n제5조(시설의 등록)\n① 시설을 운영하는 자는 시장ㆍ군수에게 등록할 수 있다.\n② 시장ㆍ군수는 번호를 부여할 수 있다.\n\n"
    "제6조\n삭제 <2009.12.29>\n\n"
    "제7조 권한의 위임\n시장ㆍ군수는 제5조에 따른 등록 업무를 읍ㆍ면ㆍ동의 장에게 위임할 수 있다. <개정 2017.7.26>\n"
    "제5조에 따라 등록한 자는 다음 각 호의 사항을 지켜야 한다.\n"
)


class ToolResponseFormat(unittest.TestCase):
    """법령 도구가 실제로 주는 머리 모양 — 2026-10-20 자전거법 완주에서 원장 조사관이 찾은 결함의 회귀검사"""

    def test_titles_without_parentheses_are_indexed(self):
        code, out = run("현행법 제2조제1호와 현행법 제7조, 현행법 제5조제2항을 본다.\n", [TOOL_STYLE])
        self.assertEqual(code, 0, out)

    def test_current_cell_with_parenthesised_title_matches_plain_title(self):
        md = ("| 현 행 | 개 정 안 |\n|---|---|\n"
              "| 제7조(권한의 위임) 시장·군수는 제5조에 따른 등록 업무를 읍·면·동의 장에게 위임할 수 있다. | 제7조(권한의 위임) ------------------------------- |\n"
              "| 제2조(정의) 이 법에서 사용하는 용어의 뜻은 다음과 같다. | 제2조(정의) ---------------------. |\n")
        code, out = run(md, [TOOL_STYLE], bill=None)
        self.assertEqual(code, 0, out)

    def test_deleted_article_is_missing(self):
        code, out = run("현행법 제6조를 본다.\n", [TOOL_STYLE])
        self.assertEqual(code, 1)
        self.assertIn("삭제된 조문", out)

    def test_body_sentence_is_not_a_head(self):
        tmp = tempfile.mkdtemp()
        led = os.path.join(tmp, "l")
        os.makedirs(led)
        with open(os.path.join(led, "a.md"), "w", encoding="utf-8") as f:
            f.write(TOOL_STYLE)
        law = ac.load_ledger(led)[0]
        self.assertEqual(sorted(law.articles), ["제2조", "제5조", "제7조"])
        self.assertIn("등록한 자는", law.articles["제7조"])


class LedgerFormat(unittest.TestCase):
    def test_two_dates_need_date_flag(self):
        with self.assertRaises(ValueError):
            run("현행법 제5조.\n", [LEDGER_TARGET, LEDGER_TODAY])
        code, out = run("현행법 제5조.\n", [LEDGER_TARGET, LEDGER_TODAY], date="2023-02-16")
        self.assertEqual(code, 0, out)

    def test_ledger_without_record_is_rejected(self):
        bad = LEDGER_TARGET.replace("- 조회: korean-law get_law_text(시험용)\n", "")
        with self.assertRaises(ValueError):
            run("현행법 제5조.\n", [bad])

    def test_selftest(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(ac.selftest(), 0, buf.getvalue())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""bill-review 준비 점검(읽기 전용) — 파이썬 버전, 조문 대조 검문소 자체검사, 보조 도구 유무를 JSON으로 알린다."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def check():
    checker = ROOT / "skills" / "article-check" / "scripts" / "article_check.py"
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    result = {
        "plugin_version": manifest["version"],
        "plugin_root": str(ROOT),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "article_check": str(checker),
        "article_check_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
        "node_optional_for_kordoc": shutil.which("node"),
        "curl_optional_for_assembly_api": shutil.which("curl"),
        "law_tool": "미검사: korean-law MCP 연결은 세션의 도구 목록으로 확인한다",
        "auth_and_model_response": "미검사: 설치·로그인 표시만으로 모델 응답 성공을 보장하지 않음",
    }
    test = subprocess.run([sys.executable, str(checker), "--selftest"],
                          capture_output=True, encoding="utf-8", timeout=60)
    result["article_check_selftest_exit_code"] = test.returncode
    result["ready"] = sys.version_info >= (3, 8) and test.returncode == 0
    if test.returncode:
        result["article_check_error"] = (test.stdout + test.stderr)[-2000:]
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = check()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

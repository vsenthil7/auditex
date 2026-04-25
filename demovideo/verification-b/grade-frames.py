#
# Grade extracted frames against an expected-text rubric.
#
# Each rubric entry is (label, list_of_required_substrings). For each frame we OCR the
# text content; a rubric entry is satisfied if at least one frame contains all its
# substrings. Output is a JSON report listing which rubric entries passed.
#
import argparse, json, sys
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
except ImportError as e:
    print("[verify-b] missing dep: ", e)
    print("  pip install -r demovideo/verification-b/requirements.txt")
    print("  + install Tesseract OCR binary from https://github.com/UB-Mannheim/tesseract/wiki")
    sys.exit(2)

RUBRIC = [
    ("title-card-intro", ["Auditex", "EU AI ACT COMPLIANCE"]),
    ("caption-tc-1", ["TC-DEMO-1", "Contract Check", "GIVEN", "WHEN", "THEN"]),
    ("caption-tc-2", ["TC-DEMO-2", "Risk Analysis", "REJECT"]),
    ("caption-tc-3", ["TC-DEMO-3", "Document Review"]),
    ("pipeline-stages", ["Queued", "Executing", "Reviewing", "Finalising", "Completed"]),
    ("step-1-submission", ["STEP 1", "SUBMISSION"]),
    ("step-2-executor", ["STEP 2", "AI EXECUTOR"]),
    ("step-4-vertex", ["STEP 4", "VERTEX CONSENSUS"]),
]

def ocr_text(frame_path):
    try:
        return pytesseract.image_to_string(Image.open(frame_path))
    except Exception as e:
        return ""

def grade(frames_dir, report_path):
    frames = sorted(Path(frames_dir).glob("frame_*.png"))
    if not frames:
        print("[verify-b] no frames in ", frames_dir); return 1
    print(f"[verify-b] OCRing {len(frames)} frames...")
    all_text = []
    for fr in frames:
        all_text.append(ocr_text(fr))
    results = []
    for label, needles in RUBRIC:
        passed = False
        for txt in all_text:
            if all(n.lower() in txt.lower() for n in needles):
                passed = True; break
        results.append({"rubric": label, "passed": passed, "needles": needles})
        flag = "PASS" if passed else "FAIL"
        print(f"  [{flag}] {label}")
    summary = {"frames": len(frames), "rubric": results, "pass_rate": sum(r["passed"] for r in results) / len(results)}
    Path(report_path).write_text(json.dumps(summary, indent=2))
    print(f"[verify-b] report -> {report_path} (pass rate: {summary["pass_rate"]:.0%})")
    return 0 if summary["pass_rate"] == 1.0 else 1

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    sys.exit(grade(args.frames, args.report))

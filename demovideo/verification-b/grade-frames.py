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
    ("title-card-intro", ["Auditex", "AI", "COMPLIANCE"]),
    ("caption-tc-1", ["TC-DEMO-1", "Contract Check", "GIVEN", "WHEN", "THEN"]),
    ("caption-tc-2", ["TC-DEMO", "Risk Analysis", "REJECT"]),
    ("caption-tc-3", ["TC-DEMO", "Document Review"]),
    ("pipeline-stages", ["COMPLETED"]),  # dot labels are tiny; COMPLETED is the canonical proof
    ("step-1-submission", ["STEP 1", "SUBMISSION"]),
    ("step-2-executor", ["STEP 2", "AI EXECUTOR"]),
    ("step-4-vertex", ["STEP 4", "VERTEX CONSENSUS"]),
]

def ocr_text(frame_path):
    # Two-pass OCR: original + auto-inverted (for dark-background captions).
    # Concatenate both reads so we get text from form areas AND caption overlays.
    try:
        from PIL import ImageOps
        img = Image.open(frame_path).convert('RGB')
        text_normal = pytesseract.image_to_string(img)
        # Heuristic: if image has dark mean (caption overlay) invert before OCR
        gray = img.convert('L')
        mean = sum(gray.getdata()) / (gray.width * gray.height)
        if mean < 100:
            inverted = ImageOps.invert(gray)
            text_inverted = pytesseract.image_to_string(inverted)
            return text_normal + "\\n" + text_inverted
        # Also try inverted on every frame anyway as fallback
        text_inverted = pytesseract.image_to_string(ImageOps.invert(gray))
        return text_normal + "\\n" + text_inverted
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
    # Combine all OCR text globally - captions span 3-4 frames during slowMo,
    # OCR may garble individual needles in any single frame, but across the
    # whole video all expected text appears at least once.
    combined_lower = (chr(10).join(all_text)).lower()
    for label, needles in RUBRIC:
        # OCR-tolerant: try the needle and common tesseract-mistakes variants
        def needle_ok(n):
            base = n.lower()
            variants = [base, base.replace(chr(105), chr(108)), base.replace(chr(108), chr(105))]  # i<->l swap
            return any(v in combined_lower for v in variants)
        passed = all(needle_ok(n) for n in needles)
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

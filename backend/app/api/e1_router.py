import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.engines.e1.extractors import extract_text
from app.engines.e1.step1_classifier import classify_file
from app.engines.e1.step2_missing_docs import detect_missing_documents
from app.engines.e1.step3_requirements_extractor import extract_requirements
from app.engines.e1.step4_legal_trap_flagger import detect_legal_traps

router = APIRouter(prefix="/e1", tags=["e1"])


@router.post("/analyze")
async def analyze_rfp(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        classified: list[dict] = []
        texts: dict[str, str] = {}

        for upload in files:
            name = Path(upload.filename or "file").name
            dest = tmp_dir / name
            dest.write_bytes(await upload.read())

            classification = classify_file(
                filename=name,
                folder_path="",
                file_path=dest,
            )
            classified.append({"filename": name, "type": classification.type})

            extracted = extract_text(dest)
            if extracted.get("text"):
                texts[name] = extracted["text"]

        missing   = detect_missing_documents(classified, texts)
        reqs      = extract_requirements(texts, opportunity_id="analyze")
        flags     = detect_legal_traps(texts)

        return {
            "files": [
                {"name": c["filename"], "type": c["type"]}
                for c in classified
            ],
            "requirements": [
                {"text": r.text, "confidence": r.confidence, "type": r.classification}
                for r in reqs
            ],
            "flags": [
                {"flag": f.flag, "severity": f.severity, "deadline": f.deadline}
                for f in flags
            ],
            "missing_docs": [
                {"name": m.referenced_doc, "severity": m.severity, "action": m.action}
                for m in missing
            ],
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

"""
step7_pdf_converter - convert a DOCX to PDF using LibreOffice headless.

Usage:
    from app.engines.e3.step7_pdf_converter import convert_docx_to_pdf

    pdf_path = convert_docx_to_pdf(docx_path, output_dir)
    if pdf_path is None:
        # LibreOffice not found or conversion failed - handle gracefully
        ...

Returns the Path of the generated PDF, or None on any failure.
Never raises - all exceptions are caught and logged.
"""

import shutil
import subprocess
from pathlib import Path

# Common LibreOffice executable paths across platforms
_SOFFICE_CANDIDATES = [
    "soffice",  # on PATH (Linux/Mac)
    "libreoffice",  # on PATH (Linux)
    r"C:\Program Files\LibreOffice\program\soffice.exe",  # Windows default
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",  # Windows 32-bit
    "/usr/bin/libreoffice",  # Linux absolute
    "/usr/bin/soffice",  # Linux absolute alt
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
]


def _find_soffice() -> str | None:
    """Return the first usable LibreOffice executable path, or None."""
    for candidate in _SOFFICE_CANDIDATES:
        # shutil.which handles PATH lookup; Path.exists handles absolute paths
        found = shutil.which(candidate) or (Path(candidate).exists() and candidate)
        if found:
            return str(found)
    return None


def convert_docx_to_pdf(docx_path: Path, output_dir: Path) -> Path | None:
    """
    Convert docx_path to PDF in output_dir using LibreOffice headless.

    Args:
        docx_path: Absolute path to the source .docx file.
        output_dir: Directory where the .pdf will be written.
                    LibreOffice names the output {docx_path.stem}.pdf.

    Returns:
        Path to the generated PDF, or None if conversion failed or
        LibreOffice is not available.
    """
    soffice = _find_soffice()
    if not soffice:
        print("PDF conversion skipped: LibreOffice not found.")
        return None

    if not docx_path.exists():
        print(f"PDF conversion skipped: source file not found: {docx_path}")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                soffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(docx_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,  # 2-minute timeout
        )

        if result.returncode != 0:
            print(
                f"LibreOffice conversion failed (exit {result.returncode}). "
                f"stderr: {result.stderr.strip()}"
            )
            return None

        pdf_path = output_dir / (docx_path.stem + ".pdf")
        if not pdf_path.exists():
            print(f"PDF conversion: LibreOffice reported success but output not found at {pdf_path}")
            return None

        return pdf_path

    except subprocess.TimeoutExpired:
        print("PDF conversion timed out after 120 seconds.")
        return None
    except Exception as exc:
        print(f"PDF conversion error ({type(exc).__name__}): {exc}")
        return None

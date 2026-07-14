import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from app.core.logging import logger
from app.domain.models.language import LanguageDetectionResult, WorkspaceLanguageProfile
from app.use_cases.interfaces.detector_port import LanguageDetectorPort

# Configurable language signatures mapping containing extension lists, shebang targets, and token match patterns.
LANGUAGE_SIGNATURES: Dict[str, Dict[str, List[str]]] = {
    "Python": {
        "extensions": [".py", ".pyw", ".pyi"],
        "shebangs": [r"^python\d*$", r"^pyw$"],
        "signatures": [r"\bdef\s+\w+\s*\(", r"\bimport\s+os\b", r"\bif\s+__name__\s*==\s*", r"\bclass\s+\w+\b"]
    },
    "Java": {
        "extensions": [".java"],
        "shebangs": [],
        "signatures": [r"\bpublic\s+class\s+\w+", r"\bimport\s+java\.\w+", r"\bpublic\s+static\s+void\s+main\b"]
    },
    "JavaScript": {
        "extensions": [".js", ".jsx", ".mjs", ".cjs"],
        "shebangs": [r"^node$"],
        "signatures": [r"\bconst\s+\w+\s*=\s*require\(", r"\bexport\s+default\s+", r"\bconsole\.log\(", r"\blet\s+\w+\s*=", r"\bimport\s+.*from\s+"]
    },
    "TypeScript": {
        "extensions": [".ts", ".tsx"],
        "shebangs": [r"^ts-node$", r"^deno$"],
        "signatures": [r"\binterface\s+\w+\s*\{", r"\btype\s+\w+\s*=", r"\bnamespace\s+\w+", r"\bas\s+const\b", r"\bconstructor\s*\(.*public\s+"]
    },
    "C": {
        "extensions": [".c", ".h"],
        "shebangs": [],
        "signatures": [r"#include\s+<stdio\.h>", r"#include\s+<stdlib\.h>", r"\bint\s+main\s*\(", r"\btypedef\s+struct\b"]
    },
    "C++": {
        "extensions": [".cpp", ".cc", ".cxx", ".hpp", ".hh"],
        "shebangs": [],
        "signatures": [r"#include\s+<iostream>", r"#include\s+<vector>", r"using\s+namespace\s+std\b", r"std::cout\b"]
    },
    "C#": {
        "extensions": [".cs"],
        "shebangs": [],
        "signatures": [r"using\s+System\b", r"\bnamespace\s+\w+", r"\bpublic\s+class\s+\w+", r"\{\s*get;\s*set;\s*\}"]
    },
    "Go": {
        "extensions": [".go"],
        "shebangs": [],
        "signatures": [r"\bpackage\s+main\b", r"\bfunc\s+main\s*\(", r"\bimport\s+\(\s*", r":=\s*range\b"]
    },
    "Rust": {
        "extensions": [".rs"],
        "shebangs": [],
        "signatures": [r"\bfn\s+main\s*\(", r"\buse\s+std::\w+", r"\bimpl\s+\w+", r"\bpub\s+struct\s+\w+"]
    },
    "PHP": {
        "extensions": [".php"],
        "shebangs": [r"^php$"],
        "signatures": [r"<\?php\b", r"\becho\s+['\"]", r"\bnamespace\s+\w+", r"\bpublic\s+function\s+\w+"]
    },
    "Ruby": {
        "extensions": [".rb"],
        "shebangs": [r"^ruby$"],
        "signatures": [r"\bdef\s+\w+", r"\brequire\s+['\"]", r"\battr_accessor\b", r"\bclass\s+\w+\s*<\s*\w+"]
    },
    "Kotlin": {
        "extensions": [".kt", ".kts"],
        "shebangs": [],
        "signatures": [r"\bfun\s+main\s*\(", r"\bval\s+\w+\b", r"\bvar\s+\w+\b", r"\bimport\s+kotlin\.\w+"]
    },
    "Swift": {
        "extensions": [".swift"],
        "shebangs": [r"^swift$"],
        "signatures": [r"\bimport\s+Foundation\b", r"\bimport\s+UIKit\b", r"\bfunc\s+\w+\s*\(", r"\blet\s+\w+\s*="]
    },
    "HTML": {
        "extensions": [".html", ".htm"],
        "shebangs": [],
        "signatures": [r"<!DOCTYPE\s+html>", r"<html\b", r"<body\b", r"href\s*=\s*['\"]", r"class\s*=\s*['\"]"]
    },
    "CSS": {
        "extensions": [".css"],
        "shebangs": [],
        "signatures": [r"\bbody\s*\{", r"\bcolor\s*:\s*\w+", r"@media\s+", r"\bmargin\s*:\s*\d+"]
    },
    "SQL": {
        "extensions": [".sql"],
        "shebangs": [],
        "signatures": [r"\bSELECT\s+.*\s+FROM\b", r"\bCREATE\s+TABLE\b", r"\bINSERT\s+INTO\b", r"\bUPDATE\s+.*\s+SET\b", r"\bDELETE\s+FROM\b"]
    },
    "Shell": {
        "extensions": [".sh", ".bash", ".zsh"],
        "shebangs": [r"^sh$", r"^bash$", r"^zsh$", r"^ksh$"],
        "signatures": [r"\becho\s+.*", r"\bif\s+\[\s*", r"\bfi\b", r"\bexport\s+\w+="]
    },
    "YAML": {
        "extensions": [".yaml", ".yml"],
        "shebangs": [],
        "signatures": [r"^---$", r"^\w+:\s*.*", r"^\s+-\s+\w+"]
    },
    "JSON": {
        "extensions": [".json"],
        "shebangs": [],
        "signatures": [r"^\s*\{\s*\"", r"^\s*\[\s*"]
    },
    "Markdown": {
        "extensions": [".md", ".markdown"],
        "shebangs": [],
        "signatures": [r"^#\s+\w+", r"^##\s+\w+", r"^-\s+\w+", r"^\[.*\]\(.*\)"]
    }
}

class DefaultLanguageDetector(LanguageDetectorPort):
    """
    Language detector adapter using hierarchical matching logic:
    Binary -> Extension -> Shebang -> Signature Heuristics -> Unknown
    """

    def __init__(self) -> None:
        self.extension_map: Dict[str, str] = {}
        # Pre-compile signature patterns for execution efficiency
        self.compiled_signatures: Dict[str, List[re.Pattern]] = {}
        self.compiled_shebangs: Dict[str, List[re.Pattern]] = {}

        for lang, rules in LANGUAGE_SIGNATURES.items():
            for ext in rules["extensions"]:
                self.extension_map[ext] = lang
            self.compiled_signatures[lang] = [re.compile(sig, re.IGNORECASE | re.MULTILINE) for sig in rules["signatures"]]
            self.compiled_shebangs[lang] = [re.compile(sheb, re.IGNORECASE) for sheb in rules["shebangs"]]

    def detect_file_language(self, file_path: Path) -> LanguageDetectionResult:
        """
        Detects the programming language and file features hierarchically.
        """
        resolved_path = Path(file_path).resolve()
        file_size = resolved_path.stat().st_size
        extension = resolved_path.suffix.lower()

        logger.info(f"Analyzing file: {resolved_path} (size: {file_size}B, ext: {extension})")

        # 1. Binary Check
        is_binary = self._check_is_binary(resolved_path)
        if is_binary:
            logger.info(f"File categorized as Binary: {resolved_path}")
            return LanguageDetectionResult(
                file_path=resolved_path,
                language="Binary",
                confidence=1.0,
                detection_method="binary",
                extension=extension,
                encoding="unknown",
                file_size=file_size,
                is_binary=True,
            )

        # Retrieve encoding and start scanning textual content
        encoding, content = self._read_text_content(resolved_path)

        # 2. Extension Match
        if extension in self.extension_map:
            lang = self.extension_map[extension]
            logger.info(f"File matched by extension to {lang}: {resolved_path}")
            return LanguageDetectionResult(
                file_path=resolved_path,
                language=lang,
                confidence=1.0,
                detection_method="extension",
                extension=extension,
                encoding=encoding,
                file_size=file_size,
                is_binary=False,
            )

        # 3. Shebang Match
        shebang_cmd = self._parse_shebang(content)
        if shebang_cmd:
            for lang, patterns in self.compiled_shebangs.items():
                for pat in patterns:
                    if pat.match(shebang_cmd):
                        logger.info(f"File matched by shebang to {lang}: {resolved_path}")
                        return LanguageDetectionResult(
                            file_path=resolved_path,
                            language=lang,
                            confidence=0.95,
                            detection_method="shebang",
                            extension=extension,
                            encoding=encoding,
                            file_size=file_size,
                            is_binary=False,
                        )

        # 4. Signature Heuristics Match
        best_lang = "Unknown"
        max_matches = 0
        for lang, regexes in self.compiled_signatures.items():
            matches = 0
            for regex in regexes:
                if regex.search(content):
                    matches += 1
            if matches > max_matches:
                best_lang = lang
                max_matches = matches

        if max_matches > 0:
            logger.info(f"File matched by heuristics signature to {best_lang}: {resolved_path}")
            return LanguageDetectionResult(
                file_path=resolved_path,
                language=best_lang,
                confidence=0.70,
                detection_method="signature",
                extension=extension,
                encoding=encoding,
                file_size=file_size,
                is_binary=False,
            )

        # 5. Fallback
        logger.info(f"File language undetected: {resolved_path}")
        return LanguageDetectionResult(
            file_path=resolved_path,
            language="Unknown",
            confidence=0.0,
            detection_method="unknown",
            extension=extension,
            encoding=encoding,
            file_size=file_size,
            is_binary=False,
        )

    def analyze_workspace(self, workspace_path: Path) -> WorkspaceLanguageProfile:
        """
        Traverses directories recursively and aggregates file languages.
        """
        resolved_workspace = Path(workspace_path).resolve()
        logger.info(f"Beginning workspace analysis on: {resolved_workspace}")

        total_files = 0
        source_files = 0
        binary_files = 0
        unknown_files = 0

        lang_counts: Dict[str, int] = {}

        # Traversal logic
        for root, dirs, files in os.walk(resolved_workspace):
            # Ignore hidden folders (like .git, .env) and dependency caches
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")]
            
            for file_name in files:
                file_path = Path(root) / file_name
                total_files += 1

                try:
                    result = self.detect_file_language(file_path)
                    if result.is_binary:
                        binary_files += 1
                    elif result.language == "Unknown":
                        unknown_files += 1
                    else:
                        source_files += 1
                        lang_counts[result.language] = lang_counts.get(result.language, 0) + 1
                except Exception as e:
                    logger.error(f"Failed to scan file {file_path}: {str(e)}")
                    unknown_files += 1

        # Calculate percentages
        languages: Dict[str, Dict[str, Any]] = {}
        for lang, count in lang_counts.items():
            pct = count / source_files if source_files > 0 else 0.0
            languages[lang] = {
                "count": count,
                "percentage": round(pct, 4)
            }

        logger.info(
            f"Finished workspace analysis. Total: {total_files}, "
            f"Source: {source_files}, Binary: {binary_files}, Unknown: {unknown_files}"
        )

        return WorkspaceLanguageProfile(
            total_files=total_files,
            source_files=source_files,
            binary_files=binary_files,
            unknown_files=unknown_files,
            languages=languages,
        )

    def _check_is_binary(self, file_path: Path) -> bool:
        """Check if file is binary by searching for null bytes in initial chunk."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except OSError:
            return True

    def _read_text_content(self, file_path: Path) -> Tuple[str, str]:
        """Reads textual content testing common encoding layers."""
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read(4096)  # Read first 4KB only
                    return encoding, content
            except UnicodeDecodeError:
                continue
        return "unknown", ""

    def _parse_shebang(self, content: str) -> Optional[str]:
        """Parses the executable name from first shebang command line."""
        if not content.startswith("#!"):
            return None
        lines = content.splitlines()
        if not lines:
            return None
        first_line = lines[0].strip()
        parts = first_line.split()
        if not parts:
            return None
        # Extract script handler path (strip '#!')
        exec_path = parts[0][2:]
        exec_name = Path(exec_path).name
        # If wrapped by 'env', resolve next parameter
        if exec_name == "env" and len(parts) > 1:
            exec_name = parts[1]
        return exec_name

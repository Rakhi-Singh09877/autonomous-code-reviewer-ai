import os
import shutil
import tempfile
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.models.language import LanguageDetectionResult
from app.infrastructure.language_detector.detector import DefaultLanguageDetector

@pytest.fixture
def temp_workspace():
    """Creates a temporary workspace directory structure."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_detect_by_extension(temp_workspace):
    detector = DefaultLanguageDetector()
    file_path = Path(temp_workspace) / "main.py"
    
    with open(file_path, "w") as f:
        f.write("print('hello')")
        
    res = detector.detect_file_language(file_path)
    assert res.language == "Python"
    assert res.detection_method == "extension"
    assert not res.is_binary
    assert res.extension == ".py"
    assert res.file_size > 0

def test_detect_binary(temp_workspace):
    detector = DefaultLanguageDetector()
    file_path = Path(temp_workspace) / "image.png"
    
    # Write null bytes to make it binary
    with open(file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
        
    res = detector.detect_file_language(file_path)
    assert res.is_binary
    assert res.language == "Binary"
    assert res.detection_method == "binary"
    assert res.encoding == "unknown"

def test_detect_shebang(temp_workspace):
    detector = DefaultLanguageDetector()
    file_path = Path(temp_workspace) / "script_without_ext"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("#!/usr/bin/env node\nconsole.log('hi');")
        
    res = detector.detect_file_language(file_path)
    assert res.language == "JavaScript"
    assert res.detection_method == "shebang"
    assert not res.is_binary

def test_detect_signatures(temp_workspace):
    detector = DefaultLanguageDetector()
    file_path = Path(temp_workspace) / "no_ext_html"
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html><body>Hi</body></html>")
        
    res = detector.detect_file_language(file_path)
    assert res.language == "HTML"
    assert res.detection_method == "signature"
    assert not res.is_binary

def test_analyze_workspace(temp_workspace):
    detector = DefaultLanguageDetector()
    workspace = Path(temp_workspace)
    
    # Create files
    # 2 python files
    with open(workspace / "a.py", "w") as f: f.write("def func(): pass")
    with open(workspace / "b.py", "w") as f: f.write("def func(): pass")
    # 1 JavaScript file
    with open(workspace / "main.js", "w") as f: f.write("const a = 1;")
    # 1 unknown text file
    with open(workspace / "notes", "w") as f: f.write("random thoughts")
    # 1 binary file
    with open(workspace / "bin_file", "wb") as f: f.write(b"\x00\x00\x00\x00")
    
    profile = detector.analyze_workspace(workspace)
    
    # 5 files total
    assert profile.total_files == 5
    assert profile.binary_files == 1
    assert profile.unknown_files == 1
    assert profile.source_files == 3 # a.py, b.py, main.js
    
    # Check language distributions
    assert "Python" in profile.languages
    assert profile.languages["Python"]["count"] == 2
    assert profile.languages["Python"]["percentage"] == pytest.approx(0.6667, abs=1e-3)
    
    assert "JavaScript" in profile.languages
    assert profile.languages["JavaScript"]["count"] == 1
    assert profile.languages["JavaScript"]["percentage"] == pytest.approx(0.3333, abs=1e-3)

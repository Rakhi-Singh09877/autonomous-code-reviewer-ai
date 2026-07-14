import os
import shutil
import tempfile
from pathlib import Path
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.domain.models.parser import CodeEntity
from app.infrastructure.code_parser.parser import DefaultCodeParser, ParserFactory

@pytest.fixture
def temp_repo():
    """Creates a temporary repository directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_python_ast_parser(temp_repo):
    parser = DefaultCodeParser()
    repo_path = Path(temp_repo)
    file_path = repo_path / "main.py"
    
    python_code = """
import os
from sys import exit

@decorator1
@decorator2
class MathOps(BaseOps):
    \"\"\"Perform math operations.\"\"\"
    def add(self, a, b):
        # TODO: support floating numbers
        return a + b

def standalone_func():
    return True
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(python_code)
        
    parsed = parser.parse_file(file_path, "main.py", "Python")
    
    assert parsed.parse_status == "success"
    assert parsed.language == "Python"
    assert "os" in parsed.imports
    assert "sys.exit" in parsed.imports
    
    # Check classes
    assert len(parsed.classes) == 1
    cls = parsed.classes[0]
    assert cls.name == "MathOps"
    assert cls.parent_class == "BaseOps"
    assert "decorator1" in cls.decorators
    assert cls.docstring == "Perform math operations."
    
    # Check functions/methods
    assert len(parsed.functions) == 2  # add (method) and standalone_func (function)
    func_names = [f.name for f in parsed.functions]
    assert "add" in func_names
    assert "standalone_func" in func_names
    
    # Check todos
    assert len(parsed.todos) == 1
    assert "TODO" in parsed.todos[0]["text"]
    
    # Check chunks
    assert len(parsed.chunks) == 4 # overview, MathOps class, add method, standalone_func function
    assert any(c["entity_name"] == "MathOps" for c in parsed.chunks)
    assert any(c["entity_name"] == "add" for c in parsed.chunks)

def test_java_parser(temp_repo):
    parser = DefaultCodeParser()
    repo_path = Path(temp_repo)
    file_path = repo_path / "Controller.java"
    
    java_code = """
package app.controllers;
import java.util.List;
import app.models.User;

@RestController
public class UserController extends BaseController {
    /** Get user list */
    @GetMapping
    public List<User> getUsers() {
        // TODO: add filters
        return null;
    }
}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(java_code)
        
    parsed = parser.parse_file(file_path, "Controller.java", "Java")
    
    assert parsed.parse_status == "success"
    assert parsed.package_name == "app.controllers"
    assert "java.util.List" in parsed.imports
    
    # Class assertions
    assert len(parsed.classes) == 1
    cls = parsed.classes[0]
    assert cls.name == "UserController"
    assert cls.parent_class == "BaseController"
    assert "RestController" in cls.decorators
    assert cls.visibility == "public"
    
    # Method assertions
    assert len(parsed.functions) == 1
    meth = parsed.functions[0]
    assert meth.name == "getUsers"
    assert meth.type == "method"
    assert meth.parent_class == "UserController"
    assert "GetMapping" in meth.decorators
    assert "Get user list" in meth.docstring
    
    # Todo checks
    assert len(parsed.todos) == 1
    assert "TODO: add filters" in parsed.todos[0]["text"]

def test_javascript_parser(temp_repo):
    parser = DefaultCodeParser()
    repo_path = Path(temp_repo)
    file_path = repo_path / "utils.js"
    
    js_code = """
import axios from 'axios';
const config = require('./config');

class ApiService extends Base {
    constructor() {
        super();
    }
}

/** Standalone fetch function */
function fetchData(url) {
    return axios.get(url);
}

const add = (a, b) => {
    // FIXME: validation check
    return a + b;
};
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(js_code)
        
    parsed = parser.parse_file(file_path, "utils.js", "JavaScript")
    
    assert parsed.parse_status == "success"
    assert "axios" in parsed.imports
    assert "./config" in parsed.imports
    
    # Class
    assert len(parsed.classes) == 1
    assert parsed.classes[0].name == "ApiService"
    assert parsed.classes[0].parent_class == "Base"
    
    # Standalone and arrow functions
    assert len(parsed.functions) == 2
    names = [f.name for f in parsed.functions]
    assert "fetchData" in names
    assert "add" in names
    
    # Standalone function docstring
    fetch_func = next(f for f in parsed.functions if f.name == "fetchData")
    assert "Standalone fetch function" in fetch_func.docstring

def test_fallback_parser(temp_repo):
    parser = DefaultCodeParser()
    repo_path = Path(temp_repo)
    file_path = repo_path / "metadata.json"
    
    json_content = """{
    "name": "project",
    // TODO: update version before release
    "version": "1.0.0"
}"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json_content)
        
    parsed = parser.parse_file(file_path, "metadata.json", "JSON")
    assert parsed.parse_status == "unsupported"
    assert len(parsed.todos) == 1
    assert "TODO" in parsed.todos[0]["text"]

def test_parse_repository_has_tests(temp_repo):
    parser = DefaultCodeParser()
    repo_path = Path(temp_repo)
    
    # Create code file and test file
    code_file = repo_path / "auth.py"
    test_file = repo_path / "test_auth.py"
    
    with open(code_file, "w") as f: f.write("def login(): pass")
    with open(test_file, "w") as f: f.write("def test_login(): pass")
    
    files_to_parse = [
        (code_file, "Python"),
        (test_file, "Python")
    ]
    
    structure = parser.parse_repository(repo_path, files_to_parse)
    assert structure.total_files == 2
    assert structure.parsed_files == 2
    
    # auth.py should have tests detected
    auth_parsed = next(f for f in structure.files if f.relative_path == "auth.py")
    assert auth_parsed.has_tests == True
    
    # test_auth.py does not need to have tests itself
    test_parsed = next(f for f in structure.files if f.relative_path == "test_auth.py")
    assert test_parsed.has_tests == False

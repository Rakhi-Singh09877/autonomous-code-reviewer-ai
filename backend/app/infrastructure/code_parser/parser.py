import ast
import os
import re
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from app.core.logging import logger
from app.domain.models.parser import CodeEntity, ParsedFile, CodebaseStructure
from app.domain.models.repository import Repository
from app.use_cases.interfaces.parser_port import CodeParserPort

# Helper logic for lightweight brace balancing
def find_matching_brace_lines(lines: List[str], start_line_idx: int) -> Tuple[int, int]:
    open_count = 0
    started = False
    for idx in range(start_line_idx, len(lines)):
        line = lines[idx]
        open_count += line.count("{")
        if "{" in line:
            started = True
        open_count -= line.count("}")
        if started and open_count <= 0:
            return start_line_idx + 1, idx + 1
    return start_line_idx + 1, len(lines)

# Heuristic Cyclomatic Complexity Estimator
def calculate_complexity(content: str) -> int:
    score = 1
    # General branch and loop markers across Python, Java, JS, TS
    constructs = [
        r"\bif\b", r"\belif\b", r"\belse\s+if\b", r"\bfor\b",
        r"\bwhile\b", r"\bcatch\b", r"\bexcept\b", r"\bcase\s+",
        r"&&", r"\|\|", r"\band\b", r"\bor\b"
    ]
    for pattern in constructs:
        score += len(re.findall(pattern, content))
    return score

# TODO/FIXME comments extractor
def extract_comments_and_todos(lines: List[str]) -> List[Dict[str, Any]]:
    todos = []
    todo_pattern = re.compile(r"(?:#|//|/\*|\*)\s*(TODO|FIXME):?\s*(.*)", re.IGNORECASE)
    for idx, line in enumerate(lines):
        match = todo_pattern.search(line)
        if match:
            todos.append({
                "line": idx + 1,
                "text": match.group(0).strip()
            })
    return todos

# RAG-ready chunk generator
def generate_rag_chunks(
    file_relative_path: str,
    language: str,
    content: str,
    classes: List[CodeEntity],
    functions: List[CodeEntity]
) -> List[Dict[str, Any]]:
    chunks = []
    
    # 1. Module Overview Chunk
    overview_text = (
        f"File: {file_relative_path}\n"
        f"Language: {language}\n"
        f"Symbols Defined: {', '.join([c.name for c in classes] + [f.name for f in functions])}\n"
    )
    chunks.append({
        "id": f"{file_relative_path}#overview",
        "entity_name": "module_overview",
        "language": language,
        "text": overview_text,
        "metadata": {
            "type": "overview",
            "file_path": file_relative_path
        }
    })

    # 2. Entity-level Chunks
    for c in classes:
        entity_text = content[c.source_range[0]:c.source_range[1]]
        if not entity_text.strip():
            entity_text = f"class {c.name}\nSignature: {c.signature}\nParent: {c.parent_class or 'None'}\nDocstring: {c.docstring or ''}"
        
        chunks.append({
            "id": f"{file_relative_path}#class-{c.name}",
            "entity_name": c.name,
            "language": language,
            "text": entity_text,
            "metadata": {
                "type": "class",
                "file_path": file_relative_path,
                "start_line": c.start_line,
                "end_line": c.end_line
            }
        })

    for f in functions:
        entity_text = content[f.source_range[0]:f.source_range[1]]
        if not entity_text.strip():
            entity_text = f"{f.type} {f.name}\nSignature: {f.signature}\nDocstring: {f.docstring or ''}"
        
        chunks.append({
            "id": f"{file_relative_path}#{f.type}-{f.name}",
            "entity_name": f.name,
            "language": language,
            "text": entity_text,
            "metadata": {
                "type": f.type,
                "file_path": file_relative_path,
                "start_line": f.start_line,
                "end_line": f.end_line
            }
        })

    return chunks

class BaseFileParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path, relative_path: str, content: str, language: str) -> ParsedFile:
        pass

class PythonVisitor(ast.NodeVisitor):
    def __init__(self, source_lines: List[str], source_content: str):
        self.source_lines = source_lines
        self.source_content = source_content
        self.imports: List[str] = []
        self.classes: List[CodeEntity] = []
        self.functions: List[CodeEntity] = []
        self.symbols: List[str] = []
        self.dependencies: List[str] = []
        self.current_class: Optional[str] = None

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
            self.dependencies.append(alias.name)

    def visit_ImportFrom(self, node):
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports.append(full_name)
            self.dependencies.append(module if module else alias.name)

    def visit_ClassDef(self, node):
        class_name = node.name
        self.symbols.append(class_name)
        
        parent_class = None
        if node.bases:
            first_base = node.bases[0]
            if isinstance(first_base, ast.Name):
                parent_class = first_base.id
            elif isinstance(first_base, ast.Attribute) and isinstance(first_base.value, ast.Name):
                parent_class = f"{first_base.value.id}.{first_base.attr}"

        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Name):
                decorators.append(f"{dec.value.id}.{dec.attr}")

        visibility = "private" if class_name.startswith("_") else "public"
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        
        start_offset = self._get_offset(start_line, node.col_offset)
        end_offset = self._get_offset(end_line, getattr(node, "end_col_offset", 0))

        signature = f"class {class_name}"
        if parent_class:
            signature += f"({parent_class})"

        docstring = ast.get_docstring(node)

        entity = CodeEntity(
            name=class_name,
            type="class",
            signature=signature,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
            source_range=(start_offset, end_offset),
            visibility=visibility,
            decorators=decorators,
            parent_class=parent_class
        )
        self.classes.append(entity)

        old_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        self._parse_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._parse_function(node)

    def _parse_function(self, node):
        func_name = node.name
        self.symbols.append(func_name)

        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Attribute) and isinstance(dec.value, ast.Name):
                decorators.append(f"{dec.value.id}.{dec.attr}")

        visibility = "private" if func_name.startswith("_") else "public"
        start_line = node.lineno
        end_line = getattr(node, "end_lineno", start_line)
        
        start_offset = self._get_offset(start_line, node.col_offset)
        end_offset = self._get_offset(end_line, getattr(node, "end_col_offset", 0))

        args_list = []
        for arg in node.args.args:
            args_list.append(arg.arg)
        args_str = ", ".join(args_list)
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        signature = f"{prefix} {func_name}({args_str})"

        docstring = ast.get_docstring(node)

        entity = CodeEntity(
            name=func_name,
            type="method" if self.current_class else "function",
            signature=signature,
            start_line=start_line,
            end_line=end_line,
            docstring=docstring,
            source_range=(start_offset, end_offset),
            visibility=visibility,
            decorators=decorators,
            parent_class=self.current_class
        )
        self.functions.append(entity)

    def _get_offset(self, lineno: int, col_offset: int) -> int:
        offset = 0
        for i in range(lineno - 1):
            if i < len(self.source_lines):
                offset += len(self.source_lines[i]) + 1
        offset += col_offset
        return offset

class PythonASTParser(BaseFileParser):
    def parse(self, file_path: Path, relative_path: str, content: str, language: str) -> ParsedFile:
        lines = content.splitlines()
        line_count = len(lines)
        char_count = len(content)
        module_name = file_path.stem
        package_name = ""

        try:
            tree = ast.parse(content)
            visitor = PythonVisitor(lines, content)
            visitor.visit(tree)
            
            classes = visitor.classes
            functions = visitor.functions
            imports = visitor.imports
            symbols = visitor.symbols
            dependencies = visitor.dependencies
            status = "success"
        except SyntaxError as e:
            logger.error(f"Syntax error parsing Python file {relative_path}: {e}")
            classes = []
            functions = []
            imports = []
            symbols = []
            dependencies = []
            status = "partial_failure"

        todos = extract_comments_and_todos(lines)
        complexity = calculate_complexity(content)
        chunks = generate_rag_chunks(relative_path, language, content, classes, functions)

        return ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            module_name=module_name,
            package_name=package_name,
            language=language,
            imports=imports,
            classes=classes,
            functions=functions,
            todos=todos,
            line_count=line_count,
            char_count=char_count,
            parse_status=status,
            symbols=symbols,
            dependencies=dependencies,
            complexity_score=complexity,
            has_tests=False,
            chunks=chunks
        )

class JavaParser(BaseFileParser):
    def parse(self, file_path: Path, relative_path: str, content: str, language: str) -> ParsedFile:
        lines = content.splitlines()
        line_count = len(lines)
        char_count = len(content)

        package_match = re.search(r"^\s*package\s+([\w\.]+);", content, re.MULTILINE)
        package_name = package_match.group(1) if package_match else ""
        module_name = file_path.stem

        imports = re.findall(r"^\s*import\s+([\w\.\*]+);", content, re.MULTILINE)
        dependencies = list(set(imports))

        classes: List[CodeEntity] = []
        functions: List[CodeEntity] = []
        symbols: List[str] = []

        class_regex = re.compile(
            r"((?:public|protected|private|static|abstract|final|[ \t])*)\bclass\s+(\w+)(?:\s+extends\s+(\w+))?\s*(?:implements\s+[\w\s,]+)?\s*\{"
        )
        for match in class_regex.finditer(content):
            class_name = match.group(2)
            symbols.append(class_name)
            parent_class = match.group(3)

            match_start_char = match.start()
            start_line = content.count("\n", 0, match_start_char) + 1
            start_l, end_l = find_matching_brace_lines(lines, start_line - 1)
            end_offset = len("\n".join(lines[:end_l]))

            visibility = self._parse_visibility(match.group(1) or "")
            decorators = self._find_decorators_above(lines, start_line - 1)

            entity = CodeEntity(
                name=class_name,
                type="class",
                signature=match.group(0).strip().rstrip("{").strip(),
                start_line=start_line,
                end_line=end_l,
                docstring=self._extract_docstring_above(lines, start_line - 1),
                source_range=(match_start_char, end_offset),
                visibility=visibility,
                decorators=decorators,
                parent_class=parent_class
            )
            classes.append(entity)

        method_regex = re.compile(
            r"((?:public|protected|private|static|final|synchronized|[ \t])*)\b([\w\<\>\[\]]+)\s+(\w+)\s*\((.*?)\)\s*(?:throws\s+[\w\s,]+)?\s*\{"
        )
        for match in method_regex.finditer(content):
            method_name = match.group(3)
            if method_name in ("class", "if", "for", "while", "switch", "catch"):
                continue

            symbols.append(method_name)
            match_start_char = match.start()
            start_line = content.count("\n", 0, match_start_char) + 1
            start_l, end_l = find_matching_brace_lines(lines, start_line - 1)
            end_offset = len("\n".join(lines[:end_l]))

            visibility = self._parse_visibility(match.group(1) or "")
            decorators = self._find_decorators_above(lines, start_line - 1)

            parent_class = None
            for c in classes:
                if c.start_line <= start_line <= c.end_line:
                    parent_class = c.name
                    break

            entity = CodeEntity(
                name=method_name,
                type="method" if parent_class else "function",
                signature=match.group(0).strip().rstrip("{").strip(),
                start_line=start_line,
                end_line=end_l,
                docstring=self._extract_docstring_above(lines, start_line - 1),
                source_range=(match_start_char, end_offset),
                visibility=visibility,
                decorators=decorators,
                parent_class=parent_class
            )
            functions.append(entity)

        todos = extract_comments_and_todos(lines)
        complexity = calculate_complexity(content)
        chunks = generate_rag_chunks(relative_path, language, content, classes, functions)

        return ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            module_name=module_name,
            package_name=package_name,
            language=language,
            imports=imports,
            classes=classes,
            functions=functions,
            todos=todos,
            line_count=line_count,
            char_count=char_count,
            parse_status="success",
            symbols=symbols,
            dependencies=dependencies,
            complexity_score=complexity,
            has_tests=False,
            chunks=chunks
        )

    def _parse_visibility(self, modifiers: str) -> str:
        if "public" in modifiers: return "public"
        if "protected" in modifiers: return "protected"
        if "private" in modifiers: return "private"
        return "internal"

    def _find_decorators_above(self, lines: List[str], start_line_idx: int) -> List[str]:
        decorators = []
        idx = start_line_idx - 1
        while idx >= 0:
            line = lines[idx].strip()
            if not line:
                idx -= 1
                continue
            if line.startswith("@"):
                decorators.append(line[1:])
                idx -= 1
            else:
                break
        return decorators

    def _extract_docstring_above(self, lines: List[str], start_line_idx: int) -> Optional[str]:
        idx = start_line_idx - 1
        comments = []
        in_javadoc = False
        while idx >= 0:
            line = lines[idx].strip()
            if not line:
                idx -= 1
                continue
            if line.startswith("@"):
                idx -= 1
                continue
            if line.endswith("*/"):
                in_javadoc = True
                comments.insert(0, line)
                idx -= 1
                continue
            if in_javadoc:
                comments.insert(0, line)
                if line.startswith("/*"):
                    break
                idx -= 1
            else:
                break
        return "\n".join(comments) if comments else None

class JavaScriptParser(BaseFileParser):
    def parse(self, file_path: Path, relative_path: str, content: str, language: str) -> ParsedFile:
        lines = content.splitlines()
        line_count = len(lines)
        char_count = len(content)
        module_name = file_path.stem
        package_name = ""

        imports = re.findall(r"import\s+.*\s+from\s+['\"](.*)['\"]", content)
        requires = re.findall(r"require\(['\"](.*)['\"]\)", content)
        imports.extend(requires)
        dependencies = list(set(imports))

        classes: List[CodeEntity] = []
        functions: List[CodeEntity] = []
        symbols: List[str] = []

        class_regex = re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{")
        for match in class_regex.finditer(content):
            class_name = match.group(1)
            symbols.append(class_name)
            parent_class = match.group(2)

            match_start_char = match.start()
            start_line = content.count("\n", 0, match_start_char) + 1
            start_l, end_l = find_matching_brace_lines(lines, start_line - 1)
            end_offset = len("\n".join(lines[:end_l]))

            entity = CodeEntity(
                name=class_name,
                type="class",
                signature=match.group(0).strip().rstrip("{").strip(),
                start_line=start_line,
                end_line=end_l,
                docstring=self._extract_docstring_above(lines, start_line - 1),
                source_range=(match_start_char, end_offset),
                visibility="public",
                decorators=[],
                parent_class=parent_class
            )
            classes.append(entity)

        func_regex = re.compile(r"function\s+(\w+)\s*\((.*?)\)")
        for match in func_regex.finditer(content):
            func_name = match.group(1)
            symbols.append(func_name)
            match_start_char = match.start()
            start_line = content.count("\n", 0, match_start_char) + 1
            start_l, end_l = find_matching_brace_lines(lines, start_line - 1)
            end_offset = len("\n".join(lines[:end_l]))

            parent_class = self._get_parent_class_context(start_line, classes)

            entity = CodeEntity(
                name=func_name,
                type="method" if parent_class else "function",
                signature=match.group(0).strip(),
                start_line=start_line,
                end_line=end_l,
                docstring=self._extract_docstring_above(lines, start_line - 1),
                source_range=(match_start_char, end_offset),
                visibility="public",
                decorators=[],
                parent_class=parent_class
            )
            functions.append(entity)

        arrow_regex = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>")
        for match in arrow_regex.finditer(content):
            func_name = match.group(1)
            symbols.append(func_name)
            match_start_char = match.start()
            start_line = content.count("\n", 0, match_start_char) + 1
            start_l, end_l = find_matching_brace_lines(lines, start_line - 1)
            end_offset = len("\n".join(lines[:end_l]))

            parent_class = self._get_parent_class_context(start_line, classes)

            entity = CodeEntity(
                name=func_name,
                type="method" if parent_class else "function",
                signature=f"const {func_name} = ({match.group(2)}) =>",
                start_line=start_line,
                end_line=end_l,
                docstring=self._extract_docstring_above(lines, start_line - 1),
                source_range=(match_start_char, end_offset),
                visibility="public",
                decorators=[],
                parent_class=parent_class
            )
            functions.append(entity)

        todos = extract_comments_and_todos(lines)
        complexity = calculate_complexity(content)
        chunks = generate_rag_chunks(relative_path, language, content, classes, functions)

        return ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            module_name=module_name,
            package_name=package_name,
            language=language,
            imports=imports,
            classes=classes,
            functions=functions,
            todos=todos,
            line_count=line_count,
            char_count=char_count,
            parse_status="success",
            symbols=symbols,
            dependencies=dependencies,
            complexity_score=complexity,
            has_tests=False,
            chunks=chunks
        )

    def _get_parent_class_context(self, line: int, classes: List[CodeEntity]) -> Optional[str]:
        for c in classes:
            if c.start_line <= line <= c.end_line:
                return c.name
        return None

    def _extract_docstring_above(self, lines: List[str], start_line_idx: int) -> Optional[str]:
        idx = start_line_idx - 1
        comments = []
        in_comment_block = False
        while idx >= 0:
            line = lines[idx].strip()
            if not line:
                idx -= 1
                continue
            if line.startswith("@"):
                idx -= 1
                continue
            if line.endswith("*/"):
                in_comment_block = True
                comments.insert(0, line)
                idx -= 1
                continue
            if in_comment_block:
                comments.insert(0, line)
                if line.startswith("/*"):
                    break
                idx -= 1
            else:
                break
        return "\n".join(comments) if comments else None

class TypeScriptParser(JavaScriptParser):
    pass

class FallbackParser(BaseFileParser):
    def parse(self, file_path: Path, relative_path: str, content: str, language: str) -> ParsedFile:
        lines = content.splitlines()
        line_count = len(lines)
        char_count = len(content)
        module_name = file_path.name
        package_name = ""

        todos = extract_comments_and_todos(lines)
        complexity = calculate_complexity(content)

        return ParsedFile(
            file_path=file_path,
            relative_path=relative_path,
            module_name=module_name,
            package_name=package_name,
            language=language,
            imports=[],
            classes=[],
            functions=[],
            todos=todos,
            line_count=line_count,
            char_count=char_count,
            parse_status="unsupported",
            symbols=[],
            dependencies=[],
            complexity_score=complexity,
            has_tests=False,
            chunks=generate_rag_chunks(relative_path, language, content, [], [])
        )

class ParserFactory:
    @staticmethod
    def get_parser(language: str) -> BaseFileParser:
        lang = language.lower()
        if lang == "python":
            return PythonASTParser()
        elif lang == "java":
            return JavaParser()
        elif lang == "javascript":
            return JavaScriptParser()
        elif lang == "typescript":
            return TypeScriptParser()
        else:
            return FallbackParser()

class DefaultCodeParser(CodeParserPort):
    def parse_file(self, file_path: Path, relative_path: str, language: str) -> ParsedFile:
        parser = ParserFactory.get_parser(language)
        resolved_path = Path(file_path).resolve()
        
        try:
            with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as e:
            logger.error(f"Error reading file {resolved_path}: {e}")
            content = ""

        parsed_file = parser.parse(resolved_path, relative_path, content, language)
        return parsed_file

    def parse_repository(self, repository_path: Path, files_to_parse: List[Tuple[Path, str]]) -> CodebaseStructure:
        logger.info(f"Parsing repository at {repository_path} containing {len(files_to_parse)} files.")
        
        all_relative_paths = set()
        resolved_repo_path = Path(repository_path).resolve()
        for root, _, filenames in os.walk(resolved_repo_path):
            for fname in filenames:
                fpath = Path(root) / fname
                try:
                    all_relative_paths.add(str(fpath.relative_to(resolved_repo_path)))
                except ValueError:
                    pass

        files: List[ParsedFile] = []
        total_files = len(files_to_parse)
        parsed_files = 0
        failed_files = 0
        unsupported_files = 0
        lang_stats: Dict[str, int] = {}

        for file_path, language in files_to_parse:
            try:
                rel_path = str(Path(file_path).resolve().relative_to(resolved_repo_path))
            except ValueError:
                rel_path = str(file_path)

            try:
                parsed_file = self.parse_file(file_path, rel_path, language)
                parsed_file.has_tests = self._check_has_tests(rel_path, all_relative_paths)
                
                if parsed_file.parse_status == "success":
                    parsed_files += 1
                elif parsed_file.parse_status == "unsupported":
                    unsupported_files += 1
                else:
                    failed_files += 1
                
                files.append(parsed_file)
                lang_stats[language] = lang_stats.get(language, 0) + 1
            except Exception as e:
                logger.error(f"Failed to parse file {file_path}: {e}")
                failed_files += 1

        return CodebaseStructure(
            files=files,
            total_files=total_files,
            parsed_files=parsed_files,
            failed_files=failed_files,
            unsupported_files=unsupported_files,
            language_statistics=lang_stats,
        )

    def _check_has_tests(self, relative_path: str, all_relative_paths: set) -> bool:
        path = Path(relative_path)
        stem = path.stem
        ext = path.suffix
        
        candidates = [
            f"test_{stem}{ext}",
            f"{stem}_test{ext}",
            f"{stem}.test{ext}",
            f"{stem}.spec{ext}",
            f"tests/test_{stem}{ext}",
            f"test/test_{stem}{ext}",
        ]
        
        for c in candidates:
            if c in all_relative_paths or any(p.endswith(c) for p in all_relative_paths):
                return True
        return False

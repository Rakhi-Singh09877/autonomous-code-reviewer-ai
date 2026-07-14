from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple
from app.domain.models.parser import ParsedFile, CodebaseStructure

class CodeParserPort(ABC):
    """
    Interface Port defining methods for code parsing and entity extraction.
    """
    @abstractmethod
    def parse_file(self, file_path: Path, relative_path: str, language: str) -> ParsedFile:
        """
        Parses a single file and extracts imports, entities, complexity, symbols, and generates RAG-ready chunks.
        """
        pass

    @abstractmethod
    def parse_repository(self, repository_path: Path, files_to_parse: List[Tuple[Path, str]]) -> CodebaseStructure:
        """
        Parses a list of files in the repository and aggregates the structural information.
        """
        pass

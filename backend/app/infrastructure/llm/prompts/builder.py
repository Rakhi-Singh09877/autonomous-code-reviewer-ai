from typing import Dict, Any, List, Tuple
from app.domain.models.analysis import ReviewPolicy
from app.domain.models.embedding import SearchResult
from app.infrastructure.llm.prompts.library import SYSTEM_PROMPTS, USER_PROMPTS

class PromptBuilder:
    """
    Service responsible for building structured prompts for LLM analytical agents.
    Assembles system instructions, policies, metadata, RAG context, and source code.
    """

    @staticmethod
    def build_prompts(
        file_path: str,
        language: str,
        repo_metadata: Dict[str, Any],
        policy: ReviewPolicy,
        rag_chunks: List[SearchResult],
        file_content: str,
        line_offset: int = 0
    ) -> Tuple[str, str]:
        """
        Builds system and user prompts matching the configured policy version.
        """
        # Resolve prompt version
        version = policy.prompt_version.value
        
        system_template = SYSTEM_PROMPTS.get(version, SYSTEM_PROMPTS["review_v1"])
        user_template = USER_PROMPTS.get(version, USER_PROMPTS["review_v1"])

        # Format Repository Metadata
        repo_meta_parts = []
        for k, v in repo_metadata.items():
            repo_meta_parts.append(f"{k}={v}")
        repo_metadata_str = ", ".join(repo_meta_parts) if repo_meta_parts else "No metadata available"

        # Format Review Policy Components
        rules_str = ", ".join(policy.rules) if policy.rules else "Standard codebase checks"
        focus_areas_str = ", ".join(policy.focus_areas) if policy.focus_areas else "General code quality"
        custom_instructions_str = policy.custom_instructions or "Provide clean refactoring code changes."

        # Format RAG Context (XML-encapsulated)
        rag_parts = []
        for chunk in rag_chunks:
            doc = chunk.document
            rag_parts.append(
                f'<rag_context id="{doc.id}" path="{doc.file_path}" entity="{doc.entity_name}" type="{doc.entity_type}">\n'
                f'{doc.text}\n'
                f'</rag_context>'
            )
        rag_context_str = "\n\n".join(rag_parts) if rag_parts else "No external reference code chunks retrieved."

        # Format Source Code (Line Numbered)
        lines = file_content.splitlines()
        numbered_lines = [f"{i + 1 + line_offset}: {line}" for i, line in enumerate(lines)]
        numbered_source = "\n".join(numbered_lines)

        # Render User Prompt variables
        user_prompt = user_template.format(
            file_path=file_path,
            language=language,
            repo_metadata=repo_metadata_str,
            rules=rules_str,
            focus_areas=focus_areas_str,
            custom_instructions=custom_instructions_str,
            rag_context=rag_context_str,
            file_content=numbered_source
        )

        return system_template, user_prompt

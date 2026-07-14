from typing import Dict

SYSTEM_PROMPTS: Dict[str, str] = {
    "review_v1": (
        "You are an elite, senior software developer and code review assistant.\n"
        "Your task is to analyze the provided code file and detect bugs, logic errors,\n"
        "poor coding standards, code smells, complexity bottlenecks, and best practice violations.\n"
        "Focus on code quality and correctness.\n"
        "You must output code review issues through the forced tool structure."
    ),
    "security_v1": (
        "You are an expert cybersecurity auditor and secure coding expert.\n"
        "Analyze the provided code file for OWASP Top 10 vulnerabilities, injection vectors,\n"
        "poor authentication mechanisms, hardcoded secrets, resource leaks, and insecure data handling.\n"
        "You must output security review issues through the forced tool structure."
    ),
    "performance_v1": (
        "You are an expert systems performance engineer.\n"
        "Analyze the provided code file to find runtime inefficiencies, high memory allocation patterns,\n"
        "unnecessary database queries/loops, thread blockages, and caching opportunities.\n"
        "You must output performance review issues through the forced tool structure."
    ),
    "documentation_v1": (
        "You are a professional technical writer and document structures specialist.\n"
        "Analyze the provided code file to identify undocumented public APIs, missing docstrings,\n"
        "vague comments, or complicated module structures that need architectural documentation.\n"
        "You must output documentation issues through the forced tool structure."
    )
}

USER_PROMPTS: Dict[str, str] = {
    "review_v1": (
        "File Path: {file_path}\n"
        "Programming Language: {language}\n"
        "Repository Metadata: {repo_metadata}\n\n"
        "--- Review Policy ---\n"
        "Rules: {rules}\n"
        "Focus Areas: {focus_areas}\n"
        "Custom Instructions: {custom_instructions}\n\n"
        "--- Relevant Code Context (RAG) ---\n"
        "{rag_context}\n\n"
        "--- Target Source Code (Line Numbered) ---\n"
        "{file_content}\n\n"
        "Please analyze the target source code carefully. Identify quality issues, bug risks, style violations, and maintainability concerns, referencing exact line ranges."
    ),
    "security_v1": (
        "File Path: {file_path}\n"
        "Programming Language: {language}\n"
        "Repository Metadata: {repo_metadata}\n\n"
        "--- Security Policy ---\n"
        "Rules: {rules}\n"
        "Focus Areas: {focus_areas}\n"
        "Custom Instructions: {custom_instructions}\n\n"
        "--- Relevant Code Context (RAG) ---\n"
        "{rag_context}\n\n"
        "--- Target Source Code (Line Numbered) ---\n"
        "{file_content}\n\n"
        "Analyze the code specifically for security vulnerabilities, secrets leakage, and compliance issues, referencing exact line ranges."
    ),
    "performance_v1": (
        "File Path: {file_path}\n"
        "Programming Language: {language}\n"
        "Repository Metadata: {repo_metadata}\n\n"
        "--- Performance Guidelines ---\n"
        "Rules: {rules}\n"
        "Focus Areas: {focus_areas}\n"
        "Custom Instructions: {custom_instructions}\n\n"
        "--- Relevant Code Context (RAG) ---\n"
        "{rag_context}\n\n"
        "--- Target Source Code (Line Numbered) ---\n"
        "{file_content}\n\n"
        "Analyze the code specifically for scalability, CPU/memory performance bottlenecks, and resource usage inefficiencies, referencing exact line ranges."
    ),
    "documentation_v1": (
        "File Path: {file_path}\n"
        "Programming Language: {language}\n"
        "Repository Metadata: {repo_metadata}\n\n"
        "--- Documentation Requirements ---\n"
        "Rules: {rules}\n"
        "Focus Areas: {focus_areas}\n"
        "Custom Instructions: {custom_instructions}\n\n"
        "--- Relevant Code Context (RAG) ---\n"
        "{rag_context}\n\n"
        "--- Target Source Code (Line Numbered) ---\n"
        "{file_content}\n\n"
        "Analyze the code for API completeness, missing docs, and complex structure layout to describe, referencing exact line ranges."
    )
}

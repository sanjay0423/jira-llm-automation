import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import JiraTriageRequest, build_prompt
from rag import IssueContext, KnowledgeSnippet, build_retrieval_query, format_knowledge_snippets, score_text


def test_build_retrieval_query_includes_issue_metadata():
    issue = IssueContext(
        issue_key="JLA-500",
        summary="Airflow DAG failing on Redshift load",
        description="The load_subscriptions_to_redshift task is timing out.",
        project_key="JLA",
        issue_type="Bug",
        priority="High",
    )

    query = build_retrieval_query(issue)

    assert "JLA-500" in query
    assert "Airflow DAG failing on Redshift load" in query
    assert "load_subscriptions_to_redshift" in query


def test_score_text_prefers_relevant_airflow_content():
    query = "airflow dag failing redshift load timeout"
    strong_match = "Airflow DAGs use operators and retries. Redshift load failures often happen on task timeout."
    weak_match = "This page describes billing account setup and user onboarding."

    assert score_text(query, strong_match, "Airflow troubleshooting") > score_text(query, weak_match, "Billing overview")


def test_format_knowledge_snippets_includes_titles_and_urls():
    snippets = [
        KnowledgeSnippet(
            title="Airflow troubleshooting",
            url="https://airflow.apache.org/docs/apache-airflow/stable/troubleshooting.html",
            excerpt="Check scheduler logs and task retries.",
            source="airflow.apache.org",
            score=0.9,
        )
    ]

    context = format_knowledge_snippets(snippets)

    assert "Relevant internal context" in context
    assert "Airflow troubleshooting" in context
    assert "https://airflow.apache.org/docs/apache-airflow/stable/troubleshooting.html" in context
    assert "Check scheduler logs" in context


def test_build_prompt_includes_rag_context_block():
    payload = JiraTriageRequest(
        issueKey="JLA-600",
        summary="Airflow DAG failing",
        description="Task timeout on Redshift load step.",
        priority="High",
        issueType="Bug",
        projectKey="JLA",
        reporter="Sanjay Rane",
    )
    snippets = [
        KnowledgeSnippet(
            title="Airflow troubleshooting",
            url="https://airflow.apache.org/docs/apache-airflow/stable/troubleshooting.html",
            excerpt="Check scheduler logs and task retries.",
            source="airflow.apache.org",
            score=0.9,
        )
    ]

    prompt = build_prompt(payload, snippets)

    assert "Relevant internal context" in prompt
    assert "Airflow troubleshooting" in prompt
    assert "Check scheduler logs" in prompt


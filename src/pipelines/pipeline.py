import json
import os
import sys
import time

import httpx

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from rich import print

from src.agents.agent import (
    build_professor_search_agent,
    build_scrape_agent,
    resume_parser_chain,
    fit_ranker_chain,
    email_draft_chain,
)
from src.tools.resume_utils import find_urls


def invoke_with_backoff(runnable, payload, max_attempts: int = 8, base_wait: float = 30.0):
    """
    Calls runnable.invoke(payload), retrying on Mistral 429 rate-limit errors with a
    much longer backoff than the client's built-in retry uses. Honors the server's
    Retry-After header when present, otherwise falls back to exponential backoff.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return runnable.invoke(payload)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 429 and attempt < max_attempts:
                retry_after = e.response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else base_wait * (2 ** (attempt - 1))
                print(f"[rate limit] 429 from Mistral, attempt {attempt}/{max_attempts}. "
                      f"Waiting {wait:.0f}s before retrying...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("Exceeded max retry attempts after repeated 429 rate limit errors.")


def _safe_json_loads(text: str, fallback):
    """
    LLMs occasionally wrap JSON in markdown fences or add stray text even when
    told not to. Strip common wrappers before parsing, and fall back gracefully
    instead of crashing the whole pipeline on one malformed response.
    """
    if text is None:
        return fallback
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # remove a leading "json" language tag if present
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return fallback


def parse_resume(resume_text: str) -> dict:
    raw = invoke_with_backoff(resume_parser_chain, {"resume_text": resume_text})
    profile = _safe_json_loads(raw, fallback={
        "name": None,
        "degree": None,
        "research_interests": [],
        "skills": [],
        "publications": [],
        "summary": raw[:400] if isinstance(raw, str) else "",
    })
    # guard against missing/short interest lists
    if not profile.get("research_interests"):
        profile["research_interests"] = ["computer science"]
    return profile


def find_candidate_professors(research_interests: list[str], country: str, max_interests: int = 2) -> str:
    """
    Runs the search agent once per research interest (capped) and concatenates
    the raw findings into a single text blob for the ranking step to parse.
    """
    search_agent = build_professor_search_agent()
    all_notes = []

    for interest in research_interests[:max_interests]:
        query = (
            f"Find current university professors in {country} whose research focuses on "
            f"'{interest}' and who may be accepting PhD students. List their name, university, "
            f"and a link to their official faculty profile page."
        )
        result = invoke_with_backoff(search_agent, {"messages": [("user", query)]})
        text = result["messages"][-1].content
        all_notes.append(f"--- Search notes for interest '{interest}' ---\n{text}")
        time.sleep(10)  # avoid bursting the Mistral API rate limit across successive calls

    return "\n\n".join(all_notes)


def enrich_professor_pages(raw_search_notes: str, max_pages: int = 5) -> str:
    """
    Extracts candidate URLs from the search notes and scrapes each faculty page
    for structured details, appending the scraped notes to the same blob.
    """
    urls = find_urls(raw_search_notes)[:max_pages]
    if not urls:
        return raw_search_notes

    scrape_agent = build_scrape_agent()
    scraped_notes = []
    for url in urls:
        try:
            result = invoke_with_backoff(scrape_agent, {
                "messages": [("user", f"Extract professor details from this faculty page: {url}")]
            })
            text = result["messages"][-1].content
            scraped_notes.append(f"--- Scraped from {url} ---\n{text}")
        except Exception as e:
            scraped_notes.append(f"--- Failed to scrape {url}: {e} ---")
        time.sleep(10)  # avoid bursting the Mistral API rate limit across successive calls

    return raw_search_notes + "\n\n" + "\n\n".join(scraped_notes)


def rank_professors(profile: dict, candidate_notes: str) -> list[dict]:
    raw = invoke_with_backoff(fit_ranker_chain, {
        "profile": json.dumps(profile),
        "candidates": candidate_notes[:12000],  # keep prompt size bounded
    })
    professors = _safe_json_loads(raw, fallback=[])
    if not isinstance(professors, list):
        professors = []
    return professors


def draft_emails(profile: dict, professors: list[dict], top_n: int = 5) -> list[dict]:
    for prof in professors[:top_n]:
        try:
            draft = invoke_with_backoff(email_draft_chain, {
                "profile": json.dumps(profile),
                "professor_name": prof.get("name", "Professor"),
                "university": prof.get("university", ""),
                "research_area": prof.get("research_area", ""),
                "fit_reason": prof.get("fit_reason", ""),
            })
            prof["email_draft"] = draft
        except Exception as e:
            prof["email_draft"] = f"(Could not generate draft: {e})"
        time.sleep(10)  # avoid bursting the Mistral API rate limit across successive calls
    return professors


def run_professor_outreach_pipeline(resume_text: str, country: str) -> dict:
    state = {}

    print("\n" + "=" * 50)
    print("step 1 - parsing resume")
    print("=" * 50)
    profile = parse_resume(resume_text)
    state["profile"] = profile
    print("\nparsed profile:", profile)

    print("\n" + "=" * 50)
    print(f"step 2 - searching for professors in {country}")
    print("=" * 50)
    raw_notes = find_candidate_professors(profile["research_interests"], country)
    print("\nsearch notes:", raw_notes[:1000], "...")

    print("\n" + "=" * 50)
    print("step 3 - scraping faculty pages for details")
    print("=" * 50)
    enriched_notes = enrich_professor_pages(raw_notes)
    print("\nenriched notes gathered.")

    print("\n" + "=" * 50)
    print("step 4 - ranking professors by fit")
    print("=" * 50)
    professors = rank_professors(profile, enriched_notes)
    print("\nranked professors:", professors)

    print("\n" + "=" * 50)
    print("step 5 - drafting outreach emails")
    print("=" * 50)
    professors = draft_emails(profile, professors)
    state["professors"] = professors

    print("\n done.")
    return state
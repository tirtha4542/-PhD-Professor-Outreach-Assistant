import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from src.tools.tools import web_search, scrape_web

load_dotenv()

llm = ChatMistralAI(model="mistral-small-latest", temperature=0, max_retries=1)
structured_llm = ChatMistralAI(model="mistral-large-latest", temperature=0.2, max_retries=1)


# ---------------------------------------------------------------------------
# Tool-using agents (correct create_agent API: model=, system_prompt=)
# ---------------------------------------------------------------------------
def build_professor_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=(
            "You are a research assistant that finds university professors matching a given "
            "research area and country. Use the web_search tool to find current faculty members "
            "at universities in the specified country whose research matches the given topic. "
            "Prioritize official .edu / university department faculty pages over aggregator sites. "
            "For each professor you find, include their name, university, and the URL of their "
            "official faculty profile page. Stay strictly within the requested country and topic — "
            "do not substitute a different field or region."
        ),
    )


def build_scrape_agent():
    return create_agent(
        model=structured_llm,
        tools=[scrape_web],
        system_prompt=(
            "You are a research assistant that extracts structured information about a university "
            "professor from their official faculty profile page. Use the scrape_web tool on the given "
            "URL. From the page content, report: full name, email address (if present), university/"
            "department, and a short description of their research area. If the email is not visible "
            "on the page, say 'not found' rather than guessing."
        ),
    )


# ---------------------------------------------------------------------------
# Plain LCEL chains (no tools needed — operate on text already gathered)
# ---------------------------------------------------------------------------

resume_parser_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You extract structured information from resumes for the purpose of finding PhD advisors. "
     "Respond with ONLY a JSON object — no preamble, no markdown code fences, no explanation."),
    ("human", """Extract the following from this resume text and respond as JSON with exactly these keys:
    - "name": the candidate's full name (or null if not found)
    - "degree": their most recent/relevant degree, e.g. "BSc in Computer Science and Engineering"
    - "research_interests": a list of 3-6 specific research area keywords/phrases (e.g. "computer vision",
      "reinforcement learning", "natural language processing") inferred from their projects, coursework,
      publications, and skills — be specific, not generic
    - "skills": a list of key technical skills
    - "publications": a list of publication titles if any are mentioned, else an empty list
    - "summary": a 2-3 sentence summary of the candidate's academic/research profile

    Resume text:
    {resume_text}
    """)
])
resume_parser_chain = resume_parser_prompt | structured_llm | StrOutputParser()


fit_ranker_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You evaluate how well a list of professors matches a student's research profile for PhD advising. "
     "Respond with ONLY a JSON array — no preamble, no markdown code fences, no explanation."),
    ("human", """Student profile:
    {profile}

    Candidate professors (raw notes gathered from search/scraping):
    {candidates}

    For each DISTINCT professor mentioned, output one JSON object in a JSON array with exactly these keys:
    - "name": professor's full name
    - "email": their email if known, else null
    - "university": university/department name
    - "research_area": short description of their research focus
    - "profile_url": the faculty page URL if known, else null
    - "fit_score": integer 1-10 rating how well their research matches the student's interests
    - "fit_reason": one sentence explaining the match

    Only include professors that actually appear in the candidate notes above. Sort the array by
    fit_score descending. If information for a field is missing, use null.
    """)
])
fit_ranker_chain = fit_ranker_prompt | structured_llm | StrOutputParser()


email_draft_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You write short, professional, specific cold-outreach emails from prospective PhD students to "
     "professors. Emails must be genuine and specific, never generic or spammy. Keep them under 180 words."),
    ("human", """Write a personalized outreach email from this student to this professor.

    Student profile:
    {profile}

    Professor:
    Name: {professor_name}
    University: {university}
    Research area: {research_area}
    Fit reason: {fit_reason}

    The email should:
    - Have a clear subject line
    - Briefly introduce the student and their relevant background
    - Reference the professor's specific research area (not generic praise)
    - State the student's interest in PhD opportunities in their lab
    - Ask politely whether they are accepting students / open to a brief conversation
    - Close professionally

    Output the subject line and body only, no extra commentary.
    """)
])
email_draft_chain = email_draft_prompt | structured_llm | StrOutputParser()

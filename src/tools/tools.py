from langchain.tools import tool
from dotenv import load_dotenv
import os
from tavily import TavilyClient
from bs4 import BeautifulSoup
from readability import Document
import trafilatura
import re
import requests


load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    raise ValueError("TAVILY_API_KEY environment variable is not set or invalid.")

tavily_client = TavilyClient(api_key=api_key)


@tool
def web_search(query: str) -> str:
    """
    Perform a web search using the Tavily API.

    Args:
        query (str): The search query.

    Returns:
        str: The search results, including titles, URLs, and content snippets.
    """
    try:
        response = tavily_client.search(query, max_results=6)
        results = response.get("results", [])

        out = []
        for r in results:
            out.append(
                f"Title: {r.get('title')}\n"
                f"URL: {r.get('url')}\n"
                f"content: {r.get('content', '')[:400]}\n"
            )

        return "\n".join(out) if out else "No results found."
    except Exception as e:
        return f"An error occurred while performing the web search: {str(e)}"


@tool
def scrape_web(url: str) -> str:
    """
    Scrape the content of a web page using fallback extractors.

    Args:
        url (str): The URL of the web page to scrape.

    Returns:
        str: The scraped content of the web page or an error message.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            return f"Error: The page at {url} was not found (404 Not Found). The link might be broken or outdated."

        response.raise_for_status()

        html = response.text
        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        if extracted and len(extracted.split()) > 100:
            cleaned_text = re.sub(r"\s+", " ", extracted).strip()
            return cleaned_text[:5000]

        doc = Document(html)
        summary = doc.summary()
        soup = BeautifulSoup(summary, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)

        if text and len(text.split()) > 100:
            cleaned_text = re.sub(r"\s+", " ", text).strip()
            return cleaned_text[:5000]

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)

        if text and len(text.split()) > 50:
            cleaned_text = re.sub(r"\s+", " ", text).strip()
            return cleaned_text[:5000]

        return "The content of the page is too short to extract meaningful information."

    except requests.exceptions.Timeout:
        return "The request timed out while trying to access the URL."
    except requests.exceptions.HTTPError as http_err:
        return f"HTTP error occurred: {http_err}"
    except Exception as e:
        return f"An error occurred while scraping the web page: {str(e)}"

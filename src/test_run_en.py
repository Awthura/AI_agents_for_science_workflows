"""English version of test_run.py — translated prompts for better Ollama compatibility."""

import json
from pathlib import Path
from langchain_ollama import ChatOllama
from agents.scraper import run_scraper


def generate_dynamic_queries(base_topic: str, num_queries: int = 3) -> list[str]:
    """Use the LLM to generate specific research niche queries for the given topic."""
    print(f"Generating {num_queries} research niches for: {base_topic}...")

    llm = ChatOllama(model="llama3.2", base_url="http://localhost:11434", format="json")

    prompt = f"""You are an AI researcher. Give me {num_queries} highly specific, current research niches in the field of '{base_topic}'.
Use at most 3 words per niche. Use English terms only (e.g. 'Zero-Shot Learning', 'Swarm Robotics').
Reply ONLY in this exact JSON format:
{{
  "queries": ["niche 1", "niche 2", "niche 3"]
}}"""

    try:
        response = llm.invoke(prompt)
        data = json.loads(response.content)
        raw_queries = data.get("queries", [])

        clean_queries = []
        for item in raw_queries:
            if isinstance(item, dict):
                val = item.get("name") or (list(item.values())[0] if item else "")
                if val:
                    clean_queries.append(str(val))
            elif isinstance(item, str):
                clean_queries.append(item)

        print(f"-> LLM generated: {clean_queries}")
        return clean_queries

    except Exception as e:
        print(f"[!] Query generation failed: {e}")
        return [base_topic]


def main():
    print("Starting web-scraping agent...")

    test_queries = generate_dynamic_queries("Artificial Intelligence", num_queries=3)

    ollama_model = "llama3.2"
    ollama_url = "http://localhost:11434"
    cache_file = Path("temp/conferences.json")

    if not test_queries:
        print("No queries generated. Aborting.")
        return

    try:
        results = run_scraper(
            queries=test_queries,
            model=ollama_model,
            ollama_base_url=ollama_url,
            cache_path=cache_file,
            ttl_days=1,
            months_ahead=24,
            lookup_core=True,
        )

        print(f"\nDone! {len(results)} conference(s) found.")

        for conf in results:
            print("-" * 40)
            print(f"Name:     {conf.name}")
            print(f"Acronym:  {conf.acronym}")
            print(f"Dates:    {conf.dates.start} to {conf.dates.end}")
            print(f"Ranking:  {conf.core_rank}")
            print(f"Location: {conf.location.city if conf.location else 'Unknown'}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")


if __name__ == "__main__":
    main()

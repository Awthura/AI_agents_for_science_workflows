# Questions:

* How do we collect the preferences (survey, extra prompt, …)
* How much variation is in the result (what conferences were recommended)
* How do we rank the conferences (distance, prestige, …)
* XAI —> reasoning


# Research Questions:

* How do different models perform on the WebScraping / Scoring Task
* How does the agent perform with different complex individual preferences?
* (Which model is the most compatible for the task / agent)


# Tools:

* LangGraph or n8n for orchestration
* Ollama for hosting
* Gemma 4 E4B / Llama 4 / kimi-k25 / GPT-OSS
* Firecrawl
* Tavily or something else



# Example JSON-Format:
{
      "id": "ae1747733c85",
      "name": "Cyber-AI 2026",
      "acronym": "IEEE Cybersecurity and AI-Based Systems (Scopus)",
      "year": 2026,
      "url": "http://www.wikicfp.com/cfp/servlet/event.showcfp?eventid=191252&copyownerid=196290",
      "source_url": "wikicfp:Explainable AI",
      "scraped_at": "2026-06-05T14:02:50.849506",
      "dates": {
        "start": "2026-09-22",
        "end": "2026-09-25",
        "submission_deadline": "2026-06-10",
        "notification_date": null,
        "camera_ready_deadline": null
      },
      "location": {
        "city": "Bucharest, Romania",
        "country": "",
        "continent": null,
        "coordinates": null
      },
      "format": "in-person",
      "topics": [
        "Cybersecurity",
        "AI-Based Systems"
      ],
      "description": null,
      "core_rank": "B",
      "decision": null,
      "scores": null
    },
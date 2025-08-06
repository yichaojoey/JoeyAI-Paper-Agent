# AI-Powered ArXiv Paper Agent

This project is an AI-powered agent that automatically fetches, analyzes, and recommends recent research papers from ArXiv. It's designed to help researchers stay up-to-date with the latest advancements in specific fields like Large Language Models, tool use, and function calling.

## Features

-   **Automated Fetching:** Fetches the latest papers from ArXiv based on your defined search queries.
-   **Intelligent Analysis:** Uses the Gemini API to analyze each paper's abstract, determine its relevance, and generate concise summaries.
-   **Witty Summaries:** The agent generates not only the highlights and novelty of a paper but also a "critic's take" - an informal and amusing explanation of why the paper is important.
-   **History Tracking:** Maintains a local JSON file (`sent_papers_history.json`) to keep track of papers that have already been recommended, preventing duplicates.
-   **Email Digests:** Formats the recommended papers into a clean, readable HTML email digest.
-   **Configurable:** Easily customize the search queries, email recipients, API keys, and more.

## How It Works

1.  **Fetch:** The agent queries the ArXiv API for the latest papers based on the search terms defined in the `fetch_arxiv_papers` function.
2.  **Filter:** It filters out papers that have already been recommended by checking against the `sent_papers_history.json` file.
3.  **Analyze:** For each new paper, it sends the title and abstract to the Gemini API. A carefully crafted prompt instructs the model to act as a witty AI research assistant, check for relevance, and generate highlights and a "critic's take".
4.  **Format:** The agent formats the relevant papers into a beautiful HTML email. If no new relevant papers are found, it generates a "Nothing to see here!" email.
5.  **Deliver:** It sends the HTML email to the configured recipient using Gmail's SMTP server.
6.  **Update History:** The IDs and titles of the newly recommended papers are saved to the history file for future runs.

## Setup and Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/yichaojoey/JoeyAI-Paper-Agent.git
cd JoeyAI-Paper-Agent
```

### 2. Install Dependencies

The only external dependency is `requests`.

```bash
pip install requests
```

### 3. Configure Credentials and Settings

You will need to configure the following variables at the top of `paper_agent.py`:

-   **`GEMINI_API_KEY`**: Your API key for the Gemini API. It is highly recommended to use an environment variable for this instead of hardcoding it.
-   **`RECIPIENT_EMAIL`**: The email address where you want to receive the digest.
-   **`SENDER_EMAIL`**: Your Gmail address for sending the email.
-   **`SENDER_PASSWORD`**: Your Gmail "App Password". If you have 2-Factor Authentication enabled on your Google account, you must generate an App Password to allow the script to log in.

### 4. Customize the Agent (Optional)

-   **Search Query:** Modify the `search_query` parameter in the `fetch_arxiv_papers` function to change the topics of interest.
-   **Date Range:** Adjust `DATE_AHEAD` to control how many days back the agent should look for new papers.
-   **Paper Limits:** Change `MAX_PAPER_ANALYZE` and `MAX_PAPER_RECOMMEND` to control how many papers are processed and included in the final email.

## Usage

Once the script is configured, simply run it from your terminal:

```bash
python paper_agent.py
```

The script can be scheduled to run automatically (e.g., using `cron` on macOS/Linux or Task Scheduler on Windows) to provide daily digests.
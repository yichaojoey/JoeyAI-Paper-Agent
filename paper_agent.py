import os
import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from xml.etree import ElementTree
from datetime import date, datetime, timedelta


# --- CONFIGURATION ---
# WARNING: It is not secure to hardcode your API key. Use environment variables instead.
GEMINI_API_KEY = ""
RECIPIENT_EMAIL = "yichaojoey@gmail.com"
HISTORY_FILE = "sent_papers_history.json"
# The model was upgraded to a more powerful one as requested.
GEMINI_MODEL = "gemini-2.5-flash" 

# --- For sending email (optional, requires your email credentials) ---
# To use this, you'll need to generate an "App Password" from your Google Account settings
# if you have 2-Factor Authentication enabled.
SENDER_EMAIL = "yichao.joey.zhou@gmail.com"  # Your Gmail address
SENDER_PASSWORD = "" # Your Gmail App Password

DATE_AHEAD = 4
MAX_PAPER_ANALYZE = 15
MAX_PAPER_RECOMMEND = 5

def load_history():
    """Loads the history of sent papers (ID, title, summary) from the history file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            # Returns a dictionary: {paper_id: {title: "...", summary: "..."}}
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_history(history_data):
    """Saves the updated history of sent papers to the history file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history_data, f, indent=4)

def fetch_arxiv_papers():
    """Fetches recent papers from ArXiv based on search criteria."""
    print("Searching ArXiv for recent papers...")
    base_url = 'http://export.arxiv.org/api/query'
    params = {
        'search_query': 'all:"tool use" OR all:"function calling" OR all:"reinforcement learning" OR all:"agent"',
        'sortBy': 'submittedDate',
        'sortOrder': 'descending',
        'max_results': '50'
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    print("Successfully fetched papers from ArXiv.")
    return response.content

def parse_and_filter_papers(xml_content, sent_paper_ids):
    """Parses ArXiv XML, filters for papers within the last few days, and excludes duplicates."""
    root = ElementTree.fromstring(xml_content)
    entries = []
    namespace = {'arxiv': 'http://www.w3.org/2005/Atom'}
    time_window = datetime.now() - timedelta(days=DATE_AHEAD)
    
    for entry in root.findall('arxiv:entry', namespace):
        paper_id = entry.find('arxiv:id', namespace).text
        if paper_id in sent_paper_ids:
            continue
        
        published_date_str = entry.find('arxiv:published', namespace).text
        published_date = datetime.strptime(published_date_str, "%Y-%m-%dT%H:%M:%SZ")
        if published_date < time_window:
            break
            
        paper_data = {
            'title': entry.find('arxiv:title', namespace).text.strip(),
            'authors': ', '.join(author.find('arxiv:name', namespace).text for author in entry.findall('arxiv:author', namespace)),
            'summary': entry.find('arxiv:summary', namespace).text.strip().replace('\n', ' '),
            'published': published_date,
            'id': paper_id
        }
        entries.append(paper_data)
    
    entries.sort(key=lambda p: p['published'], reverse=True)
    return entries

def analyze_paper_with_history(paper, history):
    """Uses Gemini Pro to analyze a paper in the context of previously sent papers."""
    gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    history_summary = "\n".join([f"- {item['title']}" for item in history.values()])
    if not history_summary:
        history_summary = "None. This is the first paper being analyzed."

    prompt = f"""
    You are an AI research assistant with a sharp eye for detail and a witty, informal tone. Your goal is to help an expert in Language Models stay on the cutting edge of "tool use" and "function calling" research.

    **Previously Recommended Papers (Titles):**
    {history_summary}

    **Candidate Paper to Analyze:**
    - Title: "{paper['title']}"
    - Abstract: "{paper['summary']}"

    **Your Task (in two parts):**

    **Part 1: Relevance Check (Strict!)**
    First, determine if the paper's CORE contribution is about tool use/function calling/reinforcement learning within the LLM/NLP domain. Be aggressive in filtering out papers on robotics, cognitive science, or other areas that are not directly relevant. The topic must be central to the paper.

    **Part 2: Generate Recommendation Content**
    If, and only if, the paper is relevant, generate the content for the recommendation email. Your tone should be smart, insightful, and slightly amusing.

    **Provide your output as a single, valid JSON object with the following four keys:**
    1.  `"is_relevant"`: (boolean) True or false.
    2.  `"highlights_novelty"`: (string) A formal, concise summary of the paper's highlights and key novelty. What are the main takeaways? (Empty string if not relevant).
    3.  `"why_recommend"`: (string) An INFORMAL and AMUSING explanation of why this paper is important. Is it a follow-up to a paper you've recommended before? Does it challenge a common assumption? Is it from a noteworthy lab? Use the history and your own knowledge to make this section insightful and fun to read. Think of it as a "critic's take". (Empty string if not relevant).
    4.  `"relevance_reason"`: (string) A brief, professional justification for your relevance decision.
    """

    payload = {
      "contents": [{"role": "user", "parts": [{"text": prompt}]}],
      "generationConfig": {
        "responseMimeType": "application/json",
        "responseSchema": {
          "type": "OBJECT",
          "properties": {
            "is_relevant": {"type": "BOOLEAN"},
            "highlights_novelty": {"type": "STRING"},
            "why_recommend": {"type": "STRING"},
            "relevance_reason": {"type": "STRING"}
          },
          "required": ["is_relevant", "highlights_novelty", "why_recommend", "relevance_reason"]
        }
      }
    }

    try:
        response = requests.post(gemini_api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        analysis_text = result['candidates'][0]['content']['parts'][0]['text']
        return json.loads(analysis_text)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error with Gemini API: {http_err} - {response.text}")
        return None
    except (KeyError, IndexError, json.JSONDecodeError, Exception) as e:
        print(f"Error processing Gemini response: {e}")
        return None

def format_email_html(papers):
    """Formats the list of papers into a nice HTML string for an email."""
    today_str = date.today().strftime("%B %d, %Y")
    
    if not papers:
        return f"""
        <html><body style="font-family: sans-serif; text-align: center; padding: 40px;">
            <h2 style="color: #333;">ArXiv Digest: {today_str}</h2>
            <p style="color: #666; font-size: 1.1em;">Nothing to see here! No new relevant papers on LLM tool use were found in the past few days. Go enjoy your day!</p>
        </body></html>
        """

    paper_html_parts = []
    for paper in papers:
        published_str = paper['published'].strftime("%B %d, %Y")
        paper_html = f"""
        <div style="margin-bottom: 2.5em; padding: 1.5em; border: 1px solid #e0e0e0; border-radius: 12px; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
            <h3 style="margin: 0 0 0.2em 0; color: #1a237e; font-size: 1.4em;">{paper['title']}</h3>
            <p style="font-size: 0.9em; color: #555; margin: 0 0 1.5em 0;"><b>Published:</b> {published_str} | <b>By:</b> {paper['authors']}</p>
            
            <h4 style="color: #3f51b5; margin-bottom: 0.5em; font-size: 1.1em; border-bottom: 2px solid #e8eaf6; padding-bottom: 0.3em;">Highlights & Novelty</h4>
            <p style="color: #333;">{paper['analysis']['highlights_novelty']}</p>
            
            <div style="background-color: #fffde7; padding: 1em; border-left: 5px solid #ffc107; border-radius: 8px; margin-top: 1.5em;">
                <h4 style="color: #f57f17; margin-top: 0; margin-bottom: 0.5em; font-size: 1.1em;">💡 Why You're Seeing This (The Critic's Take)</h4>
                <p style="color: #4e4e4e; margin: 0; font-style: italic;">{paper['analysis']['why_recommend']}</p>
            </div>
            
            <p style="margin-top: 1.5em; text-align: right;">
                <a href="{paper['id']}" style="color: #303f9f; text-decoration: none; font-weight: bold;">Read the Full Paper on ArXiv &rarr;</a>
            </p>
        </div>
        """
        paper_html_parts.append(paper_html)
        
    all_papers_html = "".join(paper_html_parts)

    return f"""
    <html><head><style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f5f7; margin: 0; padding: 20px; }}
        .container {{ max-width: 800px; margin: auto; background: #f4f5f7; padding: 20px; border-radius: 8px; }}
    </style></head><body><div class="container">
        <h2 style="text-align: center; color: #1a237e; border-bottom: 2px solid #e0e0e0; padding-bottom: 15px; margin-bottom: 25px;">Your ArXiv Digest</h2>
        <p style="text-align: center; color: #555;">Here are the AI critic's picks on LLM tool use from the past few days, sorted by publication date:</p>
        {all_papers_html}
    </div></body></html>
    """

def send_email(html_content):
    """Sends the HTML content as an email using SMTP."""
    if SENDER_EMAIL == "your.email@gmail.com" or SENDER_PASSWORD == "your_app_password":
        print("\n--- EMAIL SENDING SKIPPED ---")
        print("Please edit SENDER_EMAIL and SENDER_PASSWORD in the script to enable email delivery.")
        return

    print(f"Attempting to send email to {RECIPIENT_EMAIL}...")
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"🔬 Your AI-Curated ArXiv Digest - {date.today().strftime('%b %d')}"
    msg['From'] = f"JoeyAI Paper Agent <{SENDER_EMAIL}>"
    msg['To'] = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    """Main function to run the agent."""
    history = load_history()
    print(f"Loaded {len(history)} paper records from history.")
    
    try:
        xml_data = fetch_arxiv_papers()
        candidate_papers = parse_and_filter_papers(xml_data, history.keys())[:MAX_PAPER_ANALYZE]
        
        relevant_papers = []

        print(f"Found {len(candidate_papers)} new candidate papers. Critiquing each one with historical context...")
        if not candidate_papers:
            print("No new papers to analyze.")

        for i, paper in enumerate(candidate_papers):
            print(f"  - Analyzing paper {i+1}/{len(candidate_papers)}: '{paper['title'][:60]}...'")
            analysis = analyze_paper_with_history(paper, history)
            if analysis and analysis.get('is_relevant'):
                paper['analysis'] = analysis
                relevant_papers.append(paper)
        
        print(f"\nFound {len(relevant_papers)} relevant papers to recommend.")
        
        email_body_html = format_email_html(relevant_papers)
        
        print("\n--- GENERATED EMAIL CONTENT PREVIEW ---")
        # To avoid clutter, only show a snippet of the HTML
        print(email_body_html[:1500] + "\n...")
        print("--- END OF EMAIL CONTENT PREVIEW ---\n")
        
        send_email(email_body_html)

        # Update history file with the new papers that were sent
        if relevant_papers:
            for paper in relevant_papers[:MAX_PAPER_RECOMMEND]:
                history[paper['id']] = {'title': paper['title'], 'summary': paper['summary']}
            save_history(history)
            print(f"Updated history file with {len(relevant_papers)} new paper(s). Total history: {len(history)}.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred fetching data from ArXiv: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
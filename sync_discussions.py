import os
import requests
import yaml
from datetime import datetime
import google.generativeai as genai
import re # Import regex for sanitizing filenames

# --- Configuration from Environment Variables ---
# The GH_REPO variable will be automatically set by GitHub Actions if running in the same repo
# Otherwise, you might need to manually set it if discussions are in a different repo
github_repo_env = os.environ.get('GH_REPO')
if github_repo_env is None:
    print("Error: GH_REPO environment variable not set. This script requires the GH_REPO environment variable to be set in the format OWNER/REPOSITORY_NAME.")
    exit(1)
REPO_OWNER, REPO_NAME = github_repo_env.split('/')
GITHUB_TOKEN = os.environ.get('GH_PAT') # MODIFIED: Changed from GITHUB_TOKEN to GH_PAT
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GEMINI_MODEL_NAME = "gemini-1.5-flash" # Recommended for speed and cost-effectiveness
# Consider "gemini-1.5-pro" for higher quality but potentially higher cost/latency

# --- New: Get the specific discussion ID from environment variable ---
# This ID comes from the GitHub Actions event payload
TARGET_DISCUSSION_ID = os.environ.get('GITHUB_DISCUSSION_ID')
if not TARGET_DISCUSSION_ID:
    print("Error: GITHUB_DISCUSSION_ID environment variable not set. This script requires a target discussion ID.")
    # Exit gracefully if the expected environment variable is not found
    exit(1)

# --- Setup Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    # Exit if Gemini API setup fails, as it's critical for the script
    exit(1)

# --- GitHub API Setup ---
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}', # This will now use GH_PAT
    'Content-Type': 'application/json',
}

def get_single_discussion(discussion_node_id):
    """
    Fetches a single GitHub Discussion by its GraphQL Node ID.
    This uses the GitHub GraphQL API to get detailed information about the discussion.
    """
    query = """
    query($nodeId: ID!) {
      node(id: $nodeId) {
        ... on Discussion {
          id
          title
          url
          createdAt
          lastEditedAt
          bodyHTML # Use bodyHTML if you want HTML content to be processed by LLM
                   # Use 'body' if you want raw Markdown
          category {
            name
          }
          author {
            login
          }
          comments(first: 100) { # Fetching first 100 comments
            nodes {
              bodyHTML
              createdAt
              author {
                login
              }
            }
          }
        }
      }
    }
    """
    variables = {"nodeId": discussion_node_id}
    try:
        response = requests.post(GITHUB_GRAPHQL_URL, headers=HEADERS, json={'query': query, 'variables': variables})
        response.raise_for_status() # Raise an exception for HTTP errors
        data = response.json()
        return data['data']['node']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching discussion from GitHub API: {e}")
        return None
    except KeyError:
        print(f"Unexpected response structure from GitHub API for discussion ID: {discussion_node_id}")
        return None


def generate_blog_post_with_gemini(discussion_title, combined_content, discussion_category):
    """
    Uses the Gemini LLM to transform the GitHub Discussion content into a blog post.
    The prompt is crucial here for guiding the LLM's output.
    """
    prompt = f"""
    You are an AI assistant tasked with synthesizing GitHub Discussions and their comments into comprehensive and engaging blog posts for a news site.

    Please take the following GitHub Discussion (which includes the original post and subsequent comments) and transform it into a single, cohesive blog post.
    The goal is to create a well-rounded article that summarizes the entire conversation, including the main points from the initial discussion and key insights or differing opinions from the comments.
    Focus on clarity, conciseness, and making it engaging for a general audience interested in tech news.
    You can expand on points, rephrase for better flow, and summarize lengthy sections.
    Acknowledge differing opinions if they are significant, but generally avoid mentioning specific user names unless critically important for context (and prefer generic attributions like "some users suggested...").
    The output should be *only* the blog post content in Markdown format, ready to be embedded.
    Ensure the generated content is well-structured with appropriate headings and paragraphs.
    Do NOT include YAML front matter.
    Do NOT include any introductory or concluding remarks outside the blog post content itself (e.g., "Here is your blog post:").
    Do NOT include code blocks or triple backticks unless they are essential for the blog post's content.

    GitHub Discussion Title: "{discussion_title}"
    GitHub Discussion Category: "{discussion_category}"

    Full Discussion Content (Original Post and Comments):
    ```
    {combined_content}
    ```

    Please generate the blog post content below:
    """
    print(f"Sending prompt to Gemini for discussion: '{discussion_title}'")
    try:
        # Fetch the response from the Gemini API
        response = model.generate_content(prompt)
        # Check if candidates and content exist before accessing text
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        else:
            print(f"Gemini API returned no content for discussion: '{discussion_title}'")
            return f"**Error: Gemini API returned no content for this discussion.**\n\nOriginal Discussion:\n\n{combined_content}"
    except Exception as e:
        print(f"Error calling Gemini API for discussion '{discussion_title}': {e}")
        return f"**Error: Could not generate content for this discussion using Gemini.**\n\nOriginal Discussion:\n\n{combined_content}"

def sanitize_filename(title):
    """
    Sanitizes a string to be suitable for a filename.
    Removes invalid characters and replaces spaces with hyphens.
    """
    # Replace spaces with hyphens
    s = title.replace(" ", "-")
    # Remove any characters that are not alphanumeric, hyphens, or underscores
    s = re.sub(r'[^\w-]', '', s)
    # Remove multiple consecutive hyphens
    s = re.sub(r'-+', '-', s)
    # Trim hyphens from start/end
    s = s.strip('-')
    return s

def main():
    # Attempt to fetch the target discussion
    discussion = get_single_discussion(TARGET_DISCUSSION_ID)
    if not discussion:
        print(f"Skipping post creation for discussion ID: {TARGET_DISCUSSION_ID} (not found or error during fetch).")
        return # Exit if the discussion couldn't be fetched

    posts_dir = '_posts'
    # Ensure the _posts directory exists
    os.makedirs(posts_dir, exist_ok=True)

    discussion_id = discussion['id']
    title = discussion['title']
    # body = discussion['bodyHTML'] # Old way
    created_at_str = discussion['createdAt']
    category = discussion['category']['name'] if discussion['category'] else "Uncategorized"
    author = discussion['author']['login'] if discussion['author'] else "Unknown Author"
    last_edited_at_str = discussion.get('lastEditedAt', created_at_str) # Use edited date if available

    # --- Construct combined content ---
    original_body = discussion['bodyHTML']
    combined_content = original_body

    if discussion.get('comments') and discussion['comments'].get('nodes'):
        combined_content += "\n\n--- Comments ---" # Add a header for comments section
        for comment in discussion['comments']['nodes']:
            comment_author = comment.get('author').get('login') if comment.get('author') else 'Unknown User'
            comment_date = comment.get('createdAt', 'Unknown Date')
            comment_body = comment.get('bodyHTML', '')
            # Providing author & date for LLM's context; LLM is instructed not to usually mention users.
            combined_content += f"\n\n**Comment by {comment_author} on {comment_date}:**\n{comment_body}"

    # Format the date for the filename
    filename_date = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
    # Sanitize the title for use in the filename
    sanitized_title = sanitize_filename(title)
    if not sanitized_title: # Fallback if sanitization results in an empty string
        sanitized_title = f"discussion-{discussion_id[:8]}"

    # Construct the full filepath for the Jekyll post
    filepath = os.path.join(posts_dir, f"{filename_date}-{sanitized_title}.md")

    print(f"Processing discussion: '{title}' (ID: {discussion_id}) with comments.")

    # Call Gemini for content generation with combined content
    blog_content = generate_blog_post_with_gemini(title, combined_content, category)

    # Format dates for Jekyll front matter
    jekyll_created_date = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S %z')
    jekyll_edited_date = datetime.strptime(last_edited_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S %z')


    # Prepare Jekyll front matter
    front_matter = {
        'layout': 'post', # Assuming you have a 'post' layout in your Jekyll theme
        'title': title,
        'date': jekyll_created_date,
        'categories': [category], # Using the discussion category as a Jekyll category
        'author': author,
        'github_discussion_url': discussion['url'],
        'github_discussion_id': discussion_id,
        'github_last_edited_at': jekyll_edited_date, # Useful for idempotency checks or display
        'llm_processed': True # Flag to indicate LLM processing
    }

    # Write the Jekyll post file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            # Dump the front matter into YAML format
            yaml.dump(front_matter, f, allow_unicode=True, default_flow_style=False)
            f.write('---\n\n')
            f.write(blog_content) # Write the LLM-generated content
        print(f"Successfully generated/updated post: {filepath}")
    except IOError as e:
        print(f"Error writing post file '{filepath}': {e}")
        exit(1)


if __name__ == '__main__':
    main()

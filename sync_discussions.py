import os
import requests
import yaml
from datetime import datetime
import google.generativeai as genai
import re # Import regex for sanitizing filenames

# --- Konfiguracja ze zmiennych środowiskowych ---
REPO_OWNER = 'marakujan'
REPO_NAME = 'siedem.it'

GITHUB_TOKEN = os.environ.get('GH_PAT')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
# ZMIANA: Model Gemini ustawiony na gemini-2.5-flash
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# --- Pobierz ID konkretnej dyskusji ze zmiennej środowiskowej ---
TARGET_DISCUSSION_ID = os.environ.get('GITHUB_DISCUSSION_ID')
if not TARGET_DISCUSSION_ID:
    print("Błąd: Zmienna środowiskowa GITHUB_DISCUSSION_ID nie jest ustawiona. Ten skrypt wymaga docelowego identyfikatora dyskusji.")
    exit(1)

# --- Konfiguracja Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)
except Exception as e:
    print(f"Błąd konfiguracji API Gemini: {e}")
    exit(1)

# --- Konfiguracja API GitHub ---
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Content-Type': 'application/json',
}

def get_single_discussion(discussion_node_id):
    """
    Pobiera pojedynczą Dyskusję GitHub za pomocą jej ID węzła GraphQL.
    Wykorzystuje API GraphQL GitHub, aby uzyskać szczegółowe informacje o dyskusji.
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
          bodyHTML
          category {
            name
          }
          author {
            login
          }
          comments(first: 100) {
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
        response.raise_for_status() # Wyrzuć wyjątek dla błędów HTTP
        data = response.json()
        return data.get('data', {}).get('node')
    except requests.exceptions.RequestException as e:
        print(f"Błąd podczas pobierania dyskusji z API GitHub: {e}")
        return None
    except KeyError:
        print(f"Nieoczekiwana struktura odpowiedzi z API GitHub dla ID dyskusji: {discussion_node_id}")
        return None


def generate_blog_post_with_gemini(discussion_title, combined_content, discussion_category):
    """
    Używa modelu Gemini LLM do przekształcenia treści Dyskusji GitHub w post blogowy.
    Prompt jest kluczowy do pokierowania wyjściem LLM.
    """
    # ZMIANA: Prompt w języku polskim
    prompt = f"""
Jesteś asystentem AI, którego zadaniem jest synteza dyskusji na GitHubie i ich komentarzy w kompleksowe i angażujące posty blogowe dla serwisu informacyjnego.

Proszę, weź pod uwagę poniższą Dyskusję GitHub (która zawiera oryginalny post i kolejne komentarze) i przekształć ją w jeden spójny post blogowy.
Celem jest stworzenie kompletnego artykułu, który podsumowuje całą rozmowę, włączając w to główne punkty z początkowej dyskusji oraz kluczowe spostrzeżenia lub odmienne opinie z komentarzy.
Skoncentruj się na jasności, zwięzłości i angażowaniu szerokiej publiczności zainteresowanej wiadomościami technologicznymi.
Możesz rozwijać punkty, przeformułowywać dla lepszego przepływu i streszczać długie sekcje.
Uznaj odmienne opinie, jeśli są znaczące, ale generalnie unikaj wspominania konkretnych nazw użytkowników.
Wynik powinien zawierać *wyłącznie* treść postu blogowego w formacie Markdown, gotową do osadzenia.
Upewnij się, że wygenerowana treść jest dobrze ustrukturyzowana z odpowiednimi nagłówkami i akapitami.
NIE dołączaj front matter w formacie YAML.
NIE dołączaj żadnych wstępnych ani końcowych uwag poza samą treścią postu blogowego (np. "Oto Twój post blogowy:").
NIE dołączaj bloków kodu ani potrójnych backticków, chyba że są one niezbędne dla treści postu blogowego.
NIE dołączaj tytułu H1, ponieważ tytuł już jest przypisany, twoim zadaniem jest rozpoczęcie artykułu od pierwszego akapitu do końca.

Tytuł Dyskusji GitHub: \"{discussion_title}\"
Kategoria Dyskusji GitHub: \"{discussion_category}\"

Pełna treść dyskusji (oryginalny post i komentarze):

{combined_content}


Proszę wygeneruj treść postu blogowego poniżej:
"""
    print(f"Wysyłam prompt do Gemini dla dyskusji: '{discussion_title}'")
    try:
        response = model.generate_content(prompt)
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        else:
            print(f"API Gemini nie zwróciło żadnej treści dla dyskusji: '{discussion_title}'")
            return f"**Błąd: API Gemini nie zwróciło żadnej treści dla tej dyskusji.**\n\nOryginalna Dyskusja:\n\n{combined_content}"
    except Exception as e:
        print(f"Błąd podczas wywoływania API Gemini dla dyskusji '{discussion_title}': {e}")
        return f"**Błąd: Nie udało się wygenerować treści dla tej dyskusji za pomocą Gemini.**\n\nOryginalna Dyskusja:\n\n{combined_content}"

def sanitize_filename(title):
    """
    Sanityzuje ciąg znaków, aby nadawał się na nazwę pliku.
    """
    s = title.replace(" ", "-")
    s = re.sub(r'[^\w-]', '', s)
    s = re.sub(r'-+', '-', s)
    s = s.strip('-')
    return s

def main():
    discussion = get_single_discussion(TARGET_DISCUSSION_ID)
    if not discussion:
        print(f"Pomijam tworzenie postu dla ID dyskusji: {TARGET_DISCUSSION_ID} (nie znaleziono lub błąd podczas pobierania).")
        return

    posts_dir = '_posts'
    os.makedirs(posts_dir, exist_ok=True)

    discussion_id = discussion['id']
    title = discussion['title']
    created_at_str = discussion['createdAt']
    category = discussion['category']['name'] if discussion.get('category') else "Uncategorized"
    author = discussion['author']['login'] if discussion.get('author') else "Unknown Author"

    last_edited_at_str = discussion.get('lastEditedAt') or created_at_str

    # --- Zbuduj połączoną treść ---
    original_body = discussion['bodyHTML']
    combined_content = original_body

    if discussion.get('comments') and discussion['comments'].get('nodes'):
        # ZMIANA: nagłówek sekcji komentarzy w języku angielskim
        combined_content += "\n\n--- Comments ---\n"
        for comment in discussion['comments']['nodes']:
            comment_author = comment.get('author', {}).get('login') or 'Unknown User'
            comment_date = comment.get('createdAt', 'Unknown Date')
            comment_body = comment.get('bodyHTML', '')
            # ZMIANA: Format komentarza w języku angielskim
            combined_content += f"\n**Comment by {comment_author} on {comment_date}:**\n{comment_body}"

    filename_date = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d')
    sanitized_title = sanitize_filename(title)
    if not sanitized_title:
        sanitized_title = f"discussion-{discussion_id[:8]}"

    filepath = os.path.join(posts_dir, f"{filename_date}-{sanitized_title}.md")

    print(f"Przetwarzam dyskusję: '{title}' (ID: {discussion_id}) wraz z komentarzami.")

    blog_content = generate_blog_post_with_gemini(title, combined_content, category)

    jekyll_created_date = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S %z')
    jekyll_edited_date = datetime.strptime(last_edited_at_str, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%d %H:%M:%S %z')

    front_matter = {
        'layout': 'post',
        'title': title,
        'date': jekyll_created_date,
        'categories': [category.lower()],
        'author': author,
        'github_discussion_url': discussion['url'],
        'github_discussion_id': discussion_id,
        'github_last_edited_at': jekyll_edited_date,
        'llm_processed': True
    }

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            yaml.dump(front_matter, f, allow_unicode=True, default_flow_style=False)
            f.write('---\n\n')
            f.write(blog_content)
        print(f"Pomyślnie wygenerowano/zaktualizowano post: {filepath}")
    except IOError as e:
        print(f"Błąd zapisu pliku postu '{filepath}': {e}")
        exit(1)


if __name__ == '__main__':
    main()

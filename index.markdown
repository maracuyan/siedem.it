---
layout: home
list_title: "Posty" # This might be overridden or ignored by the new content below
---

# Witaj w świecie technologii siedem.it!

Odkryj najnowsze trendy, recenzje i tutoriale ze świata Apple, Microsoft, Google, AI i gadżetów.
Zapraszamy do lektury i dyskusji!

## Najnowsze artykuły

{% if site.posts.size > 0 %}
  <ul class="post-list">
    {% for post in site.posts limit:5 %}
      <li>
        <h3>
          <a class="post-link" href="{{ post.url | relative_url }}">
            {{ post.title | escape }}
          </a>
        </h3>
        <span class="post-meta">{{ post.date | date: "%b %-d, %Y" }}</span>
        {{ post.excerpt }}
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>Brak dostępnych postów. Wkrótce pojawią się tu nowe treści!</p>
{% endif %}

<p class="rss-subscribe">Subskrybuj <a href="{{ "/feed.xml" | relative_url }}">via RSS</a></p>

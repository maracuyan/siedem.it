---
layout: home
list_title: "Posty" # This might be overridden or ignored by the new content below
---

<div class="welcome-section">
# Twoja codzienna dawka innowacji

Od głębokich analiz AI po praktyczne recenzje sprzętu – tutaj znajdziesz wiedzę, która napędza postęp.

[Zobacz Najnowsze Artykuły](#najnowsze-artykuly){: .cta-button}
</div>

## Najnowsze artykuły

{% if site.posts.size > 0 %}
  <ul class="post-list">
    {% for post in site.posts limit:5 %}
      <li>
        <a href="{{ post.url | relative_url }}" class="post-card-link">
          {% if post.thumbnail %}
            <div class="post-card-thumbnail">
              <img src="{{ post.thumbnail | relative_url }}" alt="Miniatura dla {{ post.title | escape }}">
            </div>
          {% endif %}
          <div class="post-card-content">
            <h3>
              {{ post.title | escape }}
            </h3>
            <span class="post-meta">{{ post.date | date: site.minima.date_format | default: "%b %-d, %Y" }}</span>
            <div class="post-excerpt">
              {{ post.excerpt }}
            </div>
          </div>
        </a>
      </li>
    {% endfor %}
  </ul>
{% else %}
  <p>Brak dostępnych postów. Wkrótce pojawią się tu nowe treści!</p>
{% endif %}

<p class="rss-subscribe">Subskrybuj <a href="{{ "/feed.xml" | relative_url }}">via RSS</a></p>

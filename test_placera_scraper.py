#!/usr/bin/env python3
"""
Test script for Placera forum scraper
"""

from bs4 import BeautifulSoup

# Test HTML from Placera forum
placera_html = """<div data-v-9d46de69="" class="post-list mt-6 mx-0">
<article data-v-9b6ecc75="" data-v-9d46de69="" class="post-card card mb-post-spacing last-of-type:mb-0" reply-limit="5">
<section data-v-9b6ecc75="">
<div data-v-9b6ecc75="" class="flex justify-between">
<div class="flex min-w-0 overflow-hidden">
<a href="/medlem/cash-is-king" class="shrink-0">
<div class="rounded-full flex justify-center items-center font-semibold shrink-0 border-surface-secondary dark:border-surface-secondary-dark capitalize text-avatar-member-text dark:text-avatar-member-text-dark" style="height: 32px; width: 32px; font-size: 12px; border-width: 0px; background: rgb(63, 38, 135);">C</div>
</a>
<div class="flex flex-col px-4 justify-center overflow-hidden text-surface-contrast dark:text-surface-contrast-dark">
<div class="text-app-specific-author-name flex items-center flex-wrap leading-tight pt-post-author">
<a href="/medlem/cash-is-king" class="whitespace-nowrap text-ellipsis overflow-hidden" data-testid="author-name">
<div class="flex items-center">
<div class="whitespace-nowrap flex items-center text-surface-contrast dark:text-surface-contrast-dark"> Cash is king</div>
</div>
</a>
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="inline-block text-surface-contrast dark:text-surface-contrast-dark mx-1" style="height: 16px; width: 16px;">
<path fill-rule="evenodd" clip-rule="evenodd" d="M8.63627 5.23431C8.32385 5.54673 8.32385 6.05327 8.63627 6.36569L14.0706 11.8L8.63627 17.2343C8.32385 17.5467 8.32385 18.0533 8.63627 18.3657C8.94869 18.6781 9.45522 18.6781 9.76764 18.3657L15.7676 12.3657C16.0801 12.0533 16.0801 11.5467 15.7676 11.2343L9.76764 5.23431C9.45522 4.9219 8.94869 4.9219 8.63627 5.23431Z" fill="currentColor"></path>
</svg>
<a href="/bolag/volvo-car" class="text-surface-contrast dark:text-surface-contrast-dark whitespace-nowrap text-ellipsis overflow-hidden" data-testid="destination-label">Volvo Car</a>
</div>
<p class="text-regular-m text-surface-bold dark:text-surface-bold-dark">
<span style="touch-action: pan-y; user-select: none; -webkit-user-drag: none; -webkit-tap-highlight-color: rgba(0, 0, 0, 0);">för 1 minut sedan</span>
</p>
</div>
</div>
</div>
<div data-v-9b6ecc75="">
<h3 data-v-9b6ecc75="" class="leading-normal text-heading6 text-surface-contrast mt-4">Över 97 % av alla ägare är kvar på 1 år</h3>
<div data-v-cae1beef="" data-v-9b6ecc75="" class="mt-2">
<div data-v-cae1beef="" class="box" style="height: 189px;">
<div data-v-9b6ecc75="" class="post-body">Det är inte alla som klarar av blankare som manipulerar kurser, knappt 3% har sålt på ett år och många försöker göra allt här för att skrämma folk för att sälja för att komma in billigare. <br>Jag ser detta som att vändningen för Volvo car kommer när som helst. <br>Ser också att det är fler fonder som har kommit in👍 <br>Detta kommer bli enkla siffror att slå när allt är igång. Tror även på en stark försäljningsökning redan nu i Kina då xc70 kommer göra succé. <br>Ex60 och ny fabrik nästa år i Slovakien. <br>Tänk att vi jämför i mot ett rekord år 2024 som var det bästa på nästan 100 år. Kommer bli kanon på långsiktigt detta och passar på att öka mera på dessa nivåer.</div>
</div>
</div>
</div>
</section>
</article>
</div>"""

# Test HTML for Placera sidebar
placera_sidebar_html = """<div class="bg-surface-primary dark:bg-surface-primary-dark rounded-lg p-4">
<h3 class="text-heading5 text-surface-contrast dark:text-surface-contrast-dark mb-4">Populära inlägg</h3>
<div class="space-y-3">
<a href="/inlagg/12345" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Tesla kursutveckling 2024</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">42 kommentarer</p>
</a>
<a href="/inlagg/67890" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Volvo Car analys</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">28 kommentarer</p>
</a>
</div>
</div>

<div class="bg-surface-primary dark:bg-surface-primary-dark rounded-lg p-4 mt-4">
<h3 class="text-heading5 text-surface-contrast dark:text-surface-contrast-dark mb-4">Populära bolag</h3>
<div class="space-y-3">
<a href="/bolag/tesla" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Tesla</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">1,234 följare</p>
</a>
<a href="/bolag/volvo-car" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Volvo Car</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">856 följare</p>
</a>
</div>
</div>

<div class="bg-surface-primary dark:bg-surface-primary-dark rounded-lg p-4 mt-4">
<h3 class="text-heading5 text-surface-contrast dark:text-surface-contrast-dark mb-4">Grupper</h3>
<div class="space-y-3">
<a href="/grupp/tech-investors" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Tech Investors</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">567 medlemmar</p>
</a>
<a href="/grupp/swedish-stocks" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Swedish Stocks</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">1,234 medlemmar</p>
</a>
</div>
</div>

<div class="bg-surface-primary dark:bg-surface-primary-dark rounded-lg p-4 mt-4">
<h3 class="text-heading5 text-surface-contrast dark:text-surface-contrast-dark mb-4">Mest följda</h3>
<div class="space-y-3">
<a href="/medlem/investor-pro" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Investor Pro</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">2,345 följare</p>
</a>
<a href="/medlem/stock-analyst" class="block">
<h4 class="text-regular-m text-surface-contrast dark:text-surface-contrast-dark hover:text-primary-80 transition-colors">Stock Analyst</h4>
<p class="text-small text-surface-contrast/70 dark:text-surface-contrast-dark/70">1,876 följare</p>
</a>
</div>
</div>"""


def test_placera_parsing():
    """Test parsing Placera forum HTML"""
    soup = BeautifulSoup(placera_html, "html.parser")

    # Find all posts
    posts = soup.find_all("article", class_="post-card")
    print(f"Found {len(posts)} posts")

    for i, post in enumerate(posts):
        # Extract author
        author_elem = post.find("a", {"data-testid": "author-name"})
        author = author_elem.get_text(strip=True) if author_elem else "Unknown"

        # Extract ticker/company
        ticker_elem = post.find("a", {"data-testid": "destination-label"})
        ticker = ticker_elem.get_text(strip=True) if ticker_elem else "Unknown"

        # Extract title
        title_elem = post.find("h3")
        title = title_elem.get_text(strip=True) if title_elem else "No title"

        # Extract content
        content_elem = post.find("div", class_="post-body")
        content = content_elem.get_text(strip=True) if content_elem else "No content"

        # Extract timestamp
        time_elem = post.find("span")
        timestamp = time_elem.get_text(strip=True) if time_elem else "Unknown time"

        print(f"\nPost {i+1}:")
        print(f"  Author: {author}")
        print(f"  Ticker: {ticker}")
        print(f"  Title: {title[:50]}...")
        print(f"  Content: {content[:100]}...")
        print(f"  Time: {timestamp}")


def test_sidebar_extraction():
    """Test parsing Placera sidebar HTML"""
    soup = BeautifulSoup(placera_sidebar_html, "html.parser")

    # Extract popular posts
    popular_posts_section = soup.find(
        "h3", string=lambda text: text and "Populära inlägg" in text
    )
    if popular_posts_section:
        container = popular_posts_section.find_parent(
            "div", class_=lambda x: x and "bg-surface-primary" in x
        )
        if container:
            post_links = container.find_all(
                "a", href=lambda href: href and "/inlagg/" in href
            )
            print(f"\nFound {len(post_links)} popular posts:")
            for link in post_links:
                title_elem = link.find("h4")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    comment_text = link.get_text()
                    import re

                    comment_match = re.search(r"(\d+)", comment_text)
                    comment_count = comment_match.group(1) if comment_match else "0"
                    print(f"  - {title} ({comment_count} comments)")

    # Extract popular companies
    popular_companies_section = soup.find(
        "h3", string=lambda text: text and "Populära bolag" in text
    )
    if popular_companies_section:
        container = popular_companies_section.find_parent(
            "div", class_=lambda x: x and "bg-surface-primary" in x
        )
        if container:
            company_links = container.find_all(
                "a", href=lambda href: href and "/bolag/" in href
            )
            print(f"\nFound {len(company_links)} popular companies:")
            for link in company_links:
                name_elem = link.find("h4")
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    follower_text = link.get_text()
                    import re

                    follower_match = re.search(r"(\d+)", follower_text)
                    follower_count = follower_match.group(1) if follower_match else "0"
                    print(f"  - {name} ({follower_count} followers)")


if __name__ == "__main__":
    print("=== Testing Placera Forum ===")
    test_placera_parsing()

    print("\n=== Testing Sidebar Extraction ===")
    test_sidebar_extraction()

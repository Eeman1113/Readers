"""
Readers — Report Generator
Generates a single-file HTML report with shadcn-inspired design,
clean black & white UI, and colorful high-quality charts.
"""

from datetime import datetime
from pathlib import Path
import json
import math  # gauge
import html as html_lib


def _esc(text):
    """Escape HTML entities in user-generated content."""
    if not text:
        return ""
    return html_lib.escape(str(text))


def _generate_recommendations(stats: dict) -> list:
    """Analyze simulation data and generate actionable author recommendations."""
    recs = []
    avg = stats.get("avg_rating", 0)
    dnf_rate = stats.get("dnf_rate", 0)
    vs = stats.get("virality_score", 0)
    emotions = stats.get("emotions", {})
    controversies = stats.get("controversies", [])
    dnf_reasons = stats.get("dnf_reasons", [])
    platform_avg = stats.get("platform_avg_ratings", {})
    dist = stats.get("rating_distribution", {})
    timeline = stats.get("round_timeline", [])

    if avg >= 4.0:
        recs.append(("strong", "Strong Premise", "Your concept resonates broadly. Focus on execution quality — the idea is validated.", "positive"))
    elif avg >= 3.0:
        recs.append(("split", "Polarizing Concept", "Your book splits opinion — that's not bad. Polarizing books often build passionate fanbases. Lean into what makes it divisive.", "neutral"))
    else:
        recs.append(("refine", "Concept Needs Refinement", "The premise isn't landing with most readers. Consider revising your hook, blurb, or core pitch before investing in a full manuscript.", "warning"))

    if dnf_rate > 25:
        if dnf_reasons:
            reason_counts = {}
            for r in dnf_reasons:
                reason_counts[r] = reason_counts.get(r, 0) + 1
            top_reason = max(reason_counts, key=reason_counts.get)
            recs.append(("dnf", f"High DNF Risk ({dnf_rate:.0f}%)", f"Over a quarter of readers would quit. Top reason: \"{top_reason}\". Address this in your opening chapters or blurb positioning.", "warning"))
        else:
            recs.append(("dnf", f"High DNF Risk ({dnf_rate:.0f}%)", "Over a quarter of readers would quit. Strengthen your opening hook and first 3 chapters.", "warning"))
    elif dnf_rate > 10:
        recs.append(("dnf-mod", f"Moderate DNF Rate ({dnf_rate:.0f}%)", "Some readers would quit — that's normal. Check the DNF reasons above for specific friction points to address.", "neutral"))
    else:
        recs.append(("dnf-low", f"Low DNF Rate ({dnf_rate:.0f}%)", "Most readers would stick with your book. Your hook is working.", "positive"))

    if len(controversies) >= 10:
        recs.append(("controversy", "Controversy Is Your Superpower", f"{len(controversies)} debate points detected. Controversial books get talked about. Use these friction points in your marketing.", "positive"))
    elif len(controversies) >= 3:
        recs.append(("debate", "Some Debate Potential", f"{len(controversies)} controversy points could fuel organic discussion. Consider leaning into these angles in your book club guide or social media strategy.", "neutral"))

    if platform_avg:
        best_plat = max(platform_avg, key=platform_avg.get)
        worst_plat = min(platform_avg, key=platform_avg.get)
        best_avg = platform_avg[best_plat]
        worst_avg = platform_avg[worst_plat]
        plat_labels = {"BookTok": "BookTok/TikTok", "Goodreads": "Goodreads", "Reddit": "Reddit",
                       "Bookstagram": "Bookstagram/Instagram", "X_Twitter": "X/Twitter", "Lurker": "silent readers"}
        if best_avg - worst_avg > 0.8:
            recs.append(("target", f"Target {plat_labels.get(best_plat, best_plat)}", f"Your strongest audience is on {plat_labels.get(best_plat, best_plat)} ({best_avg:.1f}). Focus your launch marketing there. {plat_labels.get(worst_plat, worst_plat)} rated you lowest ({worst_avg:.1f}) — consider adjusting your pitch for that audience.", "positive"))

    if emotions:
        top_emotion = max(emotions, key=emotions.get)
        top_count = emotions[top_emotion]
        total = sum(emotions.values())
        pct = top_count / total * 100 if total else 0
        if top_emotion in ("excited", "obsessed", "moved"):
            recs.append(("emotion", f"Strong Emotional Hook ({top_emotion.title()}, {pct:.0f}%)", "Your book triggers strong positive emotions. Use reader quotes from this simulation in your marketing materials and blurb.", "positive"))
        elif top_emotion in ("intrigued",):
            recs.append(("curious", f"Curiosity-Driven ({top_emotion.title()}, {pct:.0f}%)", "Readers are curious but not yet hooked. Your premise creates intrigue — make sure your sample chapters deliver on that promise.", "neutral"))
        elif top_emotion in ("bored", "meh", "disappointed"):
            recs.append(("gap", f"Engagement Gap ({top_emotion.title()}, {pct:.0f}%)", "The dominant reaction is disengagement. Consider raising the stakes earlier, adding a stronger hook, or making your unique angle more prominent.", "warning"))
        elif top_emotion in ("uncomfortable", "angry"):
            recs.append(("strong-neg", f"Strong Negative Reaction ({top_emotion.title()}, {pct:.0f}%)", "Your book provokes strong feelings — which can be powerful for dark/literary fiction. Ensure your content warnings are clear.", "neutral"))

    if vs >= 70:
        recs.append(("viral", "High Viral Potential", "This concept could blow up on social media. Prepare a launch strategy with ARCs for influencers and hashtag campaigns.", "positive"))
    elif vs >= 40:
        recs.append(("buzz", "Moderate Buzz Potential", "Your book could generate organic conversation. Create shareable content around your most controversial or emotional angles.", "neutral"))
    else:
        recs.append(("niche", "Niche Appeal", "This book may not go viral organically, but many bestsellers start niche. Focus on targeted marketing to your core readers.", "neutral"))

    high_ratings = dist.get(4, 0) + dist.get(5, 0) + dist.get('4', 0) + dist.get('5', 0)
    low_ratings = dist.get(1, 0) + dist.get(2, 0) + dist.get('1', 0) + dist.get('2', 0)
    total_dist = sum(v for v in dist.values() if isinstance(v, (int, float)))
    if total_dist > 0 and high_ratings > total_dist * 0.3 and low_ratings > total_dist * 0.2:
        recs.append(("polarize", "Love-It-or-Hate-It Dynamic", f"{high_ratings} readers rated 4-5 while {low_ratings} rated 1-2. Polarizing books often outperform 'safe' ones commercially.", "positive"))

    if len(timeline) >= 3:
        r1_avg = timeline[0].get("avg_rating")
        last_avg = None
        for t in reversed(timeline):
            if t.get("avg_rating") is not None:
                last_avg = t["avg_rating"]
                break
        if r1_avg and last_avg:
            if last_avg < r1_avg - 0.3:
                recs.append(("decline", "Social Sentiment Declining", f"Ratings dropped from {r1_avg:.1f} to {last_avg:.1f} as readers discussed. Strengthen your weakest elements before critics amplify them.", "warning"))
            elif last_avg > r1_avg + 0.3:
                recs.append(("rise", "Social Proof Boosting Ratings", f"Ratings rose from {r1_avg:.1f} to {last_avg:.1f} as readers talked. Invest in book club outreach and reader communities.", "positive"))

    demo = stats.get("demographic_breakdown", {})
    if demo:
        best_seg = max(demo.items(), key=lambda x: x[1].get("avg_rating", 0))
        worst_seg = min(demo.items(), key=lambda x: x[1].get("avg_rating", 5))
        if best_seg[1]["avg_rating"] - worst_seg[1]["avg_rating"] > 0.5:
            recs.append(("demo-best", f"Target: {best_seg[0]}", f"Your strongest demographic is {best_seg[0]} ({best_seg[1]['avg_rating']:.1f}, {best_seg[1]['purchase_rate']:.0f}% buy rate). Focus marketing here.", "positive"))
            recs.append(("demo-worst", f"Weak With: {worst_seg[0]}", f"{worst_seg[0]} rated you {worst_seg[1]['avg_rating']:.1f} with {worst_seg[1]['dnf_rate']:.0f}% DNF. Adjust your pitch or deprioritize.", "warning"))

    purchase_rate = stats.get("purchase_rate", 0)
    avg_price = stats.get("avg_price_willing", 0)
    if purchase_rate > 0:
        if purchase_rate >= 60:
            recs.append(("buy-high", f"Strong Purchase Intent ({purchase_rate:.0f}%)", f"{purchase_rate:.0f}% would buy at ~${avg_price:.2f}. Commercially viable. Price at ${avg_price:.0f} or test higher.", "positive"))
        elif purchase_rate >= 30:
            recs.append(("buy-mod", f"Moderate Purchase Intent ({purchase_rate:.0f}%)", f"{purchase_rate:.0f}% would buy at ~${avg_price:.2f}. Strengthen your hook and consider lower pricing or KU.", "neutral"))
        else:
            recs.append(("buy-low", f"Low Purchase Intent ({purchase_rate:.0f}%)", f"Only {purchase_rate:.0f}% would buy. Improve the premise, cover, and blurb before investing in marketing.", "warning"))

    consensus = stats.get("consensus_score", 0)
    if consensus >= 70:
        recs.append(("consensus", f"High Reader Consensus ({consensus:.0f}%)", "Readers mostly agree. The rating prediction is reliable for decision-making.", "positive"))
    elif consensus < 40:
        recs.append(("divided", f"Low Consensus ({consensus:.0f}%)", "Readers are all over the map. Divisive concepts can be a strength for marketing but makes prediction less certain.", "neutral"))

    return recs


def generate_report(stats: dict, book_description: str, output_path: Path, provider_name: str) -> Path:
    """Generate the premium HTML report with shadcn-inspired design."""

    avg = stats.get("avg_rating", 0)
    full_stars = int(avg)
    half = 1 if (avg - full_stars) >= 0.25 else 0
    empty = 5 - full_stars - half
    stars_html = '<span class="star-filled">&#9733;</span>' * full_stars
    if half:
        stars_html += '<span class="star-half">&#9733;</span>'
    stars_html += '<span class="star-empty">&#9734;</span>' * empty

    total_readers = stats.get("total_readers", 1)
    total_rounds = stats.get("total_rounds", 1)
    dnf_rate = stats.get("dnf_rate", 0)
    dnf_count = stats.get("dnf_count", 0)
    vs = stats.get("virality_score", 0)
    n_controversies = len(stats.get("controversies", []))
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    # --- SECTION NUMBERING ---
    sec_num = 0

    def next_sec():
        nonlocal sec_num
        sec_num += 1
        return f"{sec_num:02d}"

    # --- RATING DISTRIBUTION ---
    dist = stats.get("rating_distribution", {})
    max_count = max(dist.values()) if dist.values() else 1
    bar_colors = ["#dc2626", "#f97316", "#eab308", "#22c55e", "#2563eb"]

    dist_rows = ""
    for star in range(5, 0, -1):
        count = dist.get(star, 0)
        pct = count / max(total_readers, 1) * 100
        bar_width = count / max_count * 100 if max_count > 0 else 0
        color = bar_colors[star - 1]
        dist_rows += f'''
        <div class="dist-row">
            <span class="dist-label">{star}</span>
            <div class="dist-track"><div class="dist-bar" style="--bar-color:{color}" data-target-width="{bar_width}%"></div></div>
            <span class="dist-count">{count}<span class="dist-pct">{pct:.0f}%</span></span>
        </div>'''

    # --- EMOTION CHIPS ---
    emotion_colors = {
        "excited": "#f97316", "bored": "#71717a", "angry": "#dc2626",
        "moved": "#7c3aed", "confused": "#eab308", "meh": "#a1a1aa",
        "obsessed": "#ec4899", "disappointed": "#6b7280", "intrigued": "#2563eb",
        "uncomfortable": "#ea580c", "unknown": "#71717a"
    }
    emotion_chips = ""
    for emotion, count in sorted(stats.get("emotions", {}).items(), key=lambda x: -x[1]):
        color = emotion_colors.get(emotion, "#71717a")
        pct = count / max(total_readers, 1) * 100
        emotion_chips += f'<div class="chip" style="--chip-color:{color}"><span class="chip-dot" style="background:{color}"></span>{emotion}<span class="chip-count">{count} ({pct:.0f}%)</span></div>'

    # --- PLATFORM CARDS ---
    plat_meta = {
        "BookTok": ("#ec4899", "BookTok"),
        "Goodreads": ("#b45309", "Goodreads"),
        "Reddit": ("#ea580c", "Reddit"),
        "Bookstagram": ("#c026d3", "Bookstagram"),
        "X_Twitter": ("#0ea5e9", "X / Twitter"),
        "Lurker": ("#6b7280", "Lurkers")
    }

    platform_cards = ""
    for plat, avg_r in sorted(stats.get("platform_avg_ratings", {}).items(), key=lambda x: -x[1]):
        color, display = plat_meta.get(plat, ("#6b7280", plat))
        posts = stats.get("platform_posts", {}).get(plat, [])[:3]
        posts_html = ""
        for sp in posts:
            r = sp.get('rating', 3)
            posts_html += f'''<div class="plat-post">
                <div class="plat-post-head"><span class="plat-post-name">{_esc(sp.get('name',''))}</span><span class="plat-post-rating">{'&#9733;' * round(r)} {r}</span></div>
                <div class="plat-post-text">{_esc(sp.get('post',''))}</div></div>'''
        platform_cards += f'''<div class="plat-card">
            <div class="plat-accent" style="background:{color}"></div>
            <div class="plat-header">
                <div><div class="plat-name">{display}</div><div class="plat-readers" style="color:{color}">{avg_r:.1f} avg</div></div>
            </div>{posts_html}</div>'''

    # --- SOCIAL FEED ---
    all_posts = []
    for plat, posts in stats.get("platform_posts", {}).items():
        for p in posts:
            p["platform"] = plat
            all_posts.append(p)
    all_posts.sort(key=lambda x: (
        {"macro": 3, "mid": 2, "micro": 1}.get(x.get("influence", ""), 0)
        + abs(x.get("rating", 3) - 3)
        + (1 if len(x.get("post", "")) > 80 else 0)
    ), reverse=True)

    feed_visible = ""
    feed_hidden = ""
    for idx, post in enumerate(all_posts[:25]):
        color, display = plat_meta.get(post.get("platform", ""), ("#6b7280", post.get("platform", "")))
        r = post.get("rating", 3)
        r_class = "tag-green" if r >= 4 else "tag-red" if r <= 2 else "tag-yellow"
        card = f'''<div class="feed-card">
            <div class="feed-top"><span class="feed-platform" style="color:{color}">{display}</span><span class="feed-name">{_esc(post.get('name',''))}</span><span class="feed-tag {r_class}">{'&#9733;'*round(r)} {r}</span></div>
            <div class="feed-text">{_esc(post.get('post',''))}</div></div>'''
        if idx < 10:
            feed_visible += card
        else:
            feed_hidden += card

    expand_btn = ""
    if feed_hidden:
        expand_btn = '<button class="btn-outline" onclick="toggleFeed()">Show all 25 posts</button>'

    # --- EXTREMES ---
    def extreme_card(items, accent):
        cards = ""
        for h in items[:3]:
            p = h.get("_persona", {})
            r = h.get("star_rating", 3)
            cards += f'''<div class="card" style="border-left:3px solid {accent}">
                <div class="ext-rating" style="color:{accent}">{'&#9733;'*max(1,round(r))}{'&#9734;'*(5-max(1,round(r)))} {r}</div>
                <div class="ext-meta">{_esc(p.get('name',''))} · {p.get('platform','')} · {p.get('review_style','')}</div>
                <div class="ext-text">{_esc(h.get('social_post', h.get('first_impression','')))}</div></div>'''
        return cards

    harshest_html = extreme_card(stats.get("harshest_reviews", []), "#dc2626")
    fans_html = extreme_card(stats.get("biggest_fans", []), "#16a34a")

    # --- CONTROVERSIES ---
    controversy_items = ""
    for c in stats.get("controversies", [])[:10]:
        controversy_items += f'<div class="list-item list-item-warning">{_esc(c)}</div>'

    # --- DNF REASONS ---
    dnf_items = ""
    if stats.get("dnf_reasons"):
        reason_counts = {}
        for r in stats["dnf_reasons"]:
            reason_counts[r] = reason_counts.get(r, 0) + 1
        for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1])[:10]:
            dnf_items += f'<div class="list-item list-item-danger">{_esc(reason)} <span class="list-meta">({count} readers)</span></div>'

    # --- ROUND TIMELINE ---
    round_timeline = stats.get("round_timeline", [])
    timeline_data_json = json.dumps(round_timeline)

    timeline_html = ""
    if len(round_timeline) > 1:
        timeline_cards = ""
        for rt in round_timeline:
            rn = rt["round"]
            ra = rt.get("avg_rating")
            ra_str = f"{ra:.2f}" if ra else "—"
            shifts = rt.get("sentiment_shifts")
            shift_info = ""
            if shifts:
                shift_info = f'''<div class="tl-shifts">
                    <span class="tl-badge tl-up">+{shifts.get('more_positive',0)}</span>
                    <span class="tl-badge tl-down">-{shifts.get('more_negative',0)}</span>
                    <span class="tl-badge tl-pol">{shifts.get('polarized',0)}</span></div>'''
            timeline_cards += f'''<div class="card tl-card">
                <div class="tl-round">R{rn}</div>
                <div class="tl-rating">{ra_str}</div>
                <div class="tl-readers">{rt.get('active_readers',0)} readers</div>
                {shift_info}</div>'''

        sec = next_sec()
        timeline_html = f'''<section class="section reveal" id="section-timeline">
            <div class="section-header"><span class="section-num">{sec}</span><h2 class="section-title">Round Timeline</h2></div>
            <p class="section-desc">How the conversation evolved across {total_rounds} rounds.</p>
            <div class="card chart-card"><canvas id="timelineChart" height="200"></canvas></div>
            <div class="tl-grid">{timeline_cards}</div>
        </section>'''

    # --- SOCIAL ROUNDS ---
    all_social_posts = stats.get("all_social_posts", [])
    if not all_social_posts:
        all_social_posts = [dict(p, round=2) for p in stats.get("round2_posts", [])]

    social_rounds_html = ""
    if all_social_posts:
        rounds_seen = sorted(set(p.get("round", 2) for p in all_social_posts))
        social_content = ""
        for rn in rounds_seen:
            round_posts = [p for p in all_social_posts if p.get("round", 2) == rn][:10]
            posts_html = ""
            for rp in round_posts:
                posts_html += f'''<div class="social-post">
                    <div class="social-meta">Replying to <strong>{_esc(rp.get('responding_to',''))}</strong> · {_esc(rp.get('name',''))} · {rp.get('platform','')}</div>
                    <div class="social-text">{_esc(rp.get('post',''))}</div></div>'''
            social_content += f'''<div class="round-group">
                <div class="round-label">Round {rn}</div>
                {posts_html}</div>'''

        shifts = stats.get("sentiment_shifts", {})
        sec = next_sec()
        social_rounds_html = f'''<section class="section reveal" id="section-social">
            <div class="section-header"><span class="section-num">{sec}</span><h2 class="section-title">The Conversation</h2></div>
            <p class="section-desc">Across {len(rounds_seen)} round{'s' if len(rounds_seen) > 1 else ''} of social interaction.</p>
            <div class="shift-grid">
                <div class="card shift-card"><div class="shift-val shift-green" data-count-to="{shifts.get('more_positive',0)}" data-decimals="0">0</div><div class="shift-label">More Positive</div></div>
                <div class="card shift-card"><div class="shift-val shift-red" data-count-to="{shifts.get('more_negative',0)}" data-decimals="0">0</div><div class="shift-label">More Negative</div></div>
                <div class="card shift-card"><div class="shift-val" data-count-to="{shifts.get('unchanged',0)}" data-decimals="0">0</div><div class="shift-label">Unchanged</div></div>
                <div class="card shift-card"><div class="shift-val shift-purple" data-count-to="{shifts.get('polarized',0)}" data-decimals="0">0</div><div class="shift-label">Polarized</div></div>
            </div>
            <div class="social-feed">{social_content}</div>
        </section>'''

    # --- VIRALITY GAUGE ---
    circumference = 2 * math.pi * 85
    vs_offset = circumference * (1 - vs / 100)
    vs_color = "#16a34a" if vs >= 70 else "#eab308" if vs >= 40 else "#a1a1aa"
    vl = "Viral Potential" if vs >= 70 else "Moderate Buzz" if vs >= 40 else "Niche Appeal"

    # --- RECOMMENDATIONS ---
    recommendations = _generate_recommendations(stats)
    recs_html = ""
    for _, title, desc, sentiment in recommendations:
        border = {"positive": "#16a34a", "warning": "#dc2626", "neutral": "#eab308"}.get(sentiment, "#eab308")
        recs_html += f'''<div class="card rec-card" style="border-left:3px solid {border}">
            <div class="rec-title">{_esc(title)}</div>
            <div class="rec-desc">{_esc(desc)}</div></div>'''

    # --- DEMOGRAPHICS ---
    demo_breakdown = stats.get("demographic_breakdown", {})
    seg_colors = {
        "Affluent Bookworms": "#7c3aed", "Young Urban Readers": "#ec4899",
        "Suburban Families": "#16a34a", "Academic Readers": "#2563eb",
        "Budget Readers": "#eab308", "Senior Traditionalists": "#6b7280",
        "Diverse Explorers": "#e11d48", "Genre Devotees": "#f97316", "General": "#71717a"
    }
    demo_cards = ""
    for seg_name, seg_data in sorted(demo_breakdown.items(), key=lambda x: -x[1].get("avg_rating", 0)):
        color = seg_colors.get(seg_name, "#71717a")
        demo_cards += f'''<div class="card seg-card" style="border-left:3px solid {color}">
            <div class="seg-name">{_esc(seg_name)}</div>
            <div class="seg-meta">{seg_data.get('count',0)} readers</div>
            <div class="seg-rating" style="color:{color}">{seg_data.get('avg_rating',0):.1f}</div>
            <div class="seg-stats">
                <span>DNF {seg_data.get('dnf_rate',0):.0f}%</span>
                <span>{seg_data.get('top_emotion','—')}</span>
                <span>Buy {seg_data.get('purchase_rate',0):.0f}%</span>
                {"<span>$" + f"{seg_data.get('avg_price',0):.0f}" + " avg</span>" if seg_data.get('avg_price',0) > 0 else ""}
            </div></div>'''

    # --- CONFIDENCE ---
    consensus = stats.get("consensus_score", 0)
    polar_idx = stats.get("polarization_index", 0)
    moe = stats.get("margin_of_error", 0)
    sample_conf = stats.get("sample_confidence", 0)
    consensus_label = "High — readers agree" if consensus >= 70 else "Moderate" if consensus >= 40 else "Low — very divided"
    polar_label = "Highly Polarizing" if polar_idx >= 2 else "Somewhat Polarizing" if polar_idx >= 1 else "Not Polarizing"

    # --- PURCHASE INTENT ---
    purchase_rate = stats.get("purchase_rate", 0)
    avg_price_willing = stats.get("avg_price_willing", 0)

    # --- NAV ---
    nav_sections = [("hero", "Overview")]
    book_sec = next_sec()
    nav_sections.append((f"section-{book_sec}", "Book"))
    rating_sec = next_sec()
    nav_sections.append((f"section-{rating_sec}", "Ratings"))
    emotion_sec = next_sec()
    nav_sections.append((f"section-{emotion_sec}", "Emotions"))
    plat_sec = next_sec()
    nav_sections.append((f"section-{plat_sec}", "Platforms"))

    demo_data = stats.get("demographic_breakdown", {})
    demo_sec = next_sec() if demo_data else None
    if demo_sec:
        nav_sections.append((f"section-{demo_sec}", "Demographics"))
    conf_sec = next_sec()
    nav_sections.append((f"section-{conf_sec}", "Confidence"))
    purchase_sec = next_sec() if stats.get("purchase_rate", 0) > 0 else None
    if purchase_sec:
        nav_sections.append((f"section-{purchase_sec}", "Purchase"))
    ext_sec = next_sec()
    nav_sections.append((f"section-{ext_sec}", "Extremes"))
    feed_sec = next_sec()
    nav_sections.append((f"section-{feed_sec}", "Feed"))
    cont_sec = next_sec() if controversy_items else None
    if cont_sec:
        nav_sections.append((f"section-{cont_sec}", "Controversy"))
    dnf_sec = next_sec() if dnf_items else None
    if dnf_sec:
        nav_sections.append((f"section-{dnf_sec}", "DNF"))
    if timeline_html:
        nav_sections.append(("section-timeline", "Timeline"))
    if social_rounds_html:
        nav_sections.append(("section-social", "Conversation"))
    viral_sec = next_sec()
    nav_sections.append((f"section-{viral_sec}", "Virality"))
    recs_sec = next_sec()
    nav_sections.append((f"section-{recs_sec}", "Next Steps"))

    nav_dots = ""
    for sid, label in nav_sections:
        nav_dots += f'<a href="#{sid}" class="nav-dot" title="{label}" data-section="{sid}"></a>\n'

    # =========================================================================
    # FULL HTML
    # =========================================================================
    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Readers Report — {total_readers:,} Readers · {total_rounds} Rounds</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html{{scroll-behavior:smooth}}
:root{{
  --bg:#fafafa;--card:#ffffff;--fg:#09090b;
  --muted:#71717a;--muted-bg:#f4f4f5;--border:#e4e4e7;
  --star:#f59e0b;
  --blue:#2563eb;--green:#16a34a;--orange:#f97316;
  --purple:#7c3aed;--rose:#e11d48;--red:#dc2626;
  --teal:#0d9488;--yellow:#eab308;
  --radius:12px;--radius-sm:8px;
}}
body{{
  background:var(--bg);color:var(--fg);
  font-family:'Inter',system-ui,-apple-system,sans-serif;
  line-height:1.6;-webkit-font-smoothing:antialiased;
  overflow-x:hidden;
}}
.container{{max-width:960px;margin:0 auto;padding:40px 24px}}

/* ── Reveal ── */
.reveal{{opacity:0;transform:translateY(20px);transition:opacity .6s ease,transform .6s ease}}
.reveal.visible{{opacity:1;transform:translateY(0)}}

/* ── Nav ── */
.side-nav{{position:fixed;right:20px;top:50%;transform:translateY(-50%);z-index:100;display:flex;flex-direction:column;gap:8px}}
.nav-dot{{width:8px;height:8px;border-radius:50%;background:var(--border);transition:all .3s;cursor:pointer;text-decoration:none;border:none;outline:none}}
.nav-dot:hover{{background:var(--muted);transform:scale(1.4)}}
.nav-dot.active{{background:var(--fg);transform:scale(1.4)}}
@media(max-width:768px){{.side-nav{{display:none}}}}

/* ── Card ── */
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px}}

/* ── Hero ── */
.hero{{text-align:center;padding:64px 20px 48px;border-bottom:1px solid var(--border);margin-bottom:48px}}
.hero-badge{{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--border);border-radius:9999px;padding:5px 16px;font-size:.75rem;font-weight:500;color:var(--muted);margin-bottom:24px;background:var(--card)}}
.hero h1{{font-size:clamp(1.8rem,4vw,2.5rem);font-weight:700;letter-spacing:-.03em;margin-bottom:8px}}
.hero-sub{{color:var(--muted);font-size:.875rem;margin-bottom:40px}}
.hero-score{{display:flex;align-items:baseline;justify-content:center;gap:16px;margin-bottom:8px}}
.hero-num{{font-family:'JetBrains Mono',monospace;font-size:5rem;font-weight:700;line-height:1;letter-spacing:-.04em}}
.hero-stars{{font-size:1.5rem;letter-spacing:2px}}
.star-filled{{color:var(--star)}}.star-half{{color:var(--star);opacity:.6}}.star-empty{{color:var(--border)}}
.hero-verdict{{font-size:.875rem;color:var(--muted);margin-top:16px}}

/* ── Stats ── */
.stats-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:48px}}
.stat-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px;text-align:center;transition:border-color .2s}}
.stat-card:hover{{border-color:var(--muted)}}
.stat-val{{font-family:'JetBrains Mono',monospace;font-size:1.75rem;font-weight:700;line-height:1.2}}
.stat-label{{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:4px;font-weight:500}}

/* ── Sections ── */
.section{{margin-bottom:48px}}
.section-header{{display:flex;align-items:center;gap:12px;margin-bottom:16px}}
.section-num{{font-family:'JetBrains Mono',monospace;font-size:.65rem;font-weight:500;color:var(--muted);background:var(--muted-bg);border-radius:6px;padding:2px 8px}}
.section-title{{font-size:1.2rem;font-weight:600;letter-spacing:-.02em}}
.section-desc{{color:var(--muted);font-size:.85rem;margin-top:-8px;margin-bottom:16px}}

/* ── Book Description ── */
.book-card{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--fg);border-radius:0 var(--radius) var(--radius) 0;padding:24px;font-size:.9rem;line-height:1.7;color:var(--muted);white-space:pre-wrap;max-height:400px;overflow-y:auto}}

/* ── Rating Distribution ── */
.dist-row{{display:flex;align-items:center;gap:12px;margin-bottom:8px}}
.dist-label{{width:20px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:600;color:var(--star)}}
.dist-track{{flex:1;height:28px;background:var(--muted-bg);border-radius:6px;overflow:hidden}}
.dist-bar{{height:100%;border-radius:6px;min-width:3px;width:0;background:var(--bar-color);transition:width 1.5s cubic-bezier(.4,0,.2,1)}}
.dist-count{{width:80px;font-family:'JetBrains Mono',monospace;font-size:.8rem;color:var(--muted);text-align:right}}
.dist-pct{{margin-left:4px;color:var(--border)}}

/* ── Chips ── */
.chips-wrap{{display:flex;flex-wrap:wrap;gap:8px}}
.chip{{display:flex;align-items:center;gap:6px;padding:6px 14px;border-radius:9999px;border:1px solid var(--border);font-size:.8rem;font-weight:500;transition:all .2s;cursor:default;background:var(--card)}}
.chip:hover{{border-color:var(--chip-color);background:color-mix(in srgb,var(--chip-color) 5%,white)}}
.chip-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.chip-count{{font-size:.7rem;color:var(--muted);font-family:'JetBrains Mono',monospace}}

/* ── Platform Cards ── */
.plat-grid{{display:grid;gap:16px}}
.plat-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;transition:border-color .2s}}
.plat-card:hover{{border-color:var(--muted)}}
.plat-accent{{height:3px;width:100%}}
.plat-header{{display:flex;align-items:center;justify-content:space-between;padding:16px 20px 8px}}
.plat-name{{font-weight:600;font-size:.95rem}}
.plat-readers{{font-family:'JetBrains Mono',monospace;font-size:.85rem;font-weight:600}}
.plat-post{{padding:10px 20px;border-top:1px solid var(--muted-bg)}}
.plat-post-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}}
.plat-post-name{{font-size:.75rem;color:var(--muted);font-weight:500}}
.plat-post-rating{{font-size:.75rem;color:var(--star);font-family:'JetBrains Mono',monospace}}
.plat-post-text{{font-size:.85rem;line-height:1.55}}

/* ── Feed ── */
.feed-grid{{display:grid;gap:8px}}
.feed-hidden{{display:none}}
.feed-card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 16px;transition:border-color .2s}}
.feed-card:hover{{border-color:var(--muted)}}
.feed-top{{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:.78rem}}
.feed-platform{{font-weight:600}}.feed-name{{color:var(--muted)}}
.feed-tag{{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600;padding:2px 8px;border-radius:9999px}}
.tag-green{{background:#dcfce7;color:#16a34a}}.tag-red{{background:#fef2f2;color:#dc2626}}.tag-yellow{{background:#fefce8;color:#a16207}}
.feed-text{{font-size:.85rem;line-height:1.55}}
.btn-outline{{display:block;margin:16px auto 0;padding:8px 24px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);font-family:'Inter',sans-serif;font-size:.8rem;color:var(--muted);cursor:pointer;transition:all .2s;font-weight:500}}
.btn-outline:hover{{border-color:var(--fg);color:var(--fg)}}

/* ── Extremes ── */
.extremes-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:680px){{.extremes-grid{{grid-template-columns:1fr}}}}
.extremes-col h3{{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;color:var(--muted)}}
.ext-rating{{font-size:.9rem;font-weight:600;margin-bottom:4px}}
.ext-meta{{font-size:.72rem;color:var(--muted);margin-bottom:6px}}
.ext-text{{font-size:.85rem;line-height:1.55}}

/* ── List Items ── */
.list-item{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 16px;margin-bottom:6px;font-size:.85rem;transition:border-color .2s}}
.list-item:hover{{border-color:var(--muted)}}
.list-item-warning{{border-left:3px solid var(--yellow)}}
.list-item-danger{{border-left:3px solid var(--red)}}
.list-meta{{color:var(--muted);font-size:.75rem}}

/* ── Timeline ── */
.chart-card{{padding:24px;margin-bottom:16px}}
.tl-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}}
.tl-card{{text-align:center;padding:14px}}
.tl-round{{font-family:'JetBrains Mono',monospace;font-size:.65rem;font-weight:600;color:var(--muted);letter-spacing:.08em;margin-bottom:4px}}
.tl-rating{{font-family:'JetBrains Mono',monospace;font-size:1.5rem;font-weight:700;color:var(--fg)}}
.tl-readers{{font-size:.65rem;color:var(--muted);margin-top:2px}}
.tl-shifts{{display:flex;gap:4px;justify-content:center;margin-top:6px;font-size:.6rem;font-family:'JetBrains Mono',monospace}}
.tl-badge{{padding:1px 6px;border-radius:9999px;font-weight:600}}
.tl-up{{background:#dcfce7;color:#16a34a}}.tl-down{{background:#fef2f2;color:#dc2626}}.tl-pol{{background:#faf5ff;color:#7c3aed}}

/* ── Social Rounds ── */
.shift-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:20px}}
@media(max-width:600px){{.shift-grid{{grid-template-columns:repeat(2,1fr)}}}}
.shift-card{{text-align:center;padding:16px}}
.shift-val{{font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;line-height:1.2}}
.shift-green{{color:var(--green)}}.shift-red{{color:var(--red)}}.shift-purple{{color:var(--purple)}}
.shift-label{{font-size:.6rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:4px;font-weight:500}}
.round-group{{margin-bottom:16px}}
.round-label{{display:inline-block;font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600;color:var(--muted);background:var(--muted-bg);border-radius:6px;padding:3px 10px;margin-bottom:8px}}
.social-feed{{display:grid;gap:8px}}
.social-post{{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--blue);border-radius:var(--radius-sm);padding:12px 16px;transition:border-color .2s}}
.social-post:hover{{border-color:var(--muted)}}
.social-meta{{font-size:.75rem;color:var(--muted);margin-bottom:4px}}
.social-text{{font-size:.85rem;line-height:1.55}}

/* ── Virality ── */
.virality-box{{text-align:center;padding:40px 20px}}
.gauge-wrap{{position:relative;width:200px;height:200px;margin:0 auto 16px}}
.gauge-svg{{width:100%;height:100%;transform:rotate(-90deg)}}
.gauge-bg{{fill:none;stroke:var(--muted-bg);stroke-width:8}}
.gauge-fill{{fill:none;stroke-width:8;stroke-linecap:round;transition:stroke-dashoffset 2.5s cubic-bezier(.4,0,.2,1)}}
.gauge-value{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-family:'JetBrains Mono',monospace;font-size:3.5rem;font-weight:700;line-height:1}}
.gauge-label{{font-size:.9rem;color:var(--muted);font-weight:500}}

/* ── Demographics ── */
.seg-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.seg-card{{padding:16px}}
.seg-name{{font-weight:600;font-size:.9rem;margin-bottom:2px}}
.seg-meta{{font-size:.7rem;color:var(--muted);margin-bottom:6px}}
.seg-rating{{font-family:'JetBrains Mono',monospace;font-size:1.8rem;font-weight:700;line-height:1.1}}
.seg-stats{{display:flex;flex-wrap:wrap;gap:8px;font-size:.7rem;color:var(--muted);margin-top:8px;font-family:'JetBrains Mono',monospace}}

/* ── Confidence ── */
.conf-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.conf-card{{text-align:center;padding:20px}}
.conf-val{{font-family:'JetBrains Mono',monospace;font-size:2rem;font-weight:700;line-height:1.1}}
.conf-label{{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:4px;font-weight:500}}
.conf-desc{{font-size:.75rem;color:var(--muted);margin-top:6px}}

/* ── Purchase ── */
.purchase-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
@media(max-width:600px){{.purchase-grid{{grid-template-columns:1fr}}}}
.purchase-card{{text-align:center;padding:24px}}
.purchase-val{{font-family:'JetBrains Mono',monospace;font-size:2.5rem;font-weight:700;color:var(--green);line-height:1}}
.purchase-label{{font-size:.65rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:6px;font-weight:500}}

/* ── Recommendations ── */
.recs-grid{{display:grid;gap:10px}}
.rec-card{{padding:20px}}
.rec-title{{font-weight:600;font-size:.9rem;margin-bottom:4px}}
.rec-desc{{font-size:.85rem;line-height:1.6;color:var(--muted)}}

/* ── Share ── */
.share-card{{max-width:560px;margin:0 auto;background:var(--fg);border-radius:var(--radius);padding:48px 40px;text-align:center;color:white}}
.share-badge{{font-size:.65rem;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.5);font-weight:500;margin-bottom:16px}}
.share-num{{font-family:'JetBrains Mono',monospace;font-size:4rem;font-weight:700;line-height:1}}
.share-stars{{font-size:1.2rem;letter-spacing:2px;color:var(--star);margin:8px 0}}
.share-meta{{font-size:.75rem;color:rgba(255,255,255,.4);margin-top:12px}}
.share-hint{{text-align:center;font-size:.75rem;color:var(--muted);margin-top:12px}}

/* ── Footer ── */
.report-footer{{text-align:center;padding:48px 20px;margin-top:48px;border-top:1px solid var(--border);color:var(--muted);font-size:.8rem}}
.footer-brand{{font-weight:600;font-size:1rem;color:var(--fg);margin-bottom:4px}}
</style>
</head>
<body>

<nav class="side-nav" id="sideNav">{nav_dots}</nav>

<div class="container">

<!-- HERO -->
<div class="hero reveal" id="hero">
  <div class="hero-badge">Readers · {total_readers:,} Readers · {total_rounds} Round{'s' if total_rounds > 1 else ''}</div>
  <h1>Reader Prediction Report</h1>
  <p class="hero-sub">Generated {timestamp} via {_esc(provider_name)}</p>
  <div class="hero-score">
    <span class="hero-num" data-count-to="{avg}" data-decimals="1">0.0</span>
    <span class="hero-stars">{stars_html}</span>
  </div>
  <p class="hero-verdict">Simulated across BookTok, Goodreads, Reddit, Bookstagram, X, and silent lurkers</p>
</div>

<!-- KEY STATS -->
<div class="stats-grid reveal">
  <div class="stat-card"><div class="stat-val" data-count-to="{avg}" data-decimals="1">0</div><div class="stat-label">Avg Rating</div></div>
  <div class="stat-card"><div class="stat-val" style="color:var(--red)" data-count-to="{dnf_rate}" data-decimals="0">0</div><div class="stat-label">DNF Rate %</div></div>
  <div class="stat-card"><div class="stat-val" style="color:var(--blue)" data-count-to="{vs}" data-decimals="0">0</div><div class="stat-label">Virality</div></div>
  <div class="stat-card"><div class="stat-val" style="color:var(--orange)" data-count-to="{n_controversies}" data-decimals="0">0</div><div class="stat-label">Controversies</div></div>
  <div class="stat-card"><div class="stat-val" data-count-to="{total_rounds}" data-decimals="0">0</div><div class="stat-label">Rounds</div></div>
</div>

<!-- BOOK DESCRIPTION -->
<section class="section reveal" id="section-{book_sec}">
  <div class="section-header"><span class="section-num">{book_sec}</span><h2 class="section-title">The Book</h2></div>
  <div class="book-card">{_esc(book_description)}</div>
</section>

<!-- RATING DISTRIBUTION -->
<section class="section reveal" id="section-{rating_sec}">
  <div class="section-header"><span class="section-num">{rating_sec}</span><h2 class="section-title">Rating Distribution</h2></div>
  {dist_rows}
</section>

<!-- EMOTIONS -->
<section class="section reveal" id="section-{emotion_sec}">
  <div class="section-header"><span class="section-num">{emotion_sec}</span><h2 class="section-title">Emotional Reactions</h2></div>
  <div class="chips-wrap">{emotion_chips}</div>
</section>

<!-- PLATFORMS -->
<section class="section reveal" id="section-{plat_sec}">
  <div class="section-header"><span class="section-num">{plat_sec}</span><h2 class="section-title">Platform Breakdown</h2></div>
  <div class="plat-grid">{platform_cards}</div>
</section>

<!-- DEMOGRAPHICS -->
{"<section class='section reveal' id='section-" + demo_sec + "'><div class='section-header'><span class='section-num'>" + demo_sec + "</span><h2 class='section-title'>Demographics (PRISM)</h2></div><p class='section-desc'>How different reader demographics rated your book.</p><div class='seg-grid'>" + demo_cards + "</div></section>" if demo_sec and demo_cards else ""}

<!-- CONFIDENCE -->
<section class="section reveal" id="section-{conf_sec}">
  <div class="section-header"><span class="section-num">{conf_sec}</span><h2 class="section-title">Prediction Confidence</h2></div>
  <p class="section-desc">Statistical confidence based on reader consensus.</p>
  <div class="conf-grid">
    <div class="card conf-card">
      <div class="conf-val" style="color:{'var(--green)' if consensus >= 70 else 'var(--yellow)' if consensus >= 40 else 'var(--red)'}" data-count-to="{consensus}" data-decimals="0">0</div>
      <div class="conf-label">Consensus Score</div>
      <div class="conf-desc">{consensus_label}</div>
    </div>
    <div class="card conf-card">
      <div class="conf-val" style="color:var(--purple)">{polar_label}</div>
      <div class="conf-label">Polarization</div>
      <div class="conf-desc">Index: {polar_idx:.1f}</div>
    </div>
    <div class="card conf-card">
      <div class="conf-val" style="color:var(--blue)">&plusmn;{moe:.2f}</div>
      <div class="conf-label">Margin of Error</div>
      <div class="conf-desc">95% confidence interval</div>
    </div>
    <div class="card conf-card">
      <div class="conf-val" style="color:var(--teal)" data-count-to="{sample_conf}" data-decimals="0">0</div>
      <div class="conf-label">Sample Confidence %</div>
      <div class="conf-desc">Based on {total_readers:,} readers</div>
    </div>
  </div>
</section>

<!-- PURCHASE INTENT -->
{"<section class='section reveal' id='section-" + purchase_sec + "'><div class='section-header'><span class='section-num'>" + purchase_sec + "</span><h2 class='section-title'>Purchase Intent</h2></div><p class='section-desc'>Would readers actually buy this book?</p><div class='purchase-grid'><div class='card purchase-card'><div class='purchase-val' data-count-to='" + f"{purchase_rate:.0f}" + "' data-decimals='0'>0</div><div class='purchase-label'>% Would Buy</div></div><div class='card purchase-card'><div class='purchase-val' style='color:var(--yellow)'>$" + f"{avg_price_willing:.0f}" + "</div><div class='purchase-label'>Avg Price Willing</div></div><div class='card purchase-card'><div class='purchase-val' style='color:var(--blue)'>" + f"{total_readers:,}" + "</div><div class='purchase-label'>Readers Surveyed</div></div></div></section>" if purchase_sec else ""}

<!-- EXTREMES -->
<section class="section reveal" id="section-{ext_sec}">
  <div class="section-header"><span class="section-num">{ext_sec}</span><h2 class="section-title">Harshest Critics vs. Biggest Fans</h2></div>
  <div class="extremes-grid">
    <div class="extremes-col"><h3 style="color:var(--red)">The Harshest</h3>{harshest_html}</div>
    <div class="extremes-col"><h3 style="color:var(--green)">The Superfans</h3>{fans_html}</div>
  </div>
</section>

<!-- SOCIAL FEED -->
<section class="section reveal" id="section-{feed_sec}">
  <div class="section-header"><span class="section-num">{feed_sec}</span><h2 class="section-title">Simulated Social Feed</h2></div>
  <p class="section-desc">The 25 most notable reactions across all platforms.</p>
  <div class="feed-grid">{feed_visible}</div>
  <div class="feed-hidden" id="feedMore">{feed_hidden}</div>
  {expand_btn}
</section>

<!-- CONTROVERSY -->
{"<section class='section reveal' id='section-" + cont_sec + "'><div class='section-header'><span class='section-num'>" + cont_sec + "</span><h2 class='section-title'>Controversy Radar</h2></div>" + controversy_items + "</section>" if cont_sec else ""}

<!-- DNF -->
{"<section class='section reveal' id='section-" + dnf_sec + "'><div class='section-header'><span class='section-num'>" + dnf_sec + "</span><h2 class='section-title'>DNF Analysis (" + str(dnf_count) + " would quit)</h2></div>" + dnf_items + "</section>" if dnf_sec else ""}

<!-- TIMELINE -->
{timeline_html}

<!-- SOCIAL ROUNDS -->
{social_rounds_html}

<!-- VIRALITY -->
<section class="section reveal" id="section-{viral_sec}">
  <div class="section-header"><span class="section-num">{viral_sec}</span><h2 class="section-title">Viral Potential</h2></div>
  <div class="card virality-box">
    <div class="gauge-wrap">
      <svg viewBox="0 0 200 200" class="gauge-svg">
        <circle cx="100" cy="100" r="85" class="gauge-bg"/>
        <circle cx="100" cy="100" r="85" class="gauge-fill" stroke="{vs_color}" stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{circumference:.1f}" data-target-offset="{vs_offset:.1f}"/>
      </svg>
      <div class="gauge-value" style="color:{vs_color}" data-count-to="{vs}" data-decimals="0">0</div>
    </div>
    <div class="gauge-label">{vl}</div>
  </div>
</section>

<!-- RECOMMENDATIONS -->
<section class="section reveal" id="section-{recs_sec}">
  <div class="section-header"><span class="section-num">{recs_sec}</span><h2 class="section-title">Recommended Next Steps</h2></div>
  <p class="section-desc">Data-driven action items based on your simulation results.</p>
  <div class="recs-grid">{recs_html}</div>
</section>

<!-- SHARE -->
<section class="section reveal" id="section-share">
  <div class="share-card">
    <div class="share-badge">Readers · {total_readers:,} AI Readers</div>
    <div class="share-num">{avg:.1f}</div>
    <div class="share-stars">{stars_html}</div>
    <div class="share-meta">{total_rounds} rounds · {vs:.0f} virality · {dnf_rate:.0f}% DNF · {n_controversies} controversies</div>
  </div>
  <p class="share-hint">Screenshot this card to share on social media</p>
</section>

<!-- FOOTER -->
<div class="report-footer">
  <div class="footer-brand">Readers</div>
  <p>{total_readers:,} AI Readers · {total_rounds} Rounds of Social Simulation</p>
</div>

</div>

<script>
const timelineData = {timeline_data_json};

function countUp(el, target, dur) {{
  dur = dur || 1200;
  const dec = parseInt(el.dataset.decimals || '0');
  let start = null;
  const step = (ts) => {{
    if (!start) start = ts;
    const p = Math.min((ts - start) / dur, 1);
    const e = 1 - Math.pow(1 - p, 3);
    el.textContent = (target * e).toFixed(dec);
    if (p < 1) requestAnimationFrame(step);
    else el.textContent = target.toFixed(dec);
  }};
  requestAnimationFrame(step);
}}

const observer = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      e.target.classList.add('visible');
      e.target.querySelectorAll('[data-count-to]').forEach(el => {{
        if (!el._c) {{ el._c = true; countUp(el, parseFloat(el.dataset.countTo)); }}
      }});
      e.target.querySelectorAll('.dist-bar[data-target-width]').forEach(b => {{
        if (!b._a) {{ b._a = true; setTimeout(() => {{ b.style.width = b.dataset.targetWidth; }}, 100); }}
      }});
      e.target.querySelectorAll('.gauge-fill[data-target-offset]').forEach(g => {{
        if (!g._a) {{ g._a = true; setTimeout(() => {{ g.style.strokeDashoffset = g.dataset.targetOffset; }}, 200); }}
      }});
    }}
  }});
}}, {{ threshold: 0.15 }});
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));

const navObs = new IntersectionObserver((entries) => {{
  entries.forEach(e => {{
    if (e.isIntersecting) {{
      document.querySelectorAll('.nav-dot').forEach(d => d.classList.remove('active'));
      const dot = document.querySelector('.nav-dot[data-section="' + e.target.id + '"]');
      if (dot) dot.classList.add('active');
    }}
  }});
}}, {{ threshold: 0.3 }});
document.querySelectorAll('[id^="hero"],[id^="section-"]').forEach(el => navObs.observe(el));

function toggleFeed() {{
  const m = document.getElementById('feedMore');
  const b = document.querySelector('.btn-outline');
  if (m.style.display === 'none' || !m.style.display) {{
    m.style.display = 'grid'; m.style.gap = '8px';
    b.textContent = 'Show fewer';
  }} else {{
    m.style.display = 'none';
    b.textContent = 'Show all 25 posts';
  }}
}}

// Timeline Chart
(function() {{
  const canvas = document.getElementById('timelineChart');
  if (!canvas || timelineData.length < 2) return;
  const ctx = canvas.getContext('2d');
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width - 48;
  canvas.height = 200;
  const W = canvas.width, H = canvas.height;
  const pad = {{ top:20, right:30, bottom:40, left:50 }};
  const pW = W - pad.left - pad.right, pH = H - pad.top - pad.bottom;
  const data = timelineData.filter(d => d.avg_rating !== null);
  if (data.length < 2) return;
  const minR = Math.floor(Math.min(...data.map(d => d.avg_rating)) * 2) / 2;
  const maxR = Math.ceil(Math.max(...data.map(d => d.avg_rating)) * 2) / 2;
  const range = Math.max(maxR - minR, 0.5);
  function xP(i) {{ return pad.left + (i / (data.length - 1)) * pW; }}
  function yP(v) {{ return pad.top + (1 - (v - minR) / range) * pH; }}

  ctx.strokeStyle = '#e4e4e7'; ctx.lineWidth = 1;
  for (let v = minR; v <= maxR; v += 0.5) {{
    const y = yP(v);
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    ctx.fillStyle = '#a1a1aa'; ctx.font = '11px JetBrains Mono, monospace';
    ctx.textAlign = 'right'; ctx.fillText(v.toFixed(1), pad.left - 8, y + 4);
  }}
  ctx.textAlign = 'center'; ctx.fillStyle = '#71717a';
  data.forEach((d, i) => {{ ctx.fillText('R' + d.round, xP(i), H - pad.bottom + 20); }});

  const grad = ctx.createLinearGradient(pad.left, 0, W - pad.right, 0);
  grad.addColorStop(0, '#2563eb'); grad.addColorStop(1, '#7c3aed');
  ctx.strokeStyle = grad; ctx.lineWidth = 2.5; ctx.lineJoin = 'round'; ctx.beginPath();
  data.forEach((d, i) => {{ const x = xP(i), y = yP(d.avg_rating); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }});
  ctx.stroke();

  const aG = ctx.createLinearGradient(0, pad.top, 0, H - pad.bottom);
  aG.addColorStop(0, 'rgba(37,99,235,0.08)'); aG.addColorStop(1, 'rgba(37,99,235,0)');
  ctx.fillStyle = aG; ctx.beginPath();
  data.forEach((d, i) => {{ const x = xP(i), y = yP(d.avg_rating); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }});
  ctx.lineTo(xP(data.length - 1), H - pad.bottom); ctx.lineTo(pad.left, H - pad.bottom);
  ctx.closePath(); ctx.fill();

  data.forEach((d, i) => {{
    const x = xP(i), y = yP(d.avg_rating);
    ctx.fillStyle = '#ffffff';
    ctx.beginPath(); ctx.arc(x, y, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = i === 0 ? '#2563eb' : '#7c3aed';
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#09090b'; ctx.font = 'bold 11px JetBrains Mono, monospace';
    ctx.textAlign = 'center'; ctx.fillText(d.avg_rating.toFixed(2), x, y - 12);
  }});
}})();
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_html)

    return output_path

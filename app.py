from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# In-memory storage of inspirations
inspirations = []

GAME_SPEC = {
    "title": "Eclipse of the Reincarned",
    "tagline": "A 3-D sci-fi fantasy action RPG of starforged magic and reborn heroes.",
    "story_intro": (
        "In the Helix Expanse, souls are recycled through a cosmic lattice called the Loom. "
        "You are a Reincarned Vanguard, awakened with fractured memories of past lives and a "
        "sentient starship known as the Ark-Relic. When the Loom glitches and resurrects ancient "
        "warlords, the Expanse fractures into warring reality-shards. Your mission is to stitch "
        "the Loom back together, confronting the echoes of who you once were."
    ),
    "pillars": [
        "High-velocity melee and ranged combat with gravity-skipping traversal.",
        "Deep progression: archetypes, skill constellations, and relic matrices.",
        "Branching quests shaped by your past-life choices and crew alliances.",
    ],
    "core_loop": [
        "Scout a reality-shard from the Ark-Relic.",
        "Engage enemies and harvest Astral Resonance.",
        "Complete quests and unlock past-life memories.",
        "Upgrade skills, gear, and ship systems.",
        "Reforge the Loom and open new shards.",
    ],
    "systems": {
        "Enemies": [
            "Loombound Revenants: resurrected soldiers with adaptive armor.",
            "Voidglass Hydras: multi-core beasts that mutate mid-fight.",
            "Chrono-Scribes: time-mages who rewrite your cooldowns.",
        ],
        "Leveling": [
            "Earn Astral Resonance for combat, quests, and exploration.",
            "Choose Attribute Nodes: Might, Flux, Insight, Resolve.",
            "Unlock Past-Life Traits that alter combat combos.",
        ],
        "Quests": [
            "Mainline: Stabilize the Loom and confront the First Reincarnate.",
            "Faction: Broker alliances between Starforged Houses.",
            "Crew Loyalty: Resolve personal arcs that unlock ship mods.",
        ],
        "Skill Trees": [
            "Vanguard (melee): Rift Blades, Gravity Counter, Starfall Slam.",
            "Arcanist (magic): Prism Barrage, Singularity Veil, Nebula Surge.",
            "Ranger (ranged): Railburst, Phase Cloak, Drone Overwatch.",
        ],
        "Matrices": [
            "Relic Matrix: socket artifacts to change weapon behavior.",
            "Ship Matrix: re-route power between shields, thrusters, and labs.",
            "Memory Matrix: equip past-life fragments for passive bonuses.",
        ],
    },
    "zones": [
        {
            "name": "Aurora Wastes",
            "hook": "A crystalline desert where gravity breaks into spirals.",
        },
        {
            "name": "Cathedral of Orbits",
            "hook": "A moon-temple that aligns with forgotten constellations.",
        },
        {
            "name": "The Sundered Loom",
            "hook": "Reality frays into floating corridors of pure memory.",
        },
    ],
}

# HTML template
HTML = """
<!doctype html>
<title>{{ game.title }}</title>
<style>
    :root {
        color-scheme: dark;
        --bg: #05070f;
        --panel: rgba(11, 16, 32, 0.85);
        --accent: #6ef4ff;
        --accent-2: #b46bff;
        --text: #e8f1ff;
        --muted: #9fb3d9;
    }
    body {
        margin: 0;
        font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
        background: radial-gradient(circle at top, #122148 0%, var(--bg) 55%);
        color: var(--text);
    }
    header {
        padding: 48px 10vw 24px;
        background: linear-gradient(135deg, rgba(110, 244, 255, 0.15), transparent 60%);
    }
    h1 {
        font-size: 2.8rem;
        margin-bottom: 8px;
    }
    h2 {
        color: var(--accent);
        margin-top: 32px;
    }
    .tagline {
        color: var(--muted);
        font-size: 1.15rem;
    }
    main {
        padding: 0 10vw 64px;
        display: grid;
        gap: 24px;
    }
    .grid {
        display: grid;
        gap: 24px;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }
    .panel {
        background: var(--panel);
        border: 1px solid rgba(110, 244, 255, 0.2);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(12px);
    }
    ul {
        margin: 12px 0 0;
        padding-left: 18px;
        color: var(--muted);
    }
    li {
        margin-bottom: 8px;
    }
    .pillars {
        display: grid;
        gap: 12px;
    }
    .pillars div {
        border-left: 3px solid var(--accent-2);
        padding-left: 12px;
    }
    form {
        display: grid;
        gap: 12px;
    }
    textarea {
        min-height: 120px;
        background: rgba(7, 11, 22, 0.85);
        color: var(--text);
        border: 1px solid rgba(110, 244, 255, 0.35);
        border-radius: 12px;
        padding: 12px;
        resize: vertical;
    }
    button {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        color: #06060b;
        border: none;
        border-radius: 999px;
        padding: 12px 24px;
        font-weight: 700;
        cursor: pointer;
        width: fit-content;
    }
    .inspirations li {
        color: var(--text);
    }
</style>
<header>
    <h1>{{ game.title }}</h1>
    <div class="tagline">{{ game.tagline }}</div>
</header>
<main>
    <section class="panel">
        <h2>Story Premise</h2>
        <p>{{ game.story_intro }}</p>
    </section>
    <section class="panel">
        <h2>Design Pillars</h2>
        <div class="pillars">
            {% for item in game.pillars %}<div>{{ item }}</div>{% endfor %}
        </div>
    </section>
    <section class="panel">
        <h2>Core Loop</h2>
        <ul>
            {% for item in game.core_loop %}<li>{{ item }}</li>{% endfor %}
        </ul>
    </section>
    <section class="grid">
        {% for system_name, system_items in game.systems.items() %}
        <div class="panel">
            <h2>{{ system_name }}</h2>
            <ul>
                {% for item in system_items %}<li>{{ item }}</li>{% endfor %}
            </ul>
        </div>
        {% endfor %}
    </section>
    <section class="panel">
        <h2>Reality-Shard Zones</h2>
        <ul>
            {% for zone in game.zones %}
            <li><strong>{{ zone.name }}:</strong> {{ zone.hook }}</li>
            {% endfor %}
        </ul>
    </section>
    <section class="panel">
        <h2>Your IP & Hobbies (Optional)</h2>
        <p>Share any themes, characters, or personal hobbies you want woven into future iterations.</p>
        <form action="{{ url_for('add_inspiration') }}" method="post">
            <textarea name="inspiration" placeholder="Example: synthwave music, astro-photography, mythic swords..." rows="5"></textarea>
            <button type="submit">Add Inspiration</button>
        </form>
        <h3>Captured Inspirations</h3>
        <ul class="inspirations">
            {% for entry in inspirations %}<li>{{ entry }}</li>{% else %}<li>No inspirations yet.</li>{% endfor %}
        </ul>
    </section>
</main>
"""

@app.route('/')
def index():
    return render_template_string(HTML, game=GAME_SPEC, inspirations=inspirations)

@app.route('/add', methods=['POST'])
def add_inspiration():
    inspiration = request.form.get('inspiration', '').strip()
    if inspiration:
        inspirations.append(inspiration)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

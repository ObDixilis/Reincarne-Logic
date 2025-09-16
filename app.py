from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# In-memory storage of ideas
ideas = []

# HTML template
HTML = """
<!doctype html>
<title>Think Tank</title>
<h1>Grand Challenge Think Tank</h1>
<form action="{{ url_for('add_idea') }}" method="post">
    <textarea name="idea" rows="4" cols="50" placeholder="Share your idea..."></textarea><br>
    <button type="submit">Submit Idea</button>
</form>
<h2>Submitted Ideas</h2>
<ul>
{% for i in ideas %}<li>{{ i }}</li>{% else %}<li>No ideas yet!</li>{% endfor %}
</ul>
"""

@app.route('/')
def index():
    return render_template_string(HTML, ideas=ideas)

@app.route('/add', methods=['POST'])
def add_idea():
    idea = request.form.get('idea', '').strip()
    if idea:
        ideas.append(idea)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

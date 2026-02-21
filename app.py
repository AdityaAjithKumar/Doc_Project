from flask import Flask, render_template, request, redirect, url_for, session
import docx
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key')

# In-memory cache: avoids re-parsing the same file on every request
_question_cache = {}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def get_questions(file_path):
    """Return parsed questions, using module-level cache to avoid re-parsing."""
    if file_path not in _question_cache:
        _question_cache[file_path] = read_docx(file_path)
    return _question_cache[file_path]


def read_docx(file_path):
    """Parse an Answer Key docx with the schema:
        Question N: <text>
        • A. <option>
        • B. <option>
        • C. <option>
        • D. <option>
        The correct answer is: X. <answer text>
        Explanation
        <explanation paragraph>
        Why the other options are not the best answer
        • A. <option>: <reason>
        • C. <option>: <reason>
        • D. <option>: <reason>
    Duplicate questions (same number) are skipped.
    """
    doc = docx.Document(file_path)
    questions = []
    seen_numbers = set()
    current_q = None
    state = None          # 'options' | 'explanation' | 'why_wrong'
    explanation_buf = []

    # Regex patterns
    q_re      = re.compile(r'^Question\s+(\d+):\s+(.+)', re.IGNORECASE)
    # Options / wrong-explanation bullets have NO literal bullet char in text;
    # the 'List Bullet' Word style is purely a paragraph style.
    opt_re    = re.compile(r'^([A-D])\.\s+(.+)')
    answer_re = re.compile(r'^The correct answer is:\s*([A-D])\.\s+(.*)', re.IGNORECASE)
    why_re    = re.compile(r'^([A-D])\.\s+(.+)')

    def save_current():
        if current_q:
            if explanation_buf:
                current_q['explanation'] = ' '.join(explanation_buf)
            questions.append(current_q)

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Skip section headers
        if re.match(r'^Answer Key', text, re.IGNORECASE):
            continue
        if re.match(r'^Why the other options', text, re.IGNORECASE):
            if current_q and explanation_buf:
                current_q['explanation'] = ' '.join(explanation_buf)
                explanation_buf = []
            state = 'why_wrong'
            continue
        if text == 'Explanation':
            state = 'explanation'
            explanation_buf = []
            continue

        # New question heading
        m = q_re.match(text)
        if m:
            q_num = int(m.group(1))
            if q_num in seen_numbers:
                # Duplicate: finalise any in-progress question and skip
                save_current()
                current_q = None
                state = None
                explanation_buf = []
                continue
            seen_numbers.add(q_num)
            save_current()
            current_q = {
                'number': q_num,
                'question': m.group(2),
                'options': [],           # list of {'letter': str, 'text': str}
                'correct_answer': '',    # letter only, e.g. 'B'
                'correct_answer_text': '',
                'explanation': '',
                'wrong_explanations': {}  # letter -> reason string
            }
            state = 'options'
            explanation_buf = []
            continue

        if current_q is None:
            continue

        # "The correct answer is: X. ..."
        m = answer_re.match(text)
        if m:
            current_q['correct_answer'] = m.group(1)
            current_q['correct_answer_text'] = m.group(2)
            state = None
            continue

        if state == 'options':
            m = opt_re.match(text)
            if m:
                current_q['options'].append({'letter': m.group(1), 'text': m.group(2)})
            continue

        if state == 'explanation':
            explanation_buf.append(text)
            continue

        if state == 'why_wrong':
            m = why_re.match(text)
            if m:
                letter = m.group(1)
                # Format: "Option text: reason" – keep the full string as the reason
                current_q['wrong_explanations'][letter] = m.group(2)
            continue

    save_current()
    questions.sort(key=lambda q: q['number'])
    return questions


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        if file.filename == '':
            return 'No selected file'
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # Pre-cache the questions so the first request is fast
            get_questions(file_path)
            session.clear()
            session['filename'] = filename
            # answers stored compactly: {str(qid): selected_letter}
            session['answers'] = {}
            session['score'] = 0
            return redirect(url_for('question', qid=0))
    return render_template('upload.html')


@app.route('/question/<int:qid>', methods=['GET', 'POST'])
def question(qid):
    filename = session.get('filename')
    if not filename:
        return redirect(url_for('upload_file'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        session.clear()
        return redirect(url_for('upload_file'))

    questions = get_questions(file_path)
    # answers: {str(qid): selected_letter}
    answers = session.get('answers', {})

    if qid >= len(questions) or qid < 0:
        return redirect(url_for('upload_file'))

    q = questions[qid]
    submitted = str(qid) in answers
    selected_option = answers.get(str(qid)) if submitted else None
    correct = (selected_option == q['correct_answer']) if submitted else None

    if request.method == 'POST' and not submitted:
        selected_option = request.form.get('option')
        if selected_option:
            correct = (selected_option == q['correct_answer'])
            answers[str(qid)] = selected_option
            session['answers'] = answers
            if correct:
                session['score'] = session.get('score', 0) + 1
            return redirect(url_for('question', qid=qid))

    return render_template(
        'question.html',
        question=q,
        qid=qid,
        correct=correct,
        submitted=submitted,
        selected_option=selected_option,
        total=len(questions),
        score=session.get('score', 0),
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)


from flask import Flask, render_template, request, redirect, url_for, session
import docx
import re
import os
import time
from werkzeug.utils import secure_filename
from flask_session import Session

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem to store session data

Session(app)  # Initialize the session

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


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
            session['questions'] = read_docx(file_path)
            session['answers'] = [None] * len(session['questions'])
            session['marked'] = [False] * len(session['questions'])
            session['visited'] = [False] * len(session['questions'])
            session['paused'] = False
            session['start_time'] = time.time()
            session['elapsed_before_pause'] = 0
            return redirect(url_for('question', qid=0))
    return render_template('upload.html')


@app.route('/question/<int:qid>', methods=['GET', 'POST'])
def question(qid):
    questions = session.get('questions', [])
    answers = session.get('answers', [])
    marked = session.get('marked', [])
    visited = session.get('visited', [])
    if not questions or qid >= len(questions) or qid < 0:
        return redirect(url_for('upload_file'))

    # Check if quiz is paused
    if session.get('paused') and request.args.get('resume') != '1':
        return redirect(url_for('paused'))

    if request.args.get('resume') == '1':
        session['paused'] = False
        session['start_time'] = time.time()

    # Mark this question as visited
    if qid < len(visited):
        visited[qid] = True
        session['visited'] = visited

    q = questions[qid]
    correct = None
    selected_option = None
    submitted = answers[qid] is not None

    if request.method == 'POST':
        action = request.form.get('action')

        # Toggle mark for review
        if action == 'mark_review':
            marked[qid] = not marked[qid]
            session['marked'] = marked
            return redirect(url_for('question', qid=qid))

        # Submit answer
        if not submitted:
            selected_option = request.form.get('option')
            if selected_option:
                correct = (selected_option == q['correct_answer'])
                answers[qid] = {'selected_option': selected_option, 'correct': correct}
                session['answers'] = answers
                return redirect(url_for('question', qid=qid))

    if submitted:
        selected_option = answers[qid]['selected_option']
        correct = answers[qid]['correct']

    # Calculate progress stats
    answered_count = sum(1 for a in answers if a is not None)
    correct_count = sum(1 for a in answers if a is not None and a['correct'])

    # Build per-question status for sidebar
    statuses = []
    for i in range(len(questions)):
        a = answers[i] if i < len(answers) else None
        m = marked[i] if i < len(marked) else False
        v = visited[i] if i < len(visited) else False
        if a is not None and m:
            statuses.append('answered_marked')
        elif a is not None:
            statuses.append('answered')
        elif m:
            statuses.append('marked')
        elif v:
            statuses.append('skipped')
        else:
            statuses.append('unanswered')
    statuses[qid] = 'current' if statuses[qid] == 'unanswered' or statuses[qid] == 'skipped' else statuses[qid]

    elapsed_before = session.get('elapsed_before_pause', 0)
    start_time = session.get('start_time', time.time())

    return render_template(
        'question.html',
        question=q,
        qid=qid,
        correct=correct,
        submitted=submitted,
        selected_option=selected_option,
        total=len(questions),
        answered_count=answered_count,
        correct_count=correct_count,
        answers=answers,
        marked=marked,
        statuses=statuses,
        start_time=start_time,
        elapsed_before=elapsed_before,
    )


@app.route('/pause')
def pause_quiz():
    """Pause the quiz and remember the current question."""
    qid = request.args.get('qid', 0, type=int)
    # Accumulate elapsed time before pausing
    start = session.get('start_time', time.time())
    session['elapsed_before_pause'] = session.get('elapsed_before_pause', 0) + (time.time() - start)
    session['paused'] = True
    session['paused_qid'] = qid
    return redirect(url_for('paused'))


@app.route('/paused')
def paused():
    """Show the paused screen."""
    questions = session.get('questions', [])
    if not questions:
        return redirect(url_for('upload_file'))
    answers = session.get('answers', [])
    answered_count = sum(1 for a in answers if a is not None)
    correct_count = sum(1 for a in answers if a is not None and a['correct'])
    paused_qid = session.get('paused_qid', 0)
    return render_template(
        'paused.html',
        paused_qid=paused_qid,
        total=len(questions),
        answered_count=answered_count,
        correct_count=correct_count,
    )


@app.route('/results')
def results():
    """Show the final quiz results."""
    questions = session.get('questions', [])
    answers = session.get('answers', [])
    if not questions:
        return redirect(url_for('upload_file'))

    total = len(questions)
    answered = sum(1 for a in answers if a is not None)
    correct_count = sum(1 for a in answers if a is not None and a['correct'])
    incorrect_count = answered - correct_count
    unanswered = total - answered
    percentage = round((correct_count / total) * 100) if total else 0

    # Build per-question summary
    summary = []
    for i, (q, a) in enumerate(zip(questions, answers)):
        summary.append({
            'number': q['number'],
            'question': q['question'],
            'correct_answer': q['correct_answer'],
            'selected': a['selected_option'] if a else None,
            'is_correct': a['correct'] if a else None,
        })

    # Calculate total elapsed time
    elapsed = session.get('elapsed_before_pause', 0)
    start = session.get('start_time', time.time())
    if not session.get('paused'):
        elapsed += time.time() - start
    total_seconds = int(elapsed)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    return render_template(
        'results.html',
        total=total,
        answered=answered,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        unanswered=unanswered,
        percentage=percentage,
        summary=summary,
        time_hours=hours,
        time_minutes=minutes,
        time_seconds=seconds,
    )


@app.route('/restart')
def restart():
    """Clear the session and start fresh."""
    session.clear()
    return redirect(url_for('upload_file'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)


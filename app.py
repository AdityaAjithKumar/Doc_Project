from flask import Flask, render_template, request, redirect, url_for, session
import docx
import re
import os
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
    doc = docx.Document(file_path)
    questions = []
    current_question = None

    question_pattern = re.compile(r'^\d+\.\s')
    option_pattern = re.compile(r'^[A-D]\.')

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if question_pattern.match(text):  # New question
            if current_question:
                questions.append(current_question)
            current_question = {'question': text, 'options': [], 'answer': ''}
            i = 0  # Initialize the option counter
        elif option_pattern.match(text):  # Option
            if current_question:  # Ensure current_question is not None
                i += 1
                if i == 5:  # This means the next line is the explanation
                    current_question['answer'] = text
                else:
                    current_question['options'].append(text)
        elif text.startswith('✓'):  # Answer
            if current_question:  # Ensure current_question is not None
                current_question['answer'] = text

    if current_question:
        questions.append(current_question)

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
            session['answers'] = [None] * len(session['questions'])  # Initialize answers list
            return redirect(url_for('question', qid=0))
    return render_template('upload.html')


@app.route('/question/<int:qid>', methods=['GET', 'POST'])
def question(qid):
    questions = session.get('questions', [])
    answers = session.get('answers', [])
    if qid >= len(questions) or qid < 0:
        return redirect(url_for('upload_file'))

    question = questions[qid]
    correct = None
    explanation = None
    selected_option = None
    submitted = answers[qid] is not None

    if request.method == 'POST' and not submitted:
        selected_option = request.form.get('option')
        if selected_option:
            correct_option = question['answer'].split('.')[0].strip()[-1]  # Extract the correct option
            explanation = question['answer']
            correct = (selected_option == correct_option)
            answers[qid] = {'selected_option': selected_option, 'correct': correct, 'explanation': explanation}
            session['answers'] = answers  # Update session with answers
            return redirect(url_for('question', qid=qid))  # Reload the page to prevent resubmission

    if submitted:
        selected_option = answers[qid]['selected_option']
        correct = answers[qid]['correct']
        explanation = answers[qid]['explanation']

    return render_template('question.html', question=question, qid=qid, correct=correct, explanation=explanation,
                           submitted=submitted, selected_option=selected_option)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)), debug=True)


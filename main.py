from flask import Flask, render_template, request, redirect, url_for, session, request
from flask_mysqldb import MySQL
import MySQLdb.cursors
import MySQLdb.cursors, re, hashlib
import anthropic
import pandas as pd
import openai
app = Flask(__name__)
history = []
is_urgent = []

# Change this to your secret key (it can be anything, it's for extra protection)
app.secret_key = 'your secret key'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'pythonlogin'

# Intialize MySQL
mysql = MySQL(app)

# http://localhost:5000/pythonlogin/ - the following will be our login page, which will use both GET and POST requests
@app.route('/pythonlogin/admin', methods=['GET', 'POST'])
def login():
    # Output a message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in out database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

# http://localhost:5000/python/logout - this will be the logout page
@app.route('/pythonlogin/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

# http://localhost:5000/pythinlogin/register - this will be the registration page, we need to use both GET and POST requests
@app.route('/pythonlogin/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
                # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Hash the password
            hash = password + app.secret_key
            hash = hashlib.sha1(hash.encode())
            password = hash.hexdigest()
            # Account doesn't exist, and the form data is valid, so insert the new account into the accounts table
            cursor.execute('INSERT INTO accounts VALUES (NULL, %s, %s, %s)', (username, password, email,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

# http://localhost:5000/pythinlogin/home - this will be the home page, only accessible for logged in users
@app.route('/pythonlogin/home')
def home():
    # Check if the user is logged in
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('home.html', username=session['username'])
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


# http://localhost:5000/pythinlogin/profile - this will be the profile page, only accessible for logged in users
@app.route('/pythonlogin/profile')
def profile():
    # Check if the user is logged in
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not logged in redirect to login page
    return redirect(url_for('login'))


@app.route("/chat", methods=['GET', 'POST'])
def home_chat():
    answer = ""
    submitted_text = None
    global is_urgent

    if request.method == 'POST':
        submitted_text = request.form['textbox']
        answer = get_response(submitted_text)
        history.append((submitted_text, answer))
        if "Link zoom:" in answer:
            
            is_urgent.append("1")
        else:
            is_urgent=is_urgent
    
    return render_template("chat.html",urgent=len(is_urgent), message=history)
    
# Insert your environment key 
client = anthropic.Client(api_key="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")

def get_response(question):
  response = client.messages.create(
    model="claude-2.1",
    max_tokens= 216,
    system= 'You are a helpful telehealth assistant. Answer the following question and determine if the patient needs urgent medical attention. If so answer with URGENT ',
    messages=[
      {
        "role": "user",
        "content": question
      },
    ]
  )

  processed = response.content[0].text
  if "URGENT" in processed:
    processed = 'Link zoom:'
    return processed
  else:
    return processed


@app.route('/get_care_plan', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get the uploaded file
        file = request.files['file']
        
        # Load the file into a pandas DataFrame
        df = pd.read_excel(file)
        
        # Ensure the expected columns are present
        expected_columns = ["Age", "Gender", "Medical history", "Current medication", "Symptoms"]
        if not set(expected_columns).issubset(df.columns):
            return "The Excel file does not contain the expected columns."
        
        # Convert the DataFrame to a string representation
        file_content = df[expected_columns]
        care_planning = generate_care_plan(file_content)

        return render_template('plan.html', response=care_planning)
    return render_template('plan.html')
openai.api_key = "sk-proj-mzM0ZJDwQy9nKVzUpcNJT3BlbkFJvOYjxq9LCxng2k8qD9e2"

def generate_care_plan(data_row):
    prompt = (
        f"Based on the following patient data, generate a detailed care plan:\n\n"
        f"Age: {data_row['Age']}\n"
        f"Gender: {data_row['Gender']}\n"
        f"Medical history: {data_row['Medical history']}\n"
        f"Current medication: {data_row['Current medication']}\n"
        f"Symptoms: {data_row['Symptoms']}\n\n"
        f"The care plan should include:\n"
        f"- Medication name, quantity, frequency\n"
        f"- Measurements to take to check for potential problems and when to make them\n"
        f"- Estimated time to see improvements and what to measure to see it\n"
    )

    response = openai.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=200
    )
    care_plan = response.choices[0].text.strip()
    return care_plan

@app.route("/")
def main():
    return render_template('main.html')

@app.route('/plangen', methods=['GET'])
def plangen():
    return render_template('plangen.html')

@app.route('/submit', methods=['POST'])
def submit():
    input1 = request.form['input1']
    input2 = request.form['input2']
    input3 = request.form['input3']
    input4 = request.form['input4']
    input5 = request.form['input5']
    input6 = request.form['input6']

    prompt = (
        f"Based on the following patient data, generate a detailed care plan:\n\n"
        f"Age: {input1}\n"
        f"Gender: {input2}\n"
        f"Medical history: {input3}\n"
        f"Current medication: {input4}\n"
        f"Symptoms: {input5}\n"
        f"Remarks: {input6}\n\n"
        f"The care plan should include:\n"
        f"- Medication name, quantity, frequency\n"
        f"- Measurements to take to check for potential problems and when to make them\n"
        f"- Estimated time to see improvements and what to measure to see it\n"
    )

    try:
        response = client.messages.create(
            messages=[
                {
                "role":"user",
                "content": prompt
            },
            ],
            model="claude-2.1",
            max_tokens=1000
        )
        result = response.content[0].text
    except Exception as e:
        result = str(e)

    return render_template('result.html', result=result)

@app.route('/learn')
def learn():
    return render_template('learn.html')

@app.route('/generate_questions', methods=['POST'])
def generate_questions():
    subject = request.form['subject']
    
    prompt = f"Generate 5 to 10 detailed, factual, and educational questions for students studying {subject}. Ensure the questions are relevant to current medical knowledge and practices. Include a variety of question types, such as multiple choice, short answer, and case studies."
    completion = openai.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=200,
        stop =None,
        n=1,
    )
    questions = completion.choices[0].text.strip().split('\n')
    return render_template('learn.html', questions=questions)

@app.route('/analyze_answers', methods=['POST'])
def analyze_answers():
    questions = request.form.getlist('questions')
    answers = request.form.getlist('answers')
    
    prompt = (
        "You are a medical expert and an educator. Analyze the following answers provided by medical students "
        "and provide detailed feedback on each answer"
        "Questions and answers:\n"
    )
    for question, answer in zip(questions, answers):
        prompt += f"Q: {question}\nA: {answer}\n\n"

    completion = openai.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=512,
        stop =None,
    )
    analysis = completion.choices[0].text.strip()
    return render_template('result-learn.html', analysis=analysis)
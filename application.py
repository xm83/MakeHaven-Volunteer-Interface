from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


# Configure application
app = Flask(__name__)

# Ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use Postgre database
db = SQL("postgres://uiuxejrdxkdbwb:c2da924d03b01b3f4d2b45e6fb4a70dd6cb58641c966a4c5a0060657a4ada831@ec2-54-227-247-225.compute-1.amazonaws.com:5432/d7e2ctn6pjsu83")



@app.route("/")
@login_required
def index():
    admin = db.execute("SELECT admin, firstname FROM users WHERE id = :u", u=session["user_id"])

    # admin index page
    if admin[0]["admin"] == true:
        return render_template("admin_index.html", firstname=admin[0]["firstname"])

    # volunteer index page
    else:
        # Select all tasks that user signed up and hasn't checked in
        tasks = db.execute(
            "SELECT task, minutes FROM tasks WHERE user_id = :u AND active = 0", u=session["user_id"])
        info = db.execute("SELECT * FROM users WHERE id = :u", u=session["user_id"])

        # Select a random unclaimed task from tasks table
        suggestion = db.execute("SELECT * FROM tasks WHERE claimed = false ORDER BY RANDOM() LIMIT 1")

        # if no signed up tasks
        if not tasks:
            # if all tasks at MakeHaven have been claimed
            if not suggestion:
                return render_template("index_none_nosuggestion.html", firstname=info[0]["firstname"])
            else:
                return render_template("index_none.html", suggestion=suggestion, firstname=info[0]["firstname"])
        else:
            # if all tasks at MakeHaven have been claimed
            if not suggestion:
                return render_template("index_nosuggestion.html", task=tasks[0]["task"], duration=tasks[0]["minutes"], firstname=info[0]["firstname"])
            else:
                return render_template("index.html", suggestion=suggestion, task=tasks[0]["task"], duration=tasks[0]["minutes"], firstname=info[0]["firstname"])


@app.route("/rankings")
@login_required
def rankings():
    """Show rankings of users"""
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    users = db.execute("SELECT username, credit FROM users ORDER BY credit DESC")
    return render_template("rankings.html", users=users, admin=admin[0]["admin"])


@app.route("/signup", methods=["POST"])
@login_required
def signup():
    """lets user sign up for the task, add task for user"""
    # Get whatever task the user clicked on task page
    if request.method == "POST":
        # change chore in tasks to claimed as true and update matching user_id, sign_up date, username for said chore
        task = request.form.get("task")
        username = db.execute("SELECT username FROM users WHERE id = :i", i=session["user_id"])
        db.execute("UPDATE tasks SET claimed = true, user_id = :i, sign_up_date = :time, username = :u WHERE task = :t",
                   t=task, i=session["user_id"], time=datetime.now(), u=username[0]["username"])

        flash("Signed up!")
        return redirect("/user_info")


@app.route("/user_info")
@login_required
def user_info():
    """Show username, credit, & user's tasks"""
    user = db.execute(
        "SELECT * FROM users WHERE id = :u", u=session["user_id"])
    # Select the tasks that user signed up but hasn't checked in
    selected_tasks = db.execute(
        "SELECT * FROM tasks WHERE user_id = :u AND active = true", u=session["user_id"])

    if not selected_tasks:
        return redirect("/user_info_none")
    else:
        return render_template("user_info.html", user=user, tasks=selected_tasks, admin=user[0]["admin"])

@app.route("/user_info_none")
@login_required
def user_info_none():
    user = db.execute(
        "SELECT * FROM users WHERE id = :u", u=session["user_id"])
    return render_template("user_info_none.html", user=user, admin=user[0]["admin"])


@app.route("/admin_message_board", methods=["GET", "POST"])
@login_required
def admin_message_board():
    """Show admin display of message board"""
    forum = db.execute("SELECT * FROM forum WHERE admin= false AND approved = true ORDER BY post_time DESC")
    admin_messages = db.execute("SELECT * FROM forum WHERE admin= true ORDER BY post_time DESC")
    outstanding = db.execute("SELECT * FROM forum WHERE reviewed=false ORDER BY post_time")

    if request.method == "GET":
        return render_template("admin_message_board.html", forum=forum, admin_messages=admin_messages, outstanding=outstanding, notifications=admin_messages)
    elif request.method == "POST":
        # approve messages
        if request.form.get("approve"):
            # update entry to reviewed and approved in forum table
            db.execute("UPDATE forum SET reviewed = true, approved = true WHERE comment_id = :c", c=request.form.get("approve"))
            flash("approved message")
            return redirect("/admin_message_board")

        # delete messages
        elif request.form.get("delete"):
            # update entry to reviewed
            db.execute("UPDATE forum SET reviewed = true WHERE comment_id = :c", c=request.form.get("delete"))
            flash("user comment has been deleted")
            return redirect("/admin_message_board")

        # post admin notification
        elif request.form.get("message"):
            # get admin info from "users" table
            info = db.execute(
                "SELECT username, admin, firstname, lastname FROM users WHERE id = :i", i=session["user_id"])
            # add new admin message to "forum" table
            db.execute("INSERT INTO forum(user_id, comment, admin, username, firstname, lastname, approved, reviewed) VALUES (:s, :c, :a, :u, :f, :l, :r, :p)", s=session["user_id"], c=request.form.get(
                "message"), a=info[0]["admin"], u=info[0]["username"], f=info[0]["firstname"], l=info[0]["lastname"], r= true, p= true)
            flash("Added an admin notification")
            return redirect("/admin_message_board")

        # delete admin notification
        elif request.form.get("admin_delete"):
            # delete admin notification
            db.execute("DELETE FROM forum WHERE comment_id = :c", c=request.form.get("admin_delete"))
            flash("admin notification has been deleted")
            return redirect("/admin_message_board")


        else:
            flash("must click approve/reject button or submit a message")
            return redirect("/admin_message_board")




@app.route("/message_board", methods=["GET", "POST"])
@login_required
def message_board():
    """Show message board"""
    forum = db.execute("SELECT * FROM forum WHERE admin=false AND approved=true ORDER BY post_time DESC")
    admin_messages = db.execute("SELECT * FROM forum WHERE admin=true ORDER BY post_time DESC")


    if request.method == "GET":
        return render_template("message_board.html", forum=forum, admin_messages=admin_messages)
    elif request.method == "POST":
        # must provide message
        if not request.form.get("message"):
            flash("must provide a message")
            return render_template("message_board.html", forum=forum, admin_messages=admin_messages)

        else:
            # get info from "users" table
            info = db.execute(
                "SELECT username, admin, firstname, lastname FROM users WHERE id = :i", i=session["user_id"])

            # add new message to "forum" table
            db.execute("INSERT INTO forum(user_id, comment, admin, username, firstname, lastname) VALUES (:s, :c, :a, :u, :f, :l)", s=session["user_id"], c=request.form.get(
                "message"), a=info[0]["admin"], u=info[0]["username"], f=info[0]["firstname"], l=info[0]["lastname"])
            flash("Comment is sent and pending admin approval.")
            return redirect("/message_board")


@app.route("/checkin_none")
@login_required
def checkin_none():
    return render_template("checkin_none.html")


@app.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    """Add credit for user"""
    # Obtain a list of tasks that user signed up and hasn't checked in
    owned_tasks = db.execute("SELECT * FROM tasks WHERE user_id = :u AND active = 0",
                             u=session["user_id"])
    if request.method == "GET":
        # if user has not signed up for any tasks
        if not owned_tasks:
            return redirect("/checkin_none")
        else:
            return render_template("checkin.html", owned_tasks=owned_tasks)

    elif request.method == "POST":
        # Update checkin table
        db.execute("INSERT INTO checkin (user_id, task) VALUES (:user_id, :task)",
                   user_id=session["user_id"], task=request.form.get("task"))

        # Set task to inactive in tasks table
        db.execute("UPDATE tasks SET active = 1 WHERE task = :t", t=request.form.get("task"))

        # Update credit in users table
        old_credit = db.execute("SELECT credit FROM users WHERE id = :id", id=session["user_id"])
        gain = db.execute("SELECT task_score FROM tasks WHERE user_id= :user_id",
                          user_id=session["user_id"])
        new_credit = old_credit[0]["credit"] + gain[0]["task_score"]
        db.execute("UPDATE users SET credit = :new_credit WHERE id = :id",
                   new_credit=new_credit, id=session["user_id"])

        # Redirect user to user_info page
        flash("Checked in!")
        return redirect("/user_info")


@app.route("/admin_checkin", methods=["GET", "POST"])
@login_required
def admin_checkin():
    """Add credit for admin"""
    # Obtain a list of tasks that user signed up and hasn't checked in
    owned_tasks = db.execute("SELECT * FROM tasks WHERE user_id = :u AND active = 0",
                             u=session["user_id"])
    if request.method == "GET":
        # if user has not signed up for any tasks
        if not owned_tasks:
            return redirect("/checkin_none")
        else:
            return render_template("checkin.html", owned_tasks=owned_tasks)

    elif request.method == "POST":
        # Update checkin table
        db.execute("INSERT INTO checkin (user_id, task) VALUES (:user_id, :task)",
                   user_id=session["user_id"], task=request.form.get("task"))

        # Set task to nonactive in tasks table
        db.execute("UPDATE tasks SET active = 1 WHERE task = :t", t=request.form.get("task"))

        # Update credit in users table
        old_credit = db.execute("SELECT credit FROM users WHERE id = :id", id=session["user_id"])
        gain = db.execute("SELECT task_score FROM tasks WHERE user_id= :user_id",
                          user_id=session["user_id"])
        new_credit = old_credit[0]["credit"] + gain[0]["task_score"]
        db.execute("UPDATE users SET credit = :new_credit WHERE id = :id",
                   new_credit=new_credit, id=session["user_id"])

        # Redirect user to user_info page
        flash("Checked in!")
        return redirect("/admin_info")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return render_template("login.html")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return render_template("register.html")
        # Ensure first and last names were submitted
        if not request.form.get("firstname"):
            flash("must provide first name")
            return render_template("register.html")
        if not request.form.get("lastname"):
            flash("must provide last name")
            return render_template("register.html")
        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return render_template("register.html")
        # Ensure password confirmation was submitted
        elif not request.form.get("confirmation"):
            flash("must confirm password")
            return render_template("register.html")
        # Ensure password and confirmation match
        elif (request.form.get("password") != request.form.get("confirmation")):
            flash("password and confirmation must match")
            return render_template("register.html")
        # if all inputs are valid, hash user's password
        else:
            hash = generate_password_hash(request.form.get("password"))
            # add username and hash number into database
            result = db.execute("INSERT INTO users (username, hash, firstname, lastname) VALUES(:username, :hash, :firstname, :lastname)",
                                username=request.form.get("username"), hash=hash, firstname=request.form.get("firstname"), lastname=request.form.get("lastname"))
            if not result:
                flash("username already exists")
                return render_template("register.html")
        rows = db.execute("SELECT id FROM users WHERE username = :u",
                          u=request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        return redirect("/")


@app.route("/change_username", methods=["GET", "POST"])
@login_required
def change_username():
    """ Change Username """
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        return render_template("change_username.html", admin=admin[0]["admin"])
    elif request.method == "POST":
        # must provide username
        if not request.form.get("username"):
            flash("You must provide username.")
            return render_template("change_username.html", admin=admin[0]["admin"])
        # must provide password
        elif not request.form.get("password"):
            flash("You must provide your password")
            return render_template("change_username.html", admin=admin[0]["admin"])
        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username",
                              username=request.form.get("username"))

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                flash("invalid username and/or password, you are not authorized to change username")
                return render_template("change_username.html", admin=admin[0]["admin"])
            else:
                # must provide new_username
                if not request.form.get("new_username"):
                    flash("You must provide a new username")
                    return render_template("change_username.html", admin=admin[0]["admin"])
                # must confirm username
                elif not request.form.get("confirmation"):
                    flash("You must provide a confirmation for your new username")
                    return render_template("change_username.html", admin=admin[0]["admin"])
                # new_username and confirmation must match
                elif request.form.get("new_username") != request.form.get("confirmation"):
                    flash("Your new username and confirmation must match")
                    return render_template("change_username.html", admin=admin[0]["admin"])
                else:
                    # update username in database
                    db.execute("UPDATE users SET username = :u  WHERE id = :s",
                               u=request.form.get("new_username"), s=session["user_id"])
                    flash("Username changed sucessfully!")
                    return redirect("/user_info")


@app.route("/change_name", methods=["GET", "POST"])
@login_required
def change_name():
    """ Change Name """
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        return render_template("change_name.html", admin=admin[0]["admin"])
    elif request.method == "POST":
        # must provide username
        if not request.form.get("username"):
            flash("You must provide username.")
            return render_template("change_name.html", admin=admin[0]["admin"])
        # must provide password
        elif not request.form.get("password"):
            flash("You must provide your password.")
            return render_template("change_name.html", admin=admin[0]["admin"])
        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username",
                              username=request.form.get("username"))

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                flash("invalid username and/or password, you are not authorized to change username")
                return render_template("change_name.html", admin=admin[0]["admin"])
            else:
                # must provide a first name
                if not request.form.get("new_firstname"):
                    flash("You must input a first name.")
                    return render_template("change_name.html", admin=admin[0]["admin"])
                # must provide a last name
                elif not request.form.get("new_lastname"):
                    flash("You must input a last name.", 403)
                    return render_template("change_name.html", admin=admin[0]["admin"])
                # must confirm first name input
                elif not request.form.get("confirmation_first"):
                    flash("You must provide a confirmation for your new name.")
                    return render_template("change_name.html", admin=admin[0]["admin"])
                # must confirm last name input
                elif not request.form.get("confirmation_last"):
                    flash("You must provide a confirmation for your new name.")
                    return render_template("change_name.html", admin=admin[0]["admin"])
                elif request.form.get("new_firstname") != request.form.get("confirmation_first"):
                    flash("Your new name and confirmation must match")
                    return render_template("change_name.html", admin=admin[0]["admin"])
                elif request.form.get("new_lastname") != request.form.get("confirmation_last"):
                    flash("Your new name and confirmation must match")
                    return render_template("change_name.html", admin=admin[0]["admin"])
                else:
                    # update first and/or last name in database
                    db.execute("UPDATE users SET firstname = :firstname, lastname  = :lastname WHERE id = :s",
                               firstname=request.form.get("new_firstname"), lastname=request.form.get("new_lastname"), s=session["user_id"])
                    flash("Name changed sucessfully!")
                    return redirect("/user_info")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])

    if request.method == "GET":
        return render_template("change_password.html", admin=admin[0]["admin"])
    elif request.method == "POST":
        # must provide username
        if not request.form.get("username"):
            flash("You must provide username.")
            return render_template("change_password.html", admin=admin[0]["admin"])
        # must provide password
        elif not request.form.get("password"):
            flash("You must provide your password.")
            return render_template("change_password.html", admin=admin[0]["admin"])
        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = :username",
                              username=request.form.get("username"))

            # Ensure username exists and password is correct
            if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
                flash("invalid username and/or password, you are not authorized to change password")
                return render_template("change_password.html", admin=admin[0]["admin"])
            else:
                # must provide new password
                if not request.form.get("new_password"):
                    flash("You must provide a new password.")
                    return render_template("change_password.html", admin=admin[0]["admin"])
                # must provide password confirmation
                elif not request.form.get("confirmation"):
                    flash("You must provide a password confirmation.")
                    return render_template("change_password.html", admin=admin[0]["admin"])
                # new_password and confirmation must match
                elif request.form.get("new_password") != request.form.get("confirmation"):
                    flash("Your new password and confirmation must match")
                    return render_template("change_password.html", admin=admin[0]["admin"])
                else:
                    hash = generate_password_hash(request.form.get("new_password"))
                    # update users table
                    db.execute("UPDATE users SET hash = :h  WHERE id = :s",
                               h=hash, s=session["user_id"])
                    flash("Password changed sucessfully!")
                    return redirect("/user_info")


@app.route("/tasks", methods=["GET"])
@login_required
def tasks():
    """Show info about tasks"""
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    tasks = db.execute("SELECT * FROM tasks ORDER BY claimed DESC, start_date")
    if request.method == "GET":
        if not tasks:
            return redirect("/tasks_none")
        else:
            return render_template("tasks.html", tasks=tasks, admin=admin[0]["admin"])

@app.route("/add_tasks", methods=["GET", "POST"])
@login_required
def add_tasks():
    """Let admin add tasks"""
    existing_tasks = db.execute("SELECT task FROM tasks WHERE active = 0")

    if request.method == "GET":
        return render_template("add_tasks.html")
    elif request.method == "POST":
        # Ensure correct information was entered
        if not request.form.get("task"):
            flash("Must provide a task title.")
            return render_template("add_tasks.html")
        elif not request.form.get("task_description"):
            flash("Must provide task description")
            return render_template("add_tasks.html")
        elif not request.form.get("minutes"):
            flash("Must provide number of minutes task takes.")
            return render_template("add_tasks.html")
        elif not request.form.get("task_score"):
            flash("Must provide task score")
            return render_template("add_tasks.html")
        elif not request.form.get("start_date"):
            flash("Must provide start date")
            return render_template("add_tasks.html")
        for dict in existing_tasks:
            if request.form.get("task") in dict['task']:
                flash("Task already exists, provide a different task name")
                return render_template("add_tasks.html")

        db.execute("INSERT INTO tasks(task, minutes, task_score, task_description, task_score, recurrence_cycle, start_date) VALUES(:t, :m, :n, :d, :s, :r, :e)",
            t=request.form.get("task"), m=request.form.get("minutes"), n=request.form.get("task_score"), d=request.form.get("task_description"), s=request.form.get("task_score"), r=request.form.get("recurrence_cycle"), e=request.form.get("start_date"))
        flash("Added task")
        return redirect("/add_tasks")

@app.route("/remove_tasks", methods=["GET", "POST"])
@login_required
def remove_tasks():
    """Let admin remove tasks"""
    tasks = db.execute("SELECT * FROM tasks ORDER BY claimed DESC, start_date")
    if request.method == "GET":
        if not tasks:
            return redirect("/tasks_none")
        else:
            return render_template("remove_tasks.html", tasks=tasks)
    elif request.method == "POST":
        db.execute("DELETE FROM tasks WHERE task = :t", t=request.form.get("task"))
        flash("removed task")
        return redirect("/remove_tasks")


@app.route("/taskstoday", methods=["GET"])
@login_required
def taskstoday():
    """Show info about tasks that start today"""
    taskstoday = db.execute(
        "SELECT * FROM tasks WHERE start_date = CURRENT_DATE ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not taskstoday:
            return redirect("/tasks_none")
        else:
            return render_template("taskstoday.html", tasks=taskstoday, admin=admin[0]["admin"])


@app.route("/tasks3days", methods=["GET"])
@login_required
def tasks3days():
    """Show info about tasks with start date within 3 days"""
    date1 = date.today() + timedelta(3)
    date2 = date.today() - timedelta(3)
    tasks3days = db.execute(
        "SELECT * FROM tasks WHERE :t2 <= start_date AND start_date <= :t1 ORDER BY claimed DESC", t2=date2, t1=date1)
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks3days:
            return redirect("/tasks_none")
        else:
            return render_template("tasks3days.html", tasks=tasks3days, admin=admin[0]["admin"])


@app.route("/tasks7days", methods=["GET"])
@login_required
def tasks7days():
    """Show info about tasks with start date within a week"""
    date3 = date.today() + timedelta(7)
    date4 = date.today() - timedelta(7)
    tasks7days = db.execute(
        "SELECT * FROM tasks WHERE :t2 <= start_date AND start_date <= :t1 ORDER BY claimed DESC", t2=date4, t1=date3)
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks7days:
            return redirect("/tasks_none")
        else:
            return render_template("tasks7days.html", tasks=tasks7days, admin=admin[0]["admin"])


@app.route("/tasksmonth", methods=["GET"])
@login_required
def tasksmonth():
    """Show info about tasks with start date within a month"""
    date5 = datetime.today() + relativedelta(months=1)
    date6 = datetime.today() - relativedelta(months=1)
    tasksmonth = db.execute(
        "SELECT * FROM tasks WHERE :t2 <= start_date AND start_date <= :t1 ORDER BY claimed DESC", t2=date6, t1=date5)
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasksmonth:
            return redirect("/tasks_none")
        else:
            return render_template("tasksmonth.html", tasks=tasksmonth, admin=admin[0]["admin"])


@app.route("/tasksmonths", methods=["GET"])
@login_required
def tasksmonths():
    """Show info about tasks with start date within more than a month"""
    date5 = datetime.today() + relativedelta(months=1)
    date6 = datetime.today() - relativedelta(months=1)
    tasksmonths = db.execute(
        "SELECT * FROM tasks WHERE :t2 >= start_date OR start_date >= :t1 ORDER BY claimed DESC", t2=date6, t1=date5)
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasksmonths:
            return redirect("/tasks_none")
        else:
            return render_template("tasksmonths.html", tasks=tasksmonths, admin=admin[0]["admin"])


@app.route("/tasks_none", methods=["GET"])
@login_required
def tasks_none():
    """Display That No Tasks is Found With This Condition."""
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    return render_template("tasks_none.html", tasks=tasks_none, admin=admin[0]["admin"])


@app.route("/tasks5min", methods=["GET"])
@login_required
def tasks5min():
    """Show info about tasks < 5 min"""
    tasks5min = db.execute("SELECT * FROM tasks WHERE minutes <= 5 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks5min:
            return redirect("/tasks_none")
        else:
            return render_template("tasks5min.html", tasks=tasks5min, admin=admin[0]["admin"])


@app.route("/tasks10min", methods=["GET"])
@login_required
def tasks10min():
    """Show info about tasks between 5 and 10 min"""
    tasks10min = db.execute(
        "SELECT * FROM tasks WHERE minutes <= 10 AND minutes >= 5 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks10min:
            return redirect("/tasks_none")
        else:
            return render_template("tasks10min.html", tasks=tasks10min, admin=admin[0]["admin"])


@app.route("/tasks20min", methods=["GET"])
@login_required
def tasks20min():
    tasks20min = db.execute(
        "SELECT * FROM tasks WHERE minutes <= 20 AND minutes >= 10 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks20min:
            return redirect("/tasks_none")
        else:
            return render_template("tasks20min.html", tasks=tasks20min, admin=admin[0]["admin"])


@app.route("/tasks30min", methods=["GET"])
@login_required
def tasks30min():
    tasks30min = db.execute(
        "SELECT * FROM tasks WHERE minutes <= 30 AND minutes >= 20 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks30min:
            return redirect("/tasks_none")
        else:
            return render_template("tasks30min.html", tasks=tasks30min, admin=admin[0]["admin"])


@app.route("/tasks40min", methods=["GET"])
@login_required
def tasks40min():
    tasks40min = db.execute("SELECT * FROM tasks WHERE minutes >= 30 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks40min:
            return redirect("/tasks_none")
        else:
            return render_template("tasks40min.html", tasks=tasks40min, admin=admin[0]["admin"])


@app.route("/tasks1", methods=["GET"])
@login_required
def tasks1():
    """Show info about tasks with credit score 1"""
    tasks1 = db.execute("SELECT * FROM tasks WHERE task_score =1 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks1:
            return redirect("/tasks_none")
        else:
            return render_template("tasks1.html", tasks=tasks1, admin=admin[0]["admin"])


@app.route("/tasks2", methods=["GET"])
@login_required
def tasks2():
    tasks2 = db.execute("SELECT * FROM tasks WHERE task_score=2 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks2:
            return redirect("/tasks_none")
        else:
            return render_template("tasks2.html", tasks=tasks2, admin=admin[0]["admin"])


@app.route("/tasks3", methods=["GET"])
@login_required
def tasks3():
    tasks3 = db.execute("SELECT * FROM tasks WHERE task_score=3 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks3:
            return redirect("/tasks_none")
        else:
            return render_template("tasks3.html", tasks=tasks3, admin=admin[0]["admin"])


@app.route("/tasks4", methods=["GET"])
@login_required
def tasks4():
    tasks4 = db.execute("SELECT * FROM tasks WHERE task_score=4 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks4:
            return redirect("/tasks_none")
        else:
            return render_template("tasks4.html", tasks=tasks4, admin=admin[0]["admin"])


@app.route("/tasks5", methods=["GET"])
@login_required
def tasks5():
    tasks5 = db.execute("SELECT * FROM tasks WHERE task_score=5 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks5:
            return redirect("/tasks_none")
        else:
            return render_template("tasks5.html", tasks=tasks5, admin=admin[0]["admin"])


@app.route("/tasks6", methods=["GET"])
@login_required
def tasks6():
    tasks6 = db.execute("SELECT * FROM tasks WHERE task_score>5 ORDER BY claimed DESC")
    admin = db.execute("SELECT admin FROM users WHERE id = :u", u = session["user_id"])
    if request.method == "GET":
        if not tasks6:
            return redirect("/tasks_none")
        else:
            return render_template("tasks6.html", tasks=tasks6, admin=admin[0]["admin"])


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

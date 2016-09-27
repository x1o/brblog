from flask import Flask, g, render_template, request, session, redirect, \
                  url_for, flash, abort
from hashlib import sha256
from base64 import b64encode
import sqlite3
from flaskext.markdown import Markdown

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
md = Markdown(app)

# app.config.from_object(__name__)
app.config.from_pyfile('config.py')

# def init_db(db_file):
   # return sqlite3.connect(db_file)

# def get_db():
    # if not hasattr(g, 'db'):
        # g.db = init_db(app.config['DB_FILE'])
    # return g.db

@app.before_request
def init_db():
    if not hasattr(g, 'db'):
        import os
        project_root = os.path.dirname(os.path.realpath(__file__))
        db_fn = os.path.join(project_root, app.config['DB_FILE'])
        g.db = sqlite3.connect(db_fn)
        g.db.row_factory = sqlite3.Row
        g.db.execute('pragma foreign_keys = on')

@app.teardown_appcontext
def teardown_db(exception):
    if hasattr(g, 'db'):
        g.db.close()

# def query_db(query, args=(), one=False):
    # rv = get_db().execute(query, args).fetchall()
    # return (rv[0] if rv else None) if one else rv

def make_pw_digest(plain):
    return b64encode(sha256(plain).digest())

def is_valid_cred(pw):
    if make_pw_digest(pw) == app.config['PASSWORD_DIGEST']:
        return True
    else:
        return False

def back(default_page='show_n_posts'):
    ref = getattr(request, 'referrer', url_for(default_page))
    if not ref:
        ref = url_for(default_page)   # duh
    return redirect(ref)

# I'm a little ashamed.
def hour_to_pod(hour):
    """Gives each hour the name of its corresponding part of the day."""
    hour = int(hour)
    if hour >= 23 or hour <= 1:
        pod = 'around midnight'
    elif hour > 1 and hour <= 6:
        pod = 'night'
    elif hour > 6 and hour < 11:
        pod = 'morning'
    elif hour >= 11 and hour <= 13:
        pod = 'around noon'
    elif hour > 13 and hour < 18:
        pod = 'daytime'
    elif hour >= 18 and hour < 23:
        pod = 'evening'
    else:
        pod = '%s has noname!' % hour
    return pod

@app.route('/')
@app.route('/<from_p>~<to_p>')
def show_n_posts(from_p='last', to_p='-%s' % (app.config['POSTS_PER_PAGE'] - 1)):
    def args_error(msg=''):
        err_msg = 'Invalid arguments to show_n_posts: %s, %s %s' % (from_p, to_p, msg)
        flash(err_msg, 'error')
        app.logger.warning(err_msg)
        return redirect(url_for('show_n_posts'))
    order = 'desc'
    last_p = g.db.execute('select max(pId) from PostFull').fetchone()[0]
    if from_p == 'last':
        from_p = last_p
    try:
        try:
            from_p = int(from_p)
        except TypeError: # from_p is None
            return render_template('show_fresh_site.html')
        to_p = int(to_p)
        if from_p <= 0:
            return args_error('(first argument should be greater than zero)')
        if to_p < 0:
            if abs(to_p) >= abs(from_p):
                to_p = 1
            else:
                to_p = from_p + to_p
        if from_p < to_p:
            order = 'asc'
        else:
            temp = from_p
            from_p = to_p
            to_p = temp
    except ValueError:
        return args_error()
    posts = g.db.execute('''select * from PostFull
                            where pId >= ? and pId <= ?
                            order by pId %s''' % order,
                         (str(from_p), str(to_p))).fetchall()
    # not sure if that's the best way to do it
    posts = [dict(zip(post.keys(), post)) for post in posts]
    for p in posts:
        (date, time, hour) = g.db.execute('''select date(postDate),
                                                    time(postDate),
                                                    strftime('%H', postDate)
                                             from PostFull
                                             where pId = ?''',
                                    [str(p['pId'])]).fetchone()
        comment_count = g.db.execute('''select count(*)
                                        from Comment
                                        where pId = ?''',
                                     [str(p['pId'])]).fetchone()[0]
        p['date'] = date
        p['time'] = time
        p['pod_name'] = hour_to_pod(hour)
        p['comment_count'] = comment_count
    return render_template('show_n_posts.html',
                           posts=posts,
                           from_p=from_p,
                           to_p=to_p,
                           last_p=last_p)

@app.route('/<int:pId>')
def show_post(pId):
    pId = str(pId)
    post = g.db.execute('select * from PostFull where pId = ?', (pId,)).fetchone()
    if not post['isVisible'] and not session.get('logged_in'):
        return render_template('sorry_hidden.html', entry_type='post')
    comments = g.db.execute('select * from CommentFull where pId = ?', (pId,))
    return render_template('show_post.html',
                           post=post,
                           comments=comments)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if is_valid_cred(request.form['password']):
            session['logged_in'] = True
            flash('Welcome home.', 'ok')
            # ref = getattr(request, 'referrer', url_for('show_n_posts'))
            ref = url_for('show_n_posts')
            return redirect(ref)
        else:
            flash('(suspiciously) That is not correct...  Are you to try again, sir?', 'error')
            return redirect(url_for('login'))
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    if session.get('logged_in'):
        flash('Goodbye and see you again.', 'ok')
        session.pop('logged_in', None)
    else:
        flash("You weren't logged in, you know?  Logging out doesn't make sense.")
    return back()

# should be splitted into two function operating on different methods perhaps
@app.route('/new', methods=['GET', 'POST'])
def add_post():
    if request.method == 'GET':
        if session.get('logged_in'):
            return render_template('add_post.html')
        else:
            flash('One has to be logged-in in order to post', 'info')
            return redirect(url_for('login'))
    else:
        if not session.get('logged_in'):
            abort(401)
        if not request.form['body']:
            flash('Please, type some content in...', 'error')
            return redirect(url_for('add_post'))
        insert_q = '''insert into PostFull (pId, title, body, postDate, isVisible)
                      values (null, ?, ?, datetime('now', ?), ?)'''
        g.db.execute(insert_q, (request.form['subject'],
                                request.form['body'],
                                app.config['TIME_ADJ'],
                                request.form['is_visible']))
        g.db.commit()
        max_pId = str(g.db.execute('select max(pId) from PostFull').fetchone()[0])
        return redirect('/'+max_pId)

@app.route('/<int:pId>/unhide')
@app.route('/<int:pId>/hide')
def hide_post(pId):
    """Toggle post.isVisible state."""
    if not session.get('logged_in'):
        flash("You don't seem to be logged in; can't hide the post.", 'error')
        return back()
    pId = str(pId)
    title = g.db.execute('select title from PostFull where pId = ?', (pId,)).fetchone()[0]
    cur = g.db.execute('select isVisible from PostFull where pId = ?', (pId,)).fetchone()[0]
    g.db.execute('update PostFull set isVisible = ? where pId = ?',
                  (str((cur + 1) % 2), pId))
    g.db.commit()
    if cur == 1:
        action = 'hidden'
    else:
        action = 'unhidden'
    if title:
        msg = 'Blog post "%s" has been %s.' % (title, action)
    else:
        msg = 'Untitled blog post #%s has been %s.' % (pId, action)
    flash(msg, 'ok')
    return back()

@app.route('/<int:pId>/kill')
def kill_post(pId):
    if not session.get('logged_in'):
        flash("Only the blog's owner can kill. Sorry :-(", 'error')
        return back()
    title = g.db.execute('select title from PostFull where pId = ?', (pId,)).fetchone()[0]  # this is getting on my nerves
    g.db.execute('delete from PostFull where pId = ?', (str(pId),))
    g.db.commit()
    if title:
        msg = 'Deleted blog post "%s".  The less STUFF the better!' % title
    else:
        msg = 'Deleted the untitled blog post #%s.' % pId
    flash(msg, 'ok')
    return back()

# This is pretty useless in fact.
@app.route('/<int:pId>/<int:cId>')
def show_comment(pId, cId):
    comment = g.db.execute('select * from CommentFull where pId = ? and cId = ?',
                           (pId, cId)).fetchone()
    if not comment['isVisible'] and not session.get('logged_in'):
        return render_template('sorry_hidden.html', entry_type='comment')
    post_title = g.db.execute('select title from PostFull where pId = ?',
                             (pId,)).fetchone()[0]
    return render_template('show_comment.html',
                            comment=comment,
                            post_title=post_title)

@app.route('/<int:pId>/new', methods=['GET', 'POST'])
def add_comment(pId):
    if request.method == 'GET':
        return render_template('add_comment.html')
    else:
        if not request.form['body']:
            flash('Empty comments are no good.', 'error')
            return redirect(url_for('add_comment', pId=pId))
        insert_q = '''insert into CommentFull
                      (pId, cId, title, body, postDate, isVisible, author, mark)
                      values (?, ?, ?, ?, datetime('now', ?), 1, ?, null)'''
        cId = g.db.execute('''select ifnull((select max(cId) from CommentFull
                                            where pId = ?), 0)''',
                          (pId,)).fetchone()[0]
        cId += 1
        g.db.execute(insert_q, (pId,
                               cId,
                               request.form['subject'],
                               request.form['body'],
                               app.config['TIME_ADJ'],
                               request.form['author']))
        g.db.commit()
        return redirect('/'+str(pId))

@app.errorhandler(404)
def page_not_found(error):
    return (render_template('404.html',
                            error=error),
            404)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)

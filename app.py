from flask import Flask, escape, url_for, request, render_template
from flask import redirect, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user
from flask_login import login_required, logout_user, current_user
import os, time
import click
#!usr/bin/python3
# -*- coding: utf-8 -*-
app = Flask(__name__)
# app.send_file_max_age_default = timedelta(seconds=1)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 关闭对模型修改的监控
app.config['SECRET_KEY'] = 'dev' # 等同于 app.secret_key = 'dev'
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
# app.config['SQLALCHEMY_DATABASE_URI'] = prefix + os.path.join(os.path.dirname(app.root_path), os.getenv('DATABASE_FILE', 'data.db'))
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = timedelta(seconds=1)
# 这个不是很理解
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

src_dir='coderepo'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True) 
    name = db.Column(db.String(20))
    username = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    year = db.Column(db.String(10))

###
class Code(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    index = db.Column(db.Integer)
    context = db.Column(db.Text(2000))
###

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user

@app.cli.command()
@click.option('--username', prompt=True, help='the username used to login')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login')
def admin(username, password):
    """Create user"""
    db.create_all()
    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)
    else :
        click.echo('Create user...')
        user = User(username=username, name='Admin')
        user.set_password(password)
        db.session.add(user)
    db.session.commit()
    click.echo('admin over')

app.cli.command()
@click.option('--drop', is_flag=True, help='Create after drop')
def initdb(drop):
    if(drop):
        db.drop_all()
    db.create_all()
    click.echo('Initialized database')

@app.cli.command()
def forge():
    """fake data"""
    db.create_all()
    name = 'frostant'
    movies = [
        {'title':'My love','year':'2000'},
        {'title':'My frost','year':'2001'},
        {'title':'My dream','year':'2002'},
        {'title':'My her','year':'2003'},
    ]
    user = User(name=name)
    db.session.add(user)
    for m in movies:
        movie = Movie(title=m['title'], year=m['year'])
        db.session.add(movie)
    
    db.session.commit()
    click.echo('Done')

@app.context_processor
def inject_user():
    user = User.query.first()
    return dict(user=user)
# 相当于全局变量

@app.errorhandler(404)
def  page_not_found(e):
    return render_template('404.html'),404

@app.route('/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']
        if not name:
            flash('Invalid name')
            return redirect(url_for('settings'))
        current_user.name = name
        db.session.commit()
        flash('settings updated')
        return redirect(url_for('index'))
    return render_template('settings.html')

@app.route('/search/<string:get_paste>',methods=['GET', 'POST'])
@login_required
def search(get_paste):
    # if get_paste:
    #     return render_template('search.html', hash_key=hash_key)
    if request.method == 'POST':
        # if not hash_key:
        hash_key = request.form['name']
        filename = os.path.join(src_dir, hash_key+'.txt')
        if not os.path.exists(filename):
            flash('the filename is Invalid')
            return render_template('search.html', hash_key=hash_key)
        else :
            with open(filename) as file_obj:
                codes = file_obj.read()
        return render_template('search.html', hash_key=hash_key, codes=codes)
    return render_template('search.html', hash_key=get_paste)

# 给你一个文本框，你输入ID，然后我去文件夹里找这个文件，并把内容输入到页面上

@app.route('/paste', methods=['GET', 'POST'])
@login_required
def paste():
    hash_key='empty'
    if request.method == 'POST':
        codes = request.form['content']
        hash_key = abs(hash(str(time.time())+request.form['name']))
        hash_str = str(hash_key)
        if hash_key and codes :
            filename = os.path.join(src_dir, hash_str+'.txt')
            flash('valid pasted')
            with open(filename,'a') as file_handle:
                file_handle.write(codes)
            print(hash_key)
            
            # return render_template('search.html', hash_key=hash_key) 
            return redirect(url_for('search', get_paste=hash_str))
        flash('Invalid operater')
        return render_template('paste.html') 
        # redirect(url_for('paste'))
    return render_template('paste.html', hash_key=hash_key)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Invalid user')
            return redirect(url_for('login'))
        
        user = User.query.first()
        if username == user.username and user.validate_password(password):
            login_user(user)
            flash('login success')
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('you are logout')
    return redirect(url_for('index'))

@app.route('/movie/edit/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)

    if request.method == 'POST':
        title = request.form['title']
        year = request.form['year']

        if not title or not year or len(year)>4:
            flash('Invalid change')
            return redirect(url_for('edit',movie_id=movie_id))
        movie.title = title
        movie.year = year
        db.session.commit()
        flash('Item updated')
        return redirect(url_for('index'))
    return render_template('edit.html',movie=movie)

@app.route('/movie/delete/<int:movie_id>', methods=['GET', 'POST'])
@login_required
def delete(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    db.session.delete(movie)
    db.session.commit()
    flash('Item deleted')
    return redirect(url_for('index'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        title = request.form.get('title')
        year = request.form.get('year')
        if not title or not year or len(year) >4:
            flash('Invalid input. ')
            return redirect(url_for('index'))
        movie = Movie(title=title, year=year)
        db.session.add(movie)
        db.session.commit()
        flash('Item created')
        return redirect(url_for('index'))

    user = User.query.first()
    movies = Movie.query.all()
    return render_template('index.html',movies=movies)

if __name__ == '__main__':
    app.run()
    # app.run(host='0.0.0.0', port=80)

from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import io
import pandas as pd

app = Flask(__name__)
app.secret_key = 'segredo123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///concurso.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)

class Candidato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    cpf = db.Column(db.String(20), unique=True)
    data_nascimento = db.Column(db.String(20))
    sexo = db.Column(db.String(20))
    nacionalidade = db.Column(db.String(50))
    naturalidade = db.Column(db.String(50))

    nome_responsavel = db.Column(db.String(100))
    cpf_responsavel = db.Column(db.String(20))
    parentesco = db.Column(db.String(50))
    telefone_responsavel = db.Column(db.String(30))
    email_responsavel = db.Column(db.String(100))

    cep = db.Column(db.String(10))
    endereco = db.Column(db.String(200))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(100))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))

    colegio = db.Column(db.String(100))
    senha = db.Column(db.String(100))

    doc_identidade = db.Column(db.String(200))
    doc_responsavel = db.Column(db.String(200))
    comprovante_residencia = db.Column(db.String(200))
    declaracao_escolar = db.Column(db.String(200))
    foto = db.Column(db.String(200))

    pago = db.Column(db.Boolean, default=False)
    respostas = db.Column(db.String(100))
    nota = db.Column(db.Float)
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)

class Gabarito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    respostas = db.Column(db.String(100))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/inscricao', methods=['GET', 'POST'])
def inscricao():
    if request.method == 'POST':
        f = request.form
        files = request.files

        candidato = Candidato(
            nome=f['nome'],
            cpf=f['cpf'],
            data_nascimento=f['data_nascimento'],
            sexo=f['sexo'],
            nacionalidade=f['nacionalidade'],
            naturalidade=f['naturalidade'],
            nome_responsavel=f['nome_responsavel'],
            cpf_responsavel=f['cpf_responsavel'],
            parentesco=f['parentesco'],
            telefone_responsavel=f['telefone_responsavel'],
            email_responsavel=f['email_responsavel'],
            cep=f['cep'],
            endereco=f['endereco'],
            numero=f['numero'],
            complemento=f['complemento'],
            bairro=f['bairro'],
            cidade=f['cidade'],
            estado=f['estado'],
            colegio=f['colegio'],
            senha=f['senha']
        )

        doc_path = app.config['UPLOAD_FOLDER']
        candidato.doc_identidade = salvar_arquivo(files['doc_identidade'], doc_path)
        candidato.doc_responsavel = salvar_arquivo(files['doc_responsavel'], doc_path)
        candidato.comprovante_residencia = salvar_arquivo(files['comprovante_residencia'], doc_path)
        candidato.declaracao_escolar = salvar_arquivo(files['declaracao_escolar'], doc_path)
        candidato.foto = salvar_arquivo(files['foto'], doc_path)

        db.session.add(candidato)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('inscricao.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cpf = request.form['cpf']
        senha = request.form['senha']
        user = Candidato.query.filter_by(cpf=cpf, senha=senha).first()
        if user:
            session['candidato_id'] = user.id
            return redirect(url_for('painel_candidato'))
    return render_template('login.html')

@app.route('/painel')
def painel_candidato():
    cid = session.get('candidato_id')
    if not cid:
        return redirect(url_for('login'))
    c = Candidato.query.get(cid)
    return render_template('painel_candidato.html', candidato=c)

@app.route('/pagar')
def pagar():
    cid = session.get('candidato_id')
    if not cid:
        return redirect(url_for('login'))
    c = Candidato.query.get(cid)
    c.pago = True
    db.session.commit()
    return redirect(url_for('painel_candidato'))

@app.route('/prova', methods=['GET', 'POST'])
def prova():
    cid = session.get('candidato_id')
    if not cid:
        return redirect(url_for('login'))
    if request.method == 'POST':
        respostas = request.form['respostas']
        c = Candidato.query.get(cid)
        c.respostas = respostas.upper()
        db.session.commit()
        return redirect(url_for('painel_candidato'))
    return render_template('prova.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        user = request.form['user']
        pwd = request.form['pwd']
        if user == 'admin' and pwd == '123':
            session['admin'] = True
            return redirect(url_for('painel_admin'))
    return render_template('admin_login.html')

@app.route('/painel_admin')
def painel_admin():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    candidatos = Candidato.query.all()
    return render_template('painel_admin.html', candidatos=candidatos)

@app.route('/lancar_gabarito', methods=['GET', 'POST'])
def lancar_gabarito():
    if request.method == 'POST':
        respostas = request.form['respostas'].upper()
        g = Gabarito.query.first()
        if not g:
            g = Gabarito(respostas=respostas)
            db.session.add(g)
        else:
            g.respostas = respostas
        db.session.commit()
        return redirect(url_for('painel_admin'))
    return render_template('gabarito.html')

@app.route('/corrigir')
def corrigir():
    gabarito = Gabarito.query.first()
    if gabarito:
        for c in Candidato.query.all():
            if c.respostas:
                acertos = sum([1 for a, b in zip(c.respostas, gabarito.respostas) if a == b])
                c.nota = acertos
        db.session.commit()
    return redirect(url_for('painel_admin'))

@app.route('/exportar')
def exportar():
    candidatos = Candidato.query.all()
    dados = [{'Nome': c.nome, 'CPF': c.cpf, 'Nota': c.nota, 'Pago': c.pago} for c in candidatos]
    df = pd.DataFrame(dados)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Notas')
    output.seek(0)
    return send_file(output, download_name="resultados.xlsx", as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

def salvar_arquivo(file, pasta):
    if file and file.filename:
        path = os.path.join(pasta, secure_filename(file.filename))
        file.save(path)
        return path
    return None
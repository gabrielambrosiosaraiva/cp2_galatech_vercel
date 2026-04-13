from flask import Flask, render_template, request
import os
import oracledb

app = Flask(__name__)

DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_DSN = os.environ["DB_DSN"]


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/inscrever', methods=['POST'])
def inscrever():
    nome = request.form.get('nome')
    email = request.form.get('email')
    tipo = request.form.get('tipo')
    prioridade = request.form.get('prioridade')

    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )

        cursor = conn.cursor()

        # teste inicial
        print("Conectado ao Oracle com sucesso")

        conn.commit()
        cursor.close()
        conn.close()

        mensagem = f'Inscrição de {nome} realizada com sucesso!'

    except oracledb.DatabaseError as e:
        mensagem = f'Erro Oracle: {str(e)}'

    return render_template('index.html', mensagem=mensagem)


if __name__ == '__main__':
    app.run(debug=True)
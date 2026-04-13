from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/inscrever', methods=['POST'])
def inscrever():
    nome = request.form.get('nome')
    email = request.form.get('email')
    tipo = request.form.get('tipo')
    prioridade = request.form.get('prioridade')

    # Aqui depois vamos conectar Oracle + PL/SQL
    print(nome, email, tipo, prioridade)

    return render_template(
        'index.html',
        mensagem=f'Inscrição de {nome} realizada com sucesso!'
    )


if __name__ == '__main__':
    app.run(debug=True)
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

    # Definir valor com base no tipo
    if tipo == "Ingresso Normal":
        valor_pago = 300
    elif tipo == "Ingresso VIP":
        valor_pago = 800
    else:
        valor_pago = 1200

    conn = None
    cursor = None
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        cursor = conn.cursor()

        # Primeiro insere o usuário se não existir
        cursor.execute("""
            MERGE INTO TB_CP2_USUARIOS u
            USING (SELECT :nome AS nome_usuario, :email AS email_usuario, :prioridade AS prioridade_usuario FROM dual) src
            ON (u.email_usuario = src.email_usuario)
            WHEN NOT MATCHED THEN
                INSERT (nome_usuario, email_usuario, prioridade_usuario, saldo_usuario)
                VALUES (src.nome_usuario, src.email_usuario, src.prioridade_usuario, 0)
        """, {"nome": nome, "email": email, "prioridade": prioridade})

        # Pegar id_usuario
        cursor.execute("SELECT id_usuario FROM TB_CP2_USUARIOS WHERE email_usuario = :email", {"email": email})
        id_usuario = cursor.fetchone()[0]

        # Inserir inscrição como WAITLIST
        cursor.execute("""
            INSERT INTO TB_CP2_INSCRICOES (id_usuario, id_evento, status_inscricao, valor_pago, tipo_inscricao)
            VALUES (:id_usuario, 1, 'WAITLIST', :valor, :tipo)
        """, {"id_usuario": id_usuario, "valor": valor_pago, "tipo": tipo})

        conn.commit()
        mensagem = f"Inscrição de {nome} realizada com sucesso!"
    except oracledb.DatabaseError as e:
        error, = e.args
        mensagem = f"Erro Oracle: {error.code} - {error.message}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('index.html', mensagem=mensagem)

@app.route('/processar_fila', methods=['POST'])
def processar_fila():
    conn = None
    cursor = None
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        cursor = conn.cursor()

        plsql_block = """
        DECLARE
            CURSOR c_inscricoes IS
                SELECT id_inscricao, id_usuario, tipo_inscricao
                FROM TB_CP2_INSCRICOES
                WHERE status_inscricao = 'WAITLIST'
                ORDER BY id_inscricao;

            v_id_inscricao TB_CP2_INSCRICOES.id_inscricao%TYPE;
            v_id_usuario   TB_CP2_INSCRICOES.id_usuario%TYPE;
            v_tipo         TB_CP2_INSCRICOES.tipo_inscricao%TYPE;
        BEGIN
            OPEN c_inscricoes;
            LOOP
                FETCH c_inscricoes INTO v_id_inscricao, v_id_usuario, v_tipo;
                EXIT WHEN c_inscricoes%NOTFOUND;

                IF v_tipo IN ('Ingresso Platinum','Ingresso VIP') THEN
                    UPDATE TB_CP2_INSCRICOES
                    SET status_inscricao = 'CONFIRMADA'
                    WHERE id_inscricao = v_id_inscricao;

                    INSERT INTO TB_CP2_LOG_AUDITORIA (id_inscricao, motivo_log)
                    VALUES (v_id_inscricao, 'Promoção automática da fila de espera');
                END IF;
            END LOOP;
            CLOSE c_inscricoes;
            COMMIT;
        EXCEPTION
            WHEN OTHERS THEN
                ROLLBACK;
                RAISE;
        END;
        """

        cursor.execute(plsql_block)
        conn.commit()
        mensagem = "Fila processada com sucesso!"
    except oracledb.DatabaseError as e:
        error, = e.args
        mensagem = f"Erro Oracle: {error.code} - {error.message}"
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template('index.html', mensagem=mensagem)

if __name__ == '__main__':
    app.run(debug=True)
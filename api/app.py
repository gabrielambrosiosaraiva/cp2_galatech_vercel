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

@app.route('/processar_fila', methods=['POST'])
def processar_fila():
    try:
        conn = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
        cursor = conn.cursor()

        # Exemplo de bloco PL/SQL com cursor explícito
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

                -- Exemplo de regra de negócio:
                -- Promover Platinum e VIP se houver vagas
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
        try:
            cursor.close()
            conn.close()
        except:
            pass

    return render_template('index.html', mensagem=mensagem)

if __name__ == '__main__':
    app.run(debug=True)

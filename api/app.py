from flask import Flask, render_template, request
import os
import oracledb

app = Flask(__name__, template_folder="../templates", static_folder="../static")


USUARIO_BD = os.environ.get("DB_USER", "usuario_teste")
SENHA_BD = os.environ.get("DB_PASSWORD", "senha_teste")
DSN_BD = os.environ.get("DB_DSN", "localhost/XEPDB1")

@app.route('/')
def pagina_inicial():
    pagina = int(request.args.get('page', 1))
    por_pagina = 10
    deslocamento = (pagina - 1) * por_pagina

    lista_confirmados, lista_fila = [], []
    vagas_disponiveis, vagas_preenchidas = 0, 0

    try:
        conexao = oracledb.connect(user=USUARIO_BD, password=SENHA_BD, dsn=DSN_BD)
        cursor = conexao.cursor()

       
        cursor.execute("SELECT vagas_disponiveis FROM TB_CP2_EVENTOS WHERE id_evento = 1")
        vagas_disponiveis = cursor.fetchone()[0]

        
        cursor.execute("""
            SELECT COUNT(*)
            FROM TB_CP2_INSCRICOES
            WHERE status_inscricao = 'CONFIRMADA'
              AND id_evento = 1
        """)
        vagas_preenchidas = cursor.fetchone()[0]

       
        cursor.execute(f"""
            SELECT u.nome_usuario, i.tipo_inscricao, TO_CHAR(i.data_inscricao,'DD/MM/YYYY HH24:MI'), u.email_usuario
            FROM TB_CP2_USUARIOS u
            JOIN TB_CP2_INSCRICOES i ON u.id_usuario = i.id_usuario
            WHERE i.status_inscricao = 'CONFIRMADA'
              AND i.id_evento = 1
            ORDER BY i.data_inscricao ASC
            OFFSET {deslocamento} ROWS FETCH NEXT {por_pagina} ROWS ONLY
        """)
        for linha in cursor.fetchall():
            lista_confirmados.append({
                "nome_usuario": linha[0],
                "tipo_inscricao": linha[1],
                "data_inscricao": linha[2],
                "email_usuario": linha[3]
            })

       
        cursor.execute("""
            SELECT u.nome_usuario, i.tipo_inscricao, TO_CHAR(i.data_inscricao,'DD/MM/YYYY HH24:MI'), u.email_usuario,
                   ROW_NUMBER() OVER (
                       ORDER BY CASE i.tipo_inscricao
                                   WHEN 'Ingresso Platinum' THEN 1
                                   WHEN 'Ingresso VIP' THEN 2
                                   WHEN 'Ingresso Normal' THEN 3
                                   ELSE 4 END,
                                i.data_inscricao
                   ) AS posicao_fila
            FROM TB_CP2_USUARIOS u
            JOIN TB_CP2_INSCRICOES i ON u.id_usuario = i.id_usuario
            WHERE i.status_inscricao = 'WAITLIST'
              AND i.id_evento = 1
        """)
        for linha in cursor.fetchall():
            lista_fila.append({
                "nome_usuario": linha[0],
                "tipo_inscricao": linha[1],
                "data_inscricao": linha[2],
                "email_usuario": linha[3],
                "posicao_fila": linha[4]
            })
    finally:
        if cursor: cursor.close()
        if conexao: conexao.close()

    total_paginas = (vagas_preenchidas + por_pagina - 1) // por_pagina

    return render_template('index.html',
                           confirmados=lista_confirmados,
                           fila=lista_fila,
                           vagas=vagas_disponiveis,
                           preenchidas=vagas_preenchidas,
                           page=pagina,
                           total_pages=total_paginas)

@app.route('/abrir_vagas', methods=['POST'])
def abrir_vagas():
    quantidade = int(request.form.get('qtd', 0))
    mensagem = ""
    lista_confirmados, lista_fila = [], []
    vagas_disponiveis, vagas_preenchidas = 0, 0
    pagina, por_pagina, deslocamento = 1, 10, 0

    try:
        conexao = oracledb.connect(user=USUARIO_BD, password=SENHA_BD, dsn=DSN_BD)
        cursor = conexao.cursor()

        
        bloco_plsql = f"""
        DECLARE
            v_vagas TB_CP2_EVENTOS.vagas_disponiveis%TYPE;
            CURSOR c_fila IS
                SELECT i.id_inscricao
                FROM TB_CP2_INSCRICOES i
                WHERE i.status_inscricao = 'WAITLIST'
                  AND i.id_evento = 1
                ORDER BY CASE i.tipo_inscricao
                            WHEN 'Ingresso Platinum' THEN 1
                            WHEN 'Ingresso VIP' THEN 2
                            WHEN 'Ingresso Normal' THEN 3
                            ELSE 4
                         END,
                         i.data_inscricao ASC
                FOR UPDATE OF i.status_inscricao;
            v_id TB_CP2_INSCRICOES.id_inscricao%TYPE;
            v_contador NUMBER := 0;
        BEGIN
            SELECT vagas_disponiveis INTO v_vagas
            FROM TB_CP2_EVENTOS
            WHERE id_evento = 1
            FOR UPDATE;

            v_vagas := v_vagas + {quantidade};

            OPEN c_fila;
            LOOP
                FETCH c_fila INTO v_id;
                EXIT WHEN c_fila%NOTFOUND OR v_contador = v_vagas;

                UPDATE TB_CP2_INSCRICOES
                SET status_inscricao = 'CONFIRMADA'
                WHERE CURRENT OF c_fila;

                INSERT INTO TB_CP2_LOG_AUDITORIA (id_inscricao, motivo_log)
                VALUES (v_id, 'Promoção da fila após abertura de vagas');

                v_contador := v_contador + 1;
            END LOOP;
            CLOSE c_fila;

            UPDATE TB_CP2_EVENTOS
            SET vagas_disponiveis = v_vagas - v_contador
            WHERE id_evento = 1;

            COMMIT;
        END;
        """
        cursor.execute(bloco_plsql)
        mensagem = f"{quantidade} vagas abertas, {quantidade} processadas (se disponíveis)."

        # Atualiza listas
        cursor.execute("SELECT vagas_disponiveis FROM TB_CP2_EVENTOS WHERE id_evento = 1")
        vagas_disponiveis = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM TB_CP2_INSCRICOES
            WHERE status_inscricao = 'CONFIRMADA'
              AND id_evento = 1
        """)
        vagas_preenchidas = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT u.nome_usuario, i.tipo_inscricao, TO_CHAR(i.data_inscricao,'DD/MM/YYYY HH24:MI'), u.email_usuario
            FROM TB_CP2_USUARIOS u
            JOIN TB_CP2_INSCRICOES i ON u.id_usuario = i.id_usuario
            WHERE i.status_inscricao = 'CONFIRMADA'
              AND id_evento = 1
            ORDER BY i.data_inscricao ASC
            OFFSET {deslocamento} ROWS FETCH NEXT {por_pagina} ROWS ONLY
        """)
        for linha in cursor.fetchall():
            lista_confirmados.append({
                "nome_usuario": linha[0],
                "tipo_inscricao": linha[1],
                "data_inscricao": linha[2],
                "email_usuario": linha[3]
            })

        cursor.execute("""
            SELECT u.nome_usuario, i.tipo_inscricao, TO_CHAR(i.data_inscricao,'DD/MM/YYYY HH24:MI'), u.email_usuario,
                   ROW_NUMBER() OVER (
                       ORDER BY CASE i.tipo_inscricao
                                   WHEN 'Ingresso Platinum' THEN 1
                                   WHEN 'Ingresso VIP' THEN 2
                                   WHEN 'Ingresso Normal' THEN 3
                                   ELSE 4 END,
                                i.data_inscricao
                   ) AS posicao_fila
            FROM TB_CP2_USUARIOS u
            JOIN TB_CP2_INSCRICOES i ON u.id_usuario = i.id_usuario
            WHERE i.status_inscricao = 'WAITLIST'
              AND id_evento = 1
        """)
        for linha in cursor.fetchall():
            lista_fila.append({
                "nome_usuario": linha[0],
                "tipo_inscricao": linha[1],
                "data_inscricao": linha[2],
                "email_usuario": linha[3],
                "posicao_fila": linha[4]
            })

    except oracledb.DatabaseError as e:
        erro, = e.args
        mensagem = f"Erro Oracle: {erro.code} - {erro.message}"
    finally:
        if cursor: cursor.close()
        if conexao: conexao.close()

    total_paginas = (vagas_preenchidas + por_pagina - 1) // por_pagina

    return render_template('index.html',
                           confirmados=lista_confirmados,
                           fila=lista_fila,
                           vagas=vagas_disponiveis,
                           preenchidas=vagas_preenchidas,
                           mensagem=mensagem,
                           page=pagina,
                           total_pages=total_paginas)

if __name__ == '__main__':
    app.run(debug=True)

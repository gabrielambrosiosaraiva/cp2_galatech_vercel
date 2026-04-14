
# Grand Tech Gala - Processo Automatizado de Fila de Espera

## Visão Geral

O sistema Grand Tech Gala é uma aplicação desenvolvida com Flask e Oracle Database (oracledb) com o objetivo de gerenciar inscrições em eventos, controle de vagas e processamento automático de fila de espera (WAITLIST).

O principal componente do sistema é um bloco PL/SQL anônimo com cursor explícito, responsável por automatizar a lógica de promoção de usuários com base em regras de prioridade e disponibilidade de vagas.

---

# Arquitetura do Processo

O sistema é dividido em duas camadas:

- Camada Web (Flask)
  - Recebe requisições do usuário
  - Envia a quantidade de vagas para o banco
  - Renderiza resultados na interface

- Camada Banco de Dados (Oracle + PL/SQL)
  - Executa o motor de fila
  - Aplica regras de negócio
  - Controla concorrência e consistência
  - Registra auditoria

---

# Bloco PL/SQL Anônimo (Motor da Fila)

O processamento da fila de espera é realizado através de um bloco PL/SQL anônimo executado diretamente pelo Flask, que encapsula toda a lógica de promoção de usuários.

Este bloco é responsável por transformar a WAITLIST em CONFIRMADA de forma automática e controlada.

---

## Estrutura geral do bloco

O bloco é composto por:

- Declaração de variáveis
- Declaração de cursor explícito
- Controle de vagas do evento
- Loop de processamento linha a linha
- Atualização de status das inscrições
- Registro de auditoria
- Atualização final de vagas
- Commit da transação

---

## Cursor explícito da fila de espera

O cursor seleciona todas as inscrições em WAITLIST do evento e as organiza com base em regras de prioridade.

```sql
CURSOR c_fila IS
    SELECT i.id_inscricao
    FROM TB_CP2_INSCRICOES i
    WHERE i.status_inscricao = 'WAITLIST'
      AND i.id_evento = 1
    ORDER BY 
        CASE i.tipo_inscricao
            WHEN 'Ingresso Platinum' THEN 1
            WHEN 'Ingresso VIP' THEN 2
            WHEN 'Ingresso Normal' THEN 3
            ELSE 4
        END,
        i.data_inscricao ASC
    FOR UPDATE OF i.status_inscricao;
Características do cursor:
Cursor explícito com controle manual
Filtro exclusivo para WAITLIST
Ordenação por prioridade de ingresso
Ordenação secundária por data de inscrição
Bloqueio de linhas durante execução com FOR UPDATE
Variáveis de controle
v_vagas: número total de vagas disponíveis no evento
v_id: inscrição atual processada
v_contador: controle de quantidade de promoções realizadas
Controle de vagas

Antes do processamento, o sistema obtém e bloqueia as vagas do evento:

SELECT vagas_disponiveis INTO v_vagas
FROM TB_CP2_EVENTOS
WHERE id_evento = 1
FOR UPDATE;

Em seguida, adiciona a quantidade informada pelo usuário:

v_vagas := v_vagas + {quantidade};
Processamento da fila

O cursor é percorrido linha por linha através de um loop.

O processamento é interrompido quando:

Não há mais registros na fila
O limite de vagas é atingido
Promoção de inscrições

Cada inscrição processada tem seu status atualizado:

UPDATE TB_CP2_INSCRICOES
SET status_inscricao = 'CONFIRMADA'
WHERE CURRENT OF c_fila;
Registro de auditoria

Cada promoção gera um registro na tabela de auditoria:

INSERT INTO TB_CP2_LOG_AUDITORIA (id_inscricao, motivo_log)
VALUES (v_id, 'Promoção da fila após abertura de vagas');
Controle de concorrência

O uso de FOR UPDATE garante:

Bloqueio das linhas durante processamento
Evita concorrência simultânea
Mantém consistência da fila
Atualização final de vagas

Após o processamento:

UPDATE TB_CP2_EVENTOS
SET vagas_disponiveis = v_vagas - v_contador
WHERE id_evento = 1;
Finalização da transação
COMMIT;
Regras de Negócio
Prioridade de ingresso:
Platinum (maior prioridade)
VIP
Normal
Ordenação:
Tipo de ingresso
Data de inscrição
Status possíveis:
CONFIRMADA
WAITLIST
CANCELADA
Integração com Flask

O bloco é executado no endpoint:

/abrir_vagas

Fluxo:

Usuário informa quantidade de vagas
Flask envia valor ao Oracle
Bloco PL/SQL executa processamento completo
Fila é atualizada automaticamente
Interface exibe resultados
Tecnologias
Python (Flask)
Oracle Database
PL/SQL
oracledb
HTML e CSS (Jinja2)
Conclusão

O sistema implementa um motor automatizado de fila de espera baseado em bloco PL/SQL anônimo com cursor explícito, garantindo processamento controlado, aplicação de regras de prioridade, consistência transacional, auditoria e integração com aplicação web.
#!/usr/bin/env python3
"""A ligação com o banco — que agora pode ser SQLite ou Postgres.

O sistema foi escrito em cima do SQLite e tem 631 consultas com `?`, 145 usos
de `date('now')` e `datetime('now')`, 37 `lastrowid` e 22 `INSERT OR IGNORE`.
Reescrever isso à mão em 38 módulos seria trocar um sistema que funciona por
um que talvez funcione.

Aqui a saída é outra: uma camada que fala a mesma língua do `sqlite3` para
quem chama, e traduz para Postgres na hora de executar. O código das telas não
muda; muda só quem atende do outro lado.

    ./rodar.sh                        # Postgres (Supabase, ou o cluster de prova)

ADAPTAÇÃO DO TRABALHISTA (ver docs/portal-adaptacoes.md): aqui o banco já
nasce no Postgres — não há cópia SQLite. A tradução continua inteira porque
é ela que deixa o código das telas escrito no dialeto simples (`?`,
`date('now')`, `LIKE`), e porque é o mesmo arquivo do Prev: divergir agora
seria manter duas pontes.

O que a tradução cobre, e por quê:

  ?                       → %s          o marcador de parâmetro é outro
  date('now','localtime') → to_char(...)  o relógio do Postgres é UTC; o
                                          escritório trabalha em São Paulo
  julianday(a)-julianday(b) → dias entre datas, que no Postgres é subtração
  GLOB                    → ~           padrão do SQLite vira expressão regular
  LIKE                    → ILIKE       no SQLite LIKE ignora maiúscula; no
                                        Postgres, não — sem isso a busca por
                                        nome pararia de achar
  INSERT OR IGNORE        → ON CONFLICT DO NOTHING
  cur.lastrowid           → RETURNING id, guardado para quem perguntar
  PRAGMA                  → information_schema, ou nada quando não se aplica

O que NÃO dá para traduzir e precisa de outra implementação está anotado em
`FALTA_TRADUZIR`, e a busca do acervo (FTS5) é o caso principal.
"""
import decimal
import os
import re
import sqlite3

AQUI = os.path.dirname(os.path.abspath(__file__))
SQLITE = None          # o trabalhista não tem cópia local

FALTA_TRADUZIR = {}

FUSO = "America/Sao_Paulo"
_AGORA = f"(now() AT TIME ZONE '{FUSO}')"


def em_postgres():
    """Sempre. No trabalhista o banco nasce no Postgres e não há cópia local."""
    return True


# ------------------------------------------------- os erros que o código trata
# Meia dúzia de lugares dependem de *pegar* o erro do banco, não de evitá-lo:
# a automação insere e o duplicado é o sinal de que já agiu; o gatilho de
# governança recusa a transição e a tela mostra o motivo para quem clicou;
# módulo que roda antes da tabela existir segue em frente. Escrito como
# `sqlite3.IntegrityError`, nada disso pega no Postgres — o except passa reto e
# o erro vira tela branca. Estes dois nomes pegam o equivalente nos dois
# motores, ao mesmo tempo.
def _erros():
    # Os dois motores de uma vez, sempre: montar.py trabalha no SQLite com o
    # GGV_BANCO apontando para o Postgres, e chama módulos que usam estes
    # nomes. Pegar a exceção do motor que não está em uso não custa nada —
    # ela simplesmente nunca acontece.
    integridade = [sqlite3.IntegrityError]
    operacional = [sqlite3.OperationalError]
    # Família à parte: o FORMATO do que chegou não serve para a coluna —
    # 'abc' onde se espera inteiro (22P02), texto maior que o campo (22001),
    # número fora da faixa do bigint (22003). No SQLite quase não existe (a
    # coluna aceita qualquer coisa); no Postgres não é IntegrityError nem
    # OperationalError, é `DataError`. Sem ela aqui, `_RECUSAS` traduzia 22P02
    # e 22001 sem que `except` nenhum chegasse a pegá-los: duas entradas
    # mortas, e a recusa virava 500 (auditoria de 03/09/2026, §7).
    dados = [sqlite3.DataError] if hasattr(sqlite3, "DataError") else []
    try:
        from psycopg import errors as e
    except ImportError:
        pass
    else:
        # RaiseException é o RAISE do PL/pgSQL — é assim que governanca.sql
        # fala. No SQLite o mesmo RAISE(ABORT) chega como IntegrityError.
        integridade += [e.IntegrityError, e.RaiseException]
        # de propósito estreito: só "não/já existe tabela, coluna, esquema".
        # Erro de sintaxe ou função errada tem de aparecer, não ser engolido
        # por um guard. No SQLite os dois lados chegam como OperationalError,
        # e é isso que os módulos de "cria a coluna se faltar" esperam.
        operacional += [e.OperationalError, e.UndefinedTable, e.UndefinedColumn,
                        e.InvalidSchemaName, e.DuplicateColumn, e.DuplicateTable,
                        e.DuplicateObject]
        # `DataError` é o pai de InvalidTextRepresentation (22P02),
        # StringDataRightTruncation (22001), NumericValueOutOfRange (22003) e
        # DatetimeFieldOverflow — pegar o pai cobre a família inteira.
        dados += [e.DataError]
    return tuple(integridade), tuple(operacional), tuple(dados)


Integridade, Operacional, Dados = _erros()

# As três famílias de uma vez, para quem trata a RECUSA do banco sem precisar
# saber de qual delas ela veio.
#
# Existe porque `except (banco.Integridade, banco.Operacional)` NÃO funciona:
# os dois nomes já são tuplas, e Python não aceita tupla aninhada no `except` —
# levanta `TypeError: catching classes that do not inherit from BaseException
# is not allowed` em vez de pegar o erro. Escrito assim, o tratamento some sem
# avisar e toda recusa do gatilho vira 500. Foi o defeito mais grave da
# auditoria de 03/09/2026 (verificação 7): as conexões não voltavam ao poço e
# seis recusas seguidas paravam o portal para todo mundo (`PoolTimeout`).
#
#     except banco.ErroBanco as e:                           # certo
#     except (banco.Integridade, banco.Operacional) as e:    # TypeError
#
# `Dados` entrou na tupla em 03/09/2026: sem ela, `SELECT 'abc'::int` passava
# reto pelo `except banco.ErroBanco` e virava 500.
ErroBanco = Integridade + Operacional + Dados


# ------------------------------------------------------------ a tradução
def _relogio(m):
    """date('now','localtime', '-30 day') e parentes."""
    funcao = m.group(1).lower()
    resto = m.group(2) or ""
    formato = "YYYY-MM-DD" if funcao == "date" else "YYYY-MM-DD HH24:MI:SS"
    base = _AGORA
    for pedaco in re.findall(r"'([+-]?\d+\s+\w+)'", resto):
        base = f"({base} + interval '{pedaco}')"
    # o deslocamento também chega como parâmetro: date('now', ?).
    # Devolve "?" e não "%s": o marcador é trocado no fim, de uma vez só —
    # emitir %s aqui faria o escape de literal dobrá-lo em %%s, e a consulta
    # passaria a ter um parâmetro a menos do que os valores enviados.
    if "?" in resto:
        return f"to_char({base} + (?)::interval, '{formato}')"
    return f"to_char({base}, '{formato}')"


def _strftime(m):
    """strftime('%Y','now','localtime') → to_char(now(), 'YYYY')."""
    mapa = {"%Y": "YYYY", "%m": "MM", "%d": "DD", "%Y-%m": "YYYY-MM",
            "%Y-%m-%d": "YYYY-MM-DD", "%H:%M": "HH24:MI", "%w": "D"}
    padrao = mapa.get(m.group(1), "YYYY-MM-DD")
    return f"to_char({_AGORA}, '{padrao}')"


# comparação dentro de SUM: no SQLite dá 0/1 e soma; no Postgres dá booleano,
# e SUM(boolean) não existe. Vira contagem condicional.
COMPARA = re.compile(r"(<=|>=|<>|!=|<|>|=|\bIS\s+(?:NOT\s+)?NULL\b|\bI?LIKE\b|\bIN\s*\()", re.I)


def _soma_condicional(s):
    saida, i = [], 0
    while True:
        m = re.search(r"\b(SUM|AVG)\s*\(", s[i:], re.I)
        if not m:
            saida.append(s[i:])
            break
        ini = i + m.start()
        abre = i + m.end() - 1
        nivel, j = 0, abre
        while j < len(s):
            if s[j] == "(":
                nivel += 1
            elif s[j] == ")":
                nivel -= 1
                if nivel == 0:
                    break
            j += 1
        dentro = s[abre + 1:j]
        # só mexe quando há comparação no nível de cima do argumento
        raso, prof = [], 0
        for ch in dentro:
            if ch == "(":
                prof += 1
            elif ch == ")":
                prof -= 1
            raso.append(ch if prof == 0 else " ")
        if COMPARA.search("".join(raso)) and "CASE" not in dentro.upper():
            saida.append(s[i:abre + 1] + f"CASE WHEN {dentro} THEN 1 ELSE 0 END")
        else:
            saida.append(s[i:j])
        saida.append(")")
        i = j + 1
    return "".join(saida)


def traduzir(sql):
    """SQL escrito para SQLite, executável no Postgres."""
    s = sql

    # relógio: precisa vir antes da troca de ? por %s, senão o marcador some
    s = re.sub(r"\b(date|datetime)\s*\(\s*'now'\s*((?:,\s*(?:'[^']*'|\?))*)\s*\)",
               _relogio, s, flags=re.I)
    s = re.sub(r"strftime\s*\(\s*'([^']+)'\s*,\s*'now'(?:\s*,\s*'[^']*')*\s*\)",
               _strftime, s, flags=re.I)

    # diferença de datas: no SQLite é julianday; aqui é subtração de date
    s = re.sub(r"julianday\s*\(\s*'now'\s*\)", f"({_AGORA})::date", s, flags=re.I)
    s = re.sub(r"julianday\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)",
               lambda m: f"(substr({m.group(1)},1,10))::date", s, flags=re.I)

    # date(coluna) no SQLite recorta a data de um texto; no Postgres converte
    # para o tipo date, e aí comparar com texto quebra
    s = re.sub(r"\bdate\s*\(\s*([A-Za-z_][\w.]*)\s*\)",
               r"substr(\1,1,10)", s, flags=re.I)
    s = re.sub(r"\bdatetime\s*\(\s*([A-Za-z_][\w.]*)\s*\)",
               r"substr(\1,1,19)", s, flags=re.I)

    # juntar texto de várias linhas
    s = re.sub(r"\bgroup_concat\s*\(", "string_agg(", s, flags=re.I)
    # instr(palheiro, agulha) → strpos, com os argumentos na mesma ordem
    s = re.sub(r"\binstr\s*\(", "strpos(", s, flags=re.I)

    # o padrão do SQLite vira expressão regular. NOT GLOB tem operador próprio
    s = re.sub(r"(\w+(?:\.\w+)?)\s+NOT\s+GLOB\s+", r"\1 !~ ", s, flags=re.I)
    s = re.sub(r"(\w+(?:\.\w+)?)\s+GLOB\s+", r"\1 ~ ", s, flags=re.I)

    # LIKE no SQLite ignora maiúscula; no Postgres não. Sem ILIKE, procurar
    # "maria" pararia de achar "MARIA" — e é assim que a tela busca cliente.
    s = re.sub(r"\bLIKE\b", "ILIKE", s, flags=re.I)
    s = re.sub(r"\bNOT ILIKE\b", "NOT ILIKE", s, flags=re.I)

    s = _soma_condicional(s)

    # somar comparações: no SQLite booleano é 0/1 e soma; no Postgres não.
    # Aparece onde a tela conta quantos campos da ficha estão preenchidos.
    # o miolo pode ter uma chamada dentro, como COALESCE(a, b) IS NOT NULL
    miolo = r"(?:[^()]|\([^()]*\))*\bIS\s+(?:NOT\s+)?NULL"
    def _int_bool(m):
        return f"({m.group(1)})::int"
    # um passe só, olhando os dois lados, para não sair ::int::int
    s = re.sub(rf"\(({miolo})\)(?=\s*[+\-*])", _int_bool, s, flags=re.I)
    s = re.sub(rf"(?<![:\w])(?<=[+\-*])\s*\(({miolo})\)", lambda m: " " + _int_bool(m),
               s, flags=re.I)

    # coluna gerada: no SQLite o padrão é VIRTUAL (calculada na leitura); no
    # Postgres só existe STORED. Sem isto, todo módulo que garante o próprio
    # esquema com `executescript` morre no primeiro CREATE — e o erro aparece
    # longe da causa, porque a transação abortada derruba tudo depois.
    s = re.sub(r"\)\s+VIRTUAL\b", ") STORED", s, flags=re.I)

    # COLLATE NOCASE é do SQLite. O ILIKE ali em cima já resolve maiúscula,
    # então a instrução some sem mudar o resultado.
    s = re.sub(r"\s+COLLATE\s+(NOCASE|BINARY|RTRIM)\b", "", s, flags=re.I)

    # inserção que não deve reclamar de repetido
    s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.I)
    s = re.sub(r"INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", s, flags=re.I)

    # "? IS NULL" deixa o Postgres sem saber o tipo do parâmetro. O padrão
    # aparece nas telas que filtram por campo opcional — "(? IS NULL OR
    # t.grupo=?)" — e um cast resolve sem mudar o sentido.
    s = re.sub(r"\?(\s+IS\s+(?:NOT\s+)?NULL)", r"?::text\1", s, flags=re.I)

    # O psycopg lê % como marcador. Todo % que é literal — o do
    # LIKE 'ENCERRADO%', por exemplo — precisa vir dobrado, e isso tem de
    # acontecer ANTES de o ? virar %s, senão dobraria o marcador também.
    s = s.replace("%", "%%")
    return _troca_marcadores(s)


def _troca_marcadores(s):
    """`?` vira `%s` — MENOS dentro de texto entre aspas.

    A troca era cega, e `COALESCE(td.nome, '?')` — SQL perfeitamente válido —
    virava um marcador a mais que ninguém ia preencher: "the query has 2
    placeholders but 1 parameters were passed", num lugar que não tem nada a
    ver com o parâmetro. Custou um bom tempo para achar.

    Aspas simples com o escape do SQL (`''` dentro da string) e aspas duplas
    de identificador, as duas contam.
    """
    fora, aspas, i, n = [], None, 0, len(s)
    while i < n:
        c = s[i]
        if aspas:
            fora.append(c)
            if c == aspas:
                # '' dentro de texto é aspas escapada, não o fim dele
                if i + 1 < n and s[i + 1] == aspas:
                    fora.append(s[i + 1]); i += 2; continue
                aspas = None
            i += 1
            continue
        if c in ("'", '"'):
            aspas = c; fora.append(c); i += 1; continue
        fora.append("%s" if c == "?" else c)
        i += 1
    return "".join(fora)


# quem pode falhar e ter o erro tratado: escrita e mudança de esquema
ESCRITA = ("INSERT", "UPDATE", "DELETE", "ALTER", "CREATE", "DROP")


def _tabela_do_insert(sql):
    m = re.search(r"INSERT\s+INTO\s+[\"']?(\w+)", sql, re.I)
    return m.group(1).lower() if m else None


# --------------------------------------------------- o disfarce de sqlite3
def _como_sqlite(v):
    """SUM() no Postgres volta Decimal; no SQLite, inteiro.

    O app faz conta com esses valores (divide por 1e9 para dar GB, por
    exemplo), e Decimal com float não se divide em Python. Converter aqui
    poupa caçar cada conta espalhada por 38 módulos.
    """
    if isinstance(v, decimal.Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    return v


class Linha(dict):
    """Row do sqlite3 aceita índice e nome; o dict do psycopg, só nome."""

    def __init__(self, cru):
        super().__init__({k: _como_sqlite(v) for k, v in cru.items()})

    def __getitem__(self, chave):
        if isinstance(chave, int):
            return list(self.values())[chave]
        return super().__getitem__(chave)

    def keys(self):
        return super().keys()

    def __iter__(self):
        """Row do sqlite3 desempacota em VALORES: `a, b = linha` funciona.

        Um dict comum itera as chaves — e foi assim que fluxo.transicoes leu
        'acao' como se fosse o nome da ação, e nenhuma transição casava.
        """
        return iter(self.values())


class Cursor:
    def __init__(self, cru, ponte):
        self._c = cru
        self._ponte = ponte
        self.lastrowid = None
        self._linhas = None      # quantas a escrita mexeu, guardado a tempo

    def execute(self, sql, args=()):
        self._ponte._executar(self, sql, args)
        return self

    def executemany(self, sql, seq):
        traduzido = traduzir(sql)
        self._c.executemany(traduzido, [tuple(a) for a in seq])
        return self

    def fetchone(self):
        r = self._c.fetchone()
        return Linha(r) if r else None

    def fetchall(self):
        return [Linha(r) for r in self._c.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self):
        """Depois do savepoint o cursor cru já conta outra coisa; vale o guardado."""
        return self._c.rowcount if self._linhas is None else self._linhas

    def close(self):
        self._c.close()


class Ponte:
    """Fala como uma conexão do sqlite3; por baixo é psycopg.

    Recebe o poço, não uma URI: `close()` DEVOLVE a conexão em vez de fechá-la,
    e é isso que faz o sistema parar de autenticar a cada tela.
    """

    # a lista de tabelas com `id` não muda entre requisições; consultá-la em
    # toda conexão era uma ida à rede a mais por tela
    _com_id_cache = None

    def __init__(self, poco):
        self._poco = poco
        self._pg = poco.getconn()
        self.row_factory = None            # o app às vezes atribui; aqui é ignorado
        if Ponte._com_id_cache is None:
            Ponte._com_id_cache = self._tabelas_com_id()
        self._com_id = Ponte._com_id_cache

    def _tabelas_com_id(self):
        with self._pg.cursor() as c:
            c.execute("""SELECT table_name FROM information_schema.columns
                         WHERE table_schema='public' AND column_name='id'""")
            return {r["table_name"] for r in c.fetchall()}

    def _executar(self, cur, sql, args=()):
        cru = cur._c
        alvo = sql.strip().upper()

        # PRAGMA não existe no Postgres
        if alvo.startswith("PRAGMA"):
            m = re.search(r"table_x?info\s*\(\s*[\"']?(\w+)", sql, re.I)
            if m:
                cru.execute("""SELECT ordinal_position-1 AS cid, column_name AS name,
                                      data_type AS type, 0 AS notnull, NULL AS dflt_value,
                                      0 AS pk, 0 AS hidden
                               FROM information_schema.columns
                               WHERE table_schema='public' AND table_name=%s
                               ORDER BY ordinal_position""", (m.group(1),))
            else:
                cru.execute("SELECT 1 WHERE false")
            return

        for marca, porque in FALTA_TRADUZIR.items():
            if marca in sql:
                raise NotImplementedError(f"{porque} (consulta usa '{marca}')")

        s = traduzir(sql)
        eh_insert = alvo.startswith("INSERT")
        if eh_insert and re.search(r"INSERT\s+OR\s+(IGNORE|REPLACE)", sql, re.I):
            if "ON CONFLICT" not in s.upper():
                s += " ON CONFLICT DO NOTHING"
        # lastrowid: no Postgres o id volta por RETURNING
        devolve = False
        if eh_insert and "RETURNING" not in s.upper():
            tab = _tabela_do_insert(s)
            if tab in self._com_id:
                s += " RETURNING id"
                devolve = True
        if alvo.startswith(ESCRITA):
            self._escrever(cur, s, args, devolve)
        else:
            self._rodar(cur, s, args, devolve)

    def _escrever(self, cur, s, args, devolve):
        """Escrita protegida por savepoint.

        No Postgres, uma instrução que falha derruba a transação inteira: tudo
        que vier depois erra até alguém dar rollback. No SQLite não é assim, e
        o sistema conta com isso — a automação insere e trata o duplicado, o
        gatilho de governança recusa a transição e a tela mostra o recado, e a
        vida segue. O savepoint devolve esse comportamento: quem falha desfaz
        só a si mesmo.

        Custa duas idas a mais ao servidor, então vale só para quem escreve ou
        mexe no esquema — que é raro. SELECT fica no caminho curto: são dezenas
        por tela, e triplicar isso numa ligação de rede se sentiria.
        """
        cur._c.execute("SAVEPOINT ggv_passo")
        try:
            self._rodar(cur, s, args, devolve)
        except Exception:
            cur._c.execute("ROLLBACK TO SAVEPOINT ggv_passo")
            raise
        cur._linhas = cur._c.rowcount     # antes do RELEASE, que zera a conta
        cur._c.execute("RELEASE SAVEPOINT ggv_passo")

    def _rodar(self, cur, s, args, devolve):
        cru = cur._c
        cru.execute(s, tuple(args) if args else None)
        cur._linhas = None
        if devolve:
            try:
                linha = cru.fetchone()
                self._ultimo = linha["id"] if linha else None
            except Exception:
                self._ultimo = None
        else:
            self._ultimo = None
        # O id vai TAMBÉM para o cursor, e não só para a ponte.
        #
        # Quem chama `Ponte.execute()` recebia o lastrowid porque aquele
        # método copiava `_ultimo` depois. Mas o padrão do sistema é
        # `cur = db.cursor()` e depois `cur.lastrowid` — 37 lugares — e por
        # esse caminho ninguém copiava nada: o insert gravava, o id existia
        # no servidor, e `lastrowid` voltava None.
        #
        # O efeito era um TypeError no primeiro uso do id, quase sempre uma
        # linha depois. Cadastrar lead, por exemplo, ficou impossível desde
        # a mudança para o Postgres.
        cur.lastrowid = self._ultimo

    def execute(self, sql, args=()):
        c = Cursor(self._pg.cursor(), self)
        c.execute(sql, args)
        c.lastrowid = getattr(self, "_ultimo", None)
        return c

    def executemany(self, sql, seq):
        c = Cursor(self._pg.cursor(), self)
        return c.executemany(sql, seq)

    def executescript(self, sql):
        with self._pg.cursor() as c:
            c.execute(traduzir(sql))
        self._pg.commit()

    def cursor(self):
        return Cursor(self._pg.cursor(), self)

    def commit(self):
        self._pg.commit()

    def rollback(self):
        self._pg.rollback()

    def close(self):
        """Devolve ao poço. Uma transação aberta seria herdada pela próxima
        tela, então volta limpa.

        **Chamar duas vezes não devolve duas vezes.** As rotas agora fecham no
        `finally`, e várias delas já fechavam antes de um `return` no meio do
        caminho; sem esta trava, a mesma conexão voltaria ao poço duas vezes e
        duas telas passariam a escrever na mesma sessão do Postgres — defeito
        muito pior do que o vazamento que o `finally` veio corrigir.
        """
        pg, self._pg = self._pg, None
        if pg is None:
            return
        try:
            pg.rollback()
        except Exception:
            pass
        self._poco.putconn(pg)

    # `with conectar() as db:` devolve a conexão ao poço mesmo se o corpo
    # levantar. É o mesmo contrato do `finally`, escrito uma vez só.
    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, tb):
        self.close()
        return False


def _uri():
    import subprocess
    import sys
    from urllib.parse import quote
    import chaves                       # tardio: evita ciclo no import
    # `--dsn` de um script chega por aqui: quem roda migrar.py e o portal
    # contra o cluster de prova não precisa mexer no Keychain.
    guardado = (os.environ.get("GGV_DSN") or "").strip() or chaves.ler("supabase-trab")
    if not guardado:
        sys.exit("✗ sem a ligação do Postgres. No Mac: tk supabase-trab. "
                 "No servidor: variável GGV_SUPABASE_TRAB (ou GGV_DSN).")
    if guardado.startswith("postgres"):
        return guardado
    p = quote(guardado, safe="")
    # 6543 é o *transaction pooler*; 5432 é a conexão direta. Num servidor com
    # mais de uma instância a direta esgota o limite do Supabase depressa — foi
    # o que derrubou este sistema uma vez, antes do pool de conexões. Fora do
    # Mac, portanto, o padrão é a porta do pooler.
    import chaves as _c
    porta = 6543 if _c.no_servidor() else 5432
    return (f"postgresql://postgres.yzayjwlgjjnoxdxgruss:{p}"
            f"@aws-0-sa-east-1.pooler.supabase.com:{porta}/postgres")


# ------------------------------------------------------- o poço de conexões
# Cada tela abre e fecha conexão — são 84 chamadas a `conectar()` só no app.py.
# Contra um SQLite local isso é de graça; contra o Postgres em São Paulo, cada
# uma custa uma ida à rede E uma autenticação. O pooler do Supabase tem um
# disjuntor que bloqueia o projeto inteiro quando vê autenticação demais em
# pouco tempo — e ele disparou aqui em 25/08/2026, durante os reinícios do dia.
#
# O poço resolve na origem: um punhado de conexões abertas uma vez e
# reaproveitadas. `conectar()` continua com a mesma cara para quem chama.
_POCO = None


def _poco():
    global _POCO
    if _POCO is None:
        from psycopg_pool import ConnectionPool
        from psycopg.rows import dict_row
        import atexit
        import logging
        # O poço avisa cada tentativa de reconexão no stderr. Quando o
        # disjuntor do Supabase está ligado isso vira dezenas de páginas de
        # erro repetido, e o erro que importa some no meio.
        logging.getLogger("psycopg.pool").setLevel(logging.ERROR)
        _POCO = ConnectionPool(
            _uri(), min_size=1, max_size=6, timeout=20,
            # 25 min: o pooler do Supabase derruba conexão ociosa, e conexão
            # morta no poço vira erro na cara de quem abriu a tela
            max_idle=1500,
            kwargs=dict(row_factory=dict_row, autocommit=False,
                        # No pooler em modo TRANSAÇÃO (porta 6543) não há sessão
                        # entre uma consulta e outra: o `PREPARE` some antes do
                        # `EXECUTE`. O psycopg prepara sozinho a partir da 5ª
                        # execução da mesma consulta — então tudo funciona no
                        # começo e trava depois, que é o pior tipo de defeito.
                        # Foi o que segurou o arranque em "Waiting for
                        # application startup".
                        # None desliga; no Mac (5432, sessão de verdade) isso
                        # custa pouco e evita ter dois comportamentos.
                        prepare_threshold=None),
            open=True)
        # sem isto, script de linha de comando termina reclamando que não
        # conseguiu parar as threads do poço
        # `_POCO` pode já ter sido fechado por fechar_poco(); o atexit
        # não pode morrer por isso e sujar a saída de um script que terminou bem.
        atexit.register(fechar_poco)
    return _POCO


def fechar_poco():
    """Fecha o poço. Para quem roda script e quer sair limpo."""
    global _POCO
    if _POCO is not None:
        _POCO.close()
        _POCO = None


def conectar():
    """A conexão que o sistema usa. Sempre Postgres, por um poço de conexões."""
    return Ponte(_poco())


if __name__ == "__main__":
    exemplos = [
        "SELECT * FROM clientes WHERE nome_norm LIKE ? AND status=?",
        "SELECT date('now','localtime')",
        "SELECT count(*) FROM prazos WHERE data_fatal <= date('now','localtime','+7 day')",
        "SELECT cast(julianday('now') - julianday(criado_em) as int) FROM processos",
        "INSERT OR IGNORE INTO acao_motivos (acao_id, motivo_id) VALUES (?,?)",
        "SELECT * FROM clientes WHERE data_nascimento GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'",
        "SELECT strftime('%Y','now','localtime')",
    ]
    for e in exemplos:
        print(f"  {e}\n→ {traduzir(e)}\n")

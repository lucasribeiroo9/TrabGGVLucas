#!/usr/bin/env python3
"""Preenchimento em LOTE do organograma, a partir da planilha — uma vez só.

Os 72 funcionários vieram do Airtable sem setor e sem chefia: a origem tem
FUNÇÕES, não organograma. O Lucas está preenchendo isso numa planilha; este
script a lê e aplica de uma vez. **Depois dela, a fonte é a tela**
(`/equipe/{id}`) — resposta 30: hierarquia muda, e mudar não pode depender de
programador.

    ./.venv/bin/python equipe_setores.py equipe.csv                # só confere
    ./.venv/bin/python equipe_setores.py equipe.csv --aplicar      # grava
    ./.venv/bin/python equipe_setores.py --exportar equipe.csv     # tira do banco

O formato é o mais simples que resolve — quatro colunas, cabeçalho obrigatório:

    nome,setor,chefe,perfil
    Fulana de Tal,Petição Inicial,Beltrano da Silva,GESTOR
    Sicrano,Documentação,,

  · **nome**   casa por nome normalizado (`pessoas.nome_norm`), como a migração
    já casa: acento e caixa não contam, "Dr. Fulano" e "Fulano" são a mesma
    pessoa. Nome que não casa — ou que casa em mais de uma — é RECUSA, nunca
    palpite: aproximação por semelhança casa Marina com Marize, e isso já
    custou caro no Prev.
  · **setor**  tem de ser um dos que a governança conhece (`fluxo_etapas.grupo`).
    Vazio significa "deixe como está"; a palavra `-` significa "tire o setor".
  · **chefe**  outro nome, casado do mesmo jeito. Vazio deixa como está, `-`
    tira a chefia.
  · **perfil** ADVOGADO / GESTOR / DIRECAO, e só para quem já tem conta. Vazio
    deixa como está.

**Nada é gravado pela metade.** O arquivo inteiro é conferido antes — nome,
setor, chefe, perfil, e o laço de chefia que a soma das linhas criaria — e uma
linha ruim impede a carga toda. Meia planilha aplicada é pior que planilha
nenhuma: ninguém sabe onde parou, e o organograma fica metade novo, metade
velho.

Cada alteração deixa linha em `auditoria`, igual à da tela. `--quem` diz de
quem é a mão; sem ele o rastro fica com autor em branco, dito no relatório.
"""
import csv
import sys

import banco
import equipe
from normalizar import norm

MANTER = ""      # coluna vazia: não mexe
LIMPAR = "-"     # a palavra que apaga o valor


def _indice(db):
    """nome normalizado → (id, nome). Nome repetido vira lista, para recusar."""
    ix = {}
    for r in db.execute("SELECT id, nome, nome_norm, ativo FROM pessoas").fetchall():
        ix.setdefault(r["nome_norm"], []).append(r)
    return ix


def _casar(ix, nome):
    """(pessoa, erro). Recusa o que não casa e o que casa duas vezes."""
    chave = norm(nome)
    if not chave:
        return None, "nome em branco"
    achados = ix.get(chave) or []
    if not achados:
        return None, f"“{nome}” não está no cadastro (casando por nome normalizado)"
    if len(achados) > 1:
        return None, f"“{nome}” casa com {len(achados)} pessoas do cadastro"
    return achados[0], None


def ler(caminho, db):
    """(planos, recusas). Confere tudo, não grava nada."""
    ix = _indice(db)
    setores_validos = equipe.setores(db)
    perfis_validos = equipe.perfis(db)
    planos, recusas = [], []
    vistos = set()

    with open(caminho, newline="", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        faltando = {"nome", "setor", "chefe", "perfil"} - set(
            (c or "").strip().lower() for c in (leitor.fieldnames or []))
        if faltando:
            return [], [(0, "", "faltam colunas no cabeçalho: " + ", ".join(sorted(faltando)))]
        for n, linha in enumerate(leitor, start=2):
            v = {(k or "").strip().lower(): (val or "").strip()
                 for k, val in linha.items() if k}
            nome, setor, chefe, perfil = (v.get("nome", ""), v.get("setor", ""),
                                          v.get("chefe", ""), v.get("perfil", ""))
            if not any((nome, setor, chefe, perfil)):
                continue
            pessoa, erro = _casar(ix, nome)
            if erro:
                recusas.append((n, nome, erro))
                continue
            if pessoa["id"] in vistos:
                recusas.append((n, nome, "esta pessoa aparece duas vezes na planilha"))
                continue
            vistos.add(pessoa["id"])

            plano = dict(linha=n, id=pessoa["id"], nome=pessoa["nome"])
            if setor and setor != LIMPAR and setor not in setores_validos:
                recusas.append((n, nome, f"“{setor}” não é setor do escritório "
                                         f"(os que valem: {', '.join(setores_validos)})"))
                continue
            plano["setor"] = None if setor == LIMPAR else (setor or MANTER)

            plano["chefe_id"] = MANTER
            if chefe == LIMPAR:
                plano["chefe_id"] = None
            elif chefe:
                alvo, erro = _casar(ix, chefe)
                if erro:
                    recusas.append((n, nome, "chefe: " + erro))
                    continue
                if not alvo["ativo"]:
                    recusas.append((n, nome, f"chefe: {alvo['nome']} está inativa"))
                    continue
                if alvo["id"] == pessoa["id"]:
                    recusas.append((n, nome, "ninguém responde a si mesmo"))
                    continue
                plano["chefe_id"] = alvo["id"]

            plano["perfil"] = MANTER
            if perfil and perfil != LIMPAR:
                if perfil.upper() not in perfis_validos:
                    recusas.append((n, nome, f"“{perfil}” não é perfil de acesso "
                                             f"({', '.join(perfis_validos)})"))
                    continue
                tem = db.execute("SELECT 1 FROM usuarios WHERE pessoa_id=?",
                                 (pessoa["id"],)).fetchone()
                if not tem:
                    recusas.append((n, nome, "não tem conta de acesso: o perfil não tem "
                                             "onde ser gravado (abrir acesso é auth.py equipe)"))
                    continue
                plano["perfil"] = perfil.upper()
            planos.append(plano)

    recusas += _lacos(db, planos)
    # a linha recusada pelo laço já estava em `planos`: sai de lá, senão o
    # relatório diz "estavam boas" sobre a linha que ele acabou de recusar
    ruins = {n for n, _, _ in recusas}
    return [p for p in planos if p["linha"] not in ruins], recusas


def _lacos(db, planos):
    """O laço que a SOMA das linhas criaria — que nenhuma linha sozinha mostra.

    A planilha pode trazer A→B numa linha e B→A vinte linhas abaixo: cada uma
    passa sozinha, e juntas fecham o ciclo. Por isso o grafo é montado inteiro
    — o que já está no banco mais o que a planilha muda — e só então se procura
    a volta.
    """
    chefe = {r["id"]: r["supervisor_id"] for r in
             db.execute("SELECT id, supervisor_id FROM pessoas").fetchall()}
    nome = {r["id"]: r["nome"] for r in
            db.execute("SELECT id, nome FROM pessoas").fetchall()}
    onde = {}
    for p in planos:
        if p["chefe_id"] != MANTER:
            chefe[p["id"]] = p["chefe_id"]
            onde[p["id"]] = p["linha"]
    ruins = []
    for pid in list(chefe):
        visto, atual, caminho = set(), pid, []
        while atual:
            if atual in visto:
                if pid in visto and pid in onde:
                    ruins.append((onde[pid], nome.get(pid, "?"),
                                  "esta linha fecha um laço de chefia: " +
                                  " → ".join(nome.get(x, "?") for x in caminho[:6])))
                break
            visto.add(atual)
            caminho.append(atual)
            atual = chefe.get(atual)
    # o mesmo laço aparece uma vez por participante; basta dizê-lo uma
    return sorted({r for r in ruins})


def aplicar(db, planos, quem=None):
    """Grava tudo. Cada campo mexido deixa a MESMA linha de auditoria da tela.

    Chama `equipe.mudar_*` em vez de escrever `UPDATE` aqui: a validação e o
    rastro têm de ser os mesmos da tela, senão a planilha vira a porta dos
    fundos por onde entra o que a tela recusa.
    """
    mexidas = []
    for p in planos:
        if p["setor"] != MANTER:
            ok, recado = equipe.mudar_setor(db, p["id"], p["setor"], quem)
            if ok:
                mexidas.append((p["nome"], recado))
        if p["chefe_id"] != MANTER:
            ok, recado = equipe.mudar_chefe(db, p["id"], p["chefe_id"], quem)
            if ok:
                mexidas.append((p["nome"], recado))
        if p["perfil"] != MANTER:
            ok, recado = equipe.mudar_perfil(db, p["id"], p["perfil"], quem)
            if ok:
                mexidas.append((p["nome"], recado))
    return mexidas


def exportar(db, caminho):
    """O organograma de hoje, no mesmo formato — é como se faz a volta.

    Serve a duas coisas: conferir a planilha contra o que ficou no banco, e ter
    de onde repor o organograma se `migrar.py` recriar `pessoas` (a migração
    recria as linhas e o setor vai junto; as contas ela preserva, o organograma
    ainda não).
    """
    linhas = db.execute("""SELECT p.nome, p.setor, s.nome chefe, u.papel
                           FROM pessoas p
                           LEFT JOIN pessoas s ON s.id = p.supervisor_id
                           LEFT JOIN usuarios u ON u.pessoa_id = p.id
                           ORDER BY p.setor NULLS FIRST, p.nome""").fetchall()
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        e = csv.writer(f)
        e.writerow(["nome", "setor", "chefe", "perfil"])
        for l in linhas:
            e.writerow([l["nome"], l["setor"] or "", l["chefe"] or "", l["papel"] or ""])
    return len(linhas)


def _quem(db, texto):
    if not texto:
        return None
    r = db.execute("""SELECT p.id FROM pessoas p LEFT JOIN usuarios u ON u.pessoa_id=p.id
                      WHERE p.nome_norm=? OR lower(u.email)=?""",
                   (norm(texto), texto.strip().lower())).fetchone()
    if not r:
        sys.exit(f"✗ --quem: “{texto}” não casa com pessoa nem com conta do escritório.")
    return r[0]


def main(argv):
    args = [a for a in argv[1:]]
    aplicar_mesmo = "--aplicar" in args
    exportar_pedido = "--exportar" in args
    quem_txt = None
    if "--quem" in args:
        i = args.index("--quem")
        quem_txt = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    caminhos = [a for a in args if not a.startswith("--")]
    if not caminhos:
        sys.exit(__doc__)
    caminho = caminhos[0]

    db = banco.conectar()
    try:
        if exportar_pedido:
            n = exportar(db, caminho)
            print(f"✓ {n} linha(s) em {caminho} — o organograma como está agora.")
            return 0

        quem = _quem(db, quem_txt)
        planos, recusas = ler(caminho, db)

        if recusas:
            print(f"✗ {len(recusas)} linha(s) recusada(s). NADA foi gravado — planilha "
                  "aplicada pela metade é pior que planilha nenhuma.\n")
            for n, nome, porque in sorted(recusas):
                print(f"  linha {n:>3}  {nome[:28]:<30} {porque}")
            print(f"\n  {len(planos)} linha(s) estavam boas e ficaram de fora junto. "
                  "Conserte as de cima e rode de novo.")
            return 1

        print(f"{len(planos)} linha(s) conferidas, nenhuma recusa.")
        if not aplicar_mesmo:
            for p in planos[:200]:
                partes = []
                if p["setor"] != MANTER:
                    partes.append(f"setor={p['setor'] or 'sem setor'}")
                if p["chefe_id"] != MANTER:
                    partes.append("responde a=" +
                                  (db.execute("SELECT nome FROM pessoas WHERE id=?",
                                              (p["chefe_id"],)).fetchone()[0]
                                   if p["chefe_id"] else "ninguém"))
                if p["perfil"] != MANTER:
                    partes.append(f"perfil={p['perfil']}")
                if partes:
                    print(f"  {p['nome'][:30]:<32} {' · '.join(partes)}")
            print("\nNada foi gravado: isto foi a conferência. Rode com --aplicar.")
            return 0

        mexidas = aplicar(db, planos, quem)
        print(f"✓ {len(mexidas)} alteração(ões) gravada(s), cada uma com linha em auditoria.")
        for nome, recado in mexidas[:200]:
            print(f"  {nome[:30]:<32} {recado}")
        if not quem:
            print("\n  Sem --quem: as linhas de auditoria ficaram sem autor. Da próxima vez, "
                  "passe --quem <nome ou e-mail> para o rastro dizer de quem foi a mão.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))


import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver

BASE = Path(__file__).resolve().parent
BANCO = BASE / "contatos.db"
CSV_SAIDA = BASE / "contatos.csv"
PERFIL = BASE / "edge_whatsapp"


PADRAO_TELEFONE = re.compile(
    r"(?<!\d)\+?\d(?:[\s().-]*\d){9,14}(?!\d)"
)


def preparar_banco():
    with sqlite3.connect(BANCO) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contatos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telefone TEXT UNIQUE NOT NULL,
                grupo TEXT NOT NULL,
                data_coleta TEXT NOT NULL
            )
        """)


def extrair_numeros(texto):
    numeros = set()

    for linha in texto.splitlines():
        for candidato in PADRAO_TELEFONE.findall(linha):
            numero = re.sub(r"\D", "", candidato)

            if 10 <= len(numero) <= 15:
                numeros.add(numero)

    return numeros


def salvar_contatos(numeros, grupo):
    novos = 0

    with sqlite3.connect(BANCO) as conn:
        for numero in sorted(numeros):
            cursor = conn.execute("""
                INSERT OR IGNORE INTO contatos
                (telefone, grupo, data_coleta)
                VALUES (?, ?, ?)
            """, (
                numero,
                grupo,
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ))

            novos += cursor.rowcount

    return novos


def exportar_csv():
    with sqlite3.connect(BANCO) as conn:
        registros = conn.execute("""
            SELECT telefone, grupo, data_coleta
            FROM contatos
            ORDER BY id
        """).fetchall()

    with open(
        CSV_SAIDA,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as arquivo:
        escritor = csv.writer(arquivo)

        escritor.writerow([
            "Telefone",
            "Grupo",
            "Data"
        ])

        escritor.writerows(registros)

    return len(registros)


def abrir_whatsapp():
    opcoes = webdriver.EdgeOptions()

    opcoes.add_argument(
        f"--user-data-dir={PERFIL}"
    )

    driver = webdriver.Edge(options=opcoes)

    driver.get("https://web.whatsapp.com/")

    return driver


def selecionar_lista(driver):
    resultado = driver.execute_script("""
        delete window.__listaContatos;

        const visivel = (elemento) => {
            const retangulo = elemento.getBoundingClientRect();
            const estilo = getComputedStyle(elemento);

            return (
                retangulo.width > 180 &&
                retangulo.height > 130 &&
                retangulo.bottom > 0 &&
                retangulo.right > 0 &&
                retangulo.top < window.innerHeight &&
                retangulo.left < window.innerWidth &&
                estilo.display !== 'none' &&
                estilo.visibility !== 'hidden'
            );
        };

        // Prioriza a janela de participantes, quando existir.
        const dialogos = Array.from(
            document.querySelectorAll('[role="dialog"]')
        ).filter(visivel);

        const raizes = dialogos.length
            ? dialogos
            : [document.body];

        const candidatos = [];
        const vistos = new Set();

        for (const raiz of raizes) {
            const elementos = [
                raiz,
                ...raiz.querySelectorAll('div, section')
            ];

            for (const elemento of elementos) {
                if (vistos.has(elemento)) continue;
                vistos.add(elemento);

                if (!visivel(elemento)) continue;

                // Evita a lista de conversas e as mensagens.
                if (elemento.closest('#pane-side, #side, #main')) {
                    continue;
                }

                const estilo = getComputedStyle(elemento);

                if (!['auto', 'scroll'].includes(estilo.overflowY)) {
                    continue;
                }

                if (
                    elemento.scrollHeight <=
                    elemento.clientHeight + 20
                ) {
                    continue;
                }

                const texto = elemento.innerText || '';

                // Exige pelo menos um telefone visível.
                const telefones = texto.match(
                    /(?:\\+?\\d[\\d ().-]{8,}\\d)/g
                ) || [];

                if (!telefones.length) continue;

                candidatos.push(elemento);
            }
        }

        // Em painéis aninhados, prioriza o contêiner interno.
        const internos = candidatos.filter(
            elemento => !candidatos.some(
                outro => outro !== elemento &&
                         elemento.contains(outro)
            )
        );

        // Não escolhe às cegas entre várias listas.
        if (internos.length !== 1) {
            return {
                ok: false,
                quantidade: internos.length
            };
        }

        window.__listaContatos = internos[0];
        window.__listaContatos.scrollTop = 0;

        return {ok: true};
    """)

    if not resultado or not resultado.get("ok"):
        print(
            "\nNão consegui identificar uma única lista "
            "de participantes com telefones visíveis."
        )
        print(
            "Abra os dados do grupo e clique em "
            "'Ver todos' os participantes, se aparecer."
        )
        return False

 
    time.sleep(1)

    print("Lista identificada automaticamente!")
    return True

def capturar_lista(driver):
    encontrados = set()

    sem_avancar = 0

    while True:
        resultado = driver.execute_script("""
            const lista = window.__listaContatos;

            if (!lista || !lista.isConnected)
                return null;

            const texto = lista.innerText || '';

            const antes = lista.scrollTop;

            const passo = Math.max(
                160,
                Math.floor(lista.clientHeight * 0.7)
            );

            lista.scrollTop = antes + passo;

            return {
                texto,
                antes,
                depois: lista.scrollTop
            };
        """)

        if resultado is None:
            print(
                "\nA lista foi fechada ou mudou de lugar."
            )
            break

        encontrados.update(
            extrair_numeros(resultado["texto"])
        )

        print(
            f"\rTelefones identificados: {len(encontrados)}",
            end="",
            flush=True
        )

        if resultado["depois"] <= resultado["antes"]:
            sem_avancar += 1
        else:
            sem_avancar = 0

        if sem_avancar >= 4:

            texto_final = driver.execute_script("""
                const lista = window.__listaContatos;

                return lista && lista.isConnected
                    ? lista.innerText
                    : '';
            """)

            encontrados.update(
                extrair_numeros(texto_final)
            )

            break

        time.sleep(0.7)

    print()

    return encontrados


def main():
    preparar_banco()

    print("=" * 50)
    print("        CAPTURADOR DE CONTATOS")
    print("=" * 50)

    grupo = input(
        "\nNome do grupo autorizado: "
    ).strip()

    if not grupo:
        print("Informe o nome do grupo.")
        return

    driver = abrir_whatsapp()

    try:
        input(
            "\nFaça login (se necessário), abra o grupo "
            "e a lista de participantes. "
            "Depois pressione ENTER... "
        )

        if not selecionar_lista(driver):
            print(
                "Não foi possível identificar a lista. "
                "Tente novamente."
            )
            return

        print("\nIniciando leitura dos contatos...\n")

        numeros = capturar_lista(driver)

        novos = salvar_contatos(
            numeros,
            grupo
        )

        total = exportar_csv()

        print("\n" + "=" * 50)
        print("          CAPTURA FINALIZADA")
        print("=" * 50)

        print(
            f"Telefones identificados: {len(numeros)}"
        )

        print(
            f"Novos registros no banco: {novos}"
        )

        print(
            f"Total no banco: {total}"
        )

        print(f"Banco: {BANCO}")
        print(f"CSV: {CSV_SAIDA}")

    finally:
        try:
            input(
                "\nPressione ENTER quando quiser fechar o Edge..."
            )
        finally:
            driver.quit()

if __name__ == "__main__":
    main()

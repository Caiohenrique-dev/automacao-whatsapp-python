import csv
import re
import sqlite3
import time
import traceback
from pathlib import Path
from urllib.parse import urlencode

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


PASTA = Path(__file__).resolve().parent

ORIGEM = "db" 

BANCO = PASTA / "contatos.db"
CSV = PASTA / "contatos.csv"
REGISTRO = PASTA / "registro_whatsapp.db"
PERFIL_EDGE = PASTA / "edge_whatsapp"

TABELA = "contatos"
COLUNA_TELEFONE = "telefone"

CAMPANHA = "aviso_clientes_001"
INTERVALO = 5

MENSAGEM = """Olá! Tudo bem?

Esta é uma mensagem de demonstração do projeto.

"""

SELETOR_CAMPO = (
    "#main footer [contenteditable='true'][role='textbox']"
)


def normalizar_telefone(valor):
    numero = re.sub(r"\D", "", str(valor or ""))

    if len(numero) in (10, 11):
        numero = "55" + numero

    if not 10 <= len(numero) <= 15:
        raise ValueError("Telefone inválido.")

    return numero


def identificador_sql(nome):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nome):
        raise ValueError("Nome de tabela ou coluna inválido.")

    return f'"{nome}"'


def carregar_contatos():
    if ORIGEM == "db":
        if not BANCO.is_file():
            raise FileNotFoundError(f"Banco não encontrado: {BANCO}")

        tabela = identificador_sql(TABELA)
        coluna = identificador_sql(COLUNA_TELEFONE)

        with sqlite3.connect(
            BANCO.as_uri() + "?mode=ro", uri=True
        ) as conn:
            valores = [
                linha[0]
                for linha in conn.execute(
                    f"SELECT {coluna} FROM {tabela}"
                )
            ]

    elif ORIGEM == "csv":
        with CSV.open(
            encoding="utf-8-sig", newline=""
        ) as arquivo:
            amostra = arquivo.read(4096)
            arquivo.seek(0)

            try:
                formato = csv.Sniffer().sniff(
                    amostra, delimiters=",;"
                )
            except csv.Error:
                formato = csv.excel

            leitor = csv.DictReader(arquivo, dialect=formato)

            colunas = {
                nome.strip().lower(): nome
                for nome in (leitor.fieldnames or [])
                if nome
            }

            chave = colunas.get(COLUNA_TELEFONE.lower())

            if chave is None:
                raise ValueError(
                    "O CSV precisa de uma coluna telefone."
                )

            valores = [
                linha.get(chave, "")
                for linha in leitor
            ]

    else:
        raise ValueError('ORIGEM deve ser "db" ou "csv".')

    contatos = set()

    for valor in valores:
        try:
            contatos.add(normalizar_telefone(valor))
        except ValueError:
            print("Um telefone inválido foi ignorado.")

    return sorted(contatos)


def preparar_registro(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS envios (
            campanha TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status TEXT NOT NULL,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (campanha, telefone)
        )
    """)
    conn.commit()


def reservar_contato(conn, telefone):
    cursor = conn.execute("""
        INSERT INTO envios (campanha, telefone, status)
        VALUES (?, ?, 'em_processamento')
        ON CONFLICT(campanha, telefone) DO UPDATE SET
            status = 'em_processamento',
            atualizado_em = CURRENT_TIMESTAMP
        WHERE envios.status = 'falha_pre_envio_v2'
    """, (CAMPANHA, telefone))
    conn.commit()

    return cursor.rowcount > 0


def atualizar_status(conn, telefone, status):
    conn.execute("""
        UPDATE envios
        SET status = ?, atualizado_em = CURRENT_TIMESTAMP
        WHERE campanha = ? AND telefone = ?
    """, (status, CAMPANHA, telefone))
    conn.commit()


def normalizar_texto(texto):
    texto = texto.replace("\ufe0f", "")
    texto = texto.replace("\u200b", "")
    return re.sub(r"\s+", " ", texto).strip()


def ler_texto_campo(driver, campo):
    # Lê o texto e o alt dos emojis sem modificar a página.
    return driver.execute_script("""
        function ler(no) {
            if (no.nodeType === Node.TEXT_NODE) {
                return no.nodeValue || '';
            }

            if (no.nodeType !== Node.ELEMENT_NODE) {
                return '';
            }

            if (no.tagName === 'IMG') {
                return no.getAttribute('alt') || '';
            }

            if (no.tagName === 'BR') {
                return '\\n';
            }

            let texto = Array.from(no.childNodes)
                .map(ler)
                .join('');

            if (['DIV', 'P', 'LI'].includes(no.tagName)) {
                texto += '\\n';
            }

            return texto;
        }

        return ler(arguments[0]);
    """, campo)


def localizar_campo(driver):
    for campo in driver.find_elements(
        By.CSS_SELECTOR, SELETOR_CAMPO
    ):
        if campo.is_displayed() and campo.is_enabled():
            return campo

    return False


def campo_com_mensagem(driver):
    try:
        campo = localizar_campo(driver)

        if not campo:
            return False

        texto = ler_texto_campo(driver, campo)

        if normalizar_texto(texto) == normalizar_texto(MENSAGEM):
            return campo

    except StaleElementReferenceException:
        pass

    return False


def campo_vazio(driver):
    try:
        campo = localizar_campo(driver)

        if not campo:
            return False

        return not normalizar_texto(
            ler_texto_campo(driver, campo)
        )

    except StaleElementReferenceException:
        return False


def executar():
    if not MENSAGEM.strip():
        raise ValueError("A mensagem está vazia.")

    contatos = carregar_contatos()
    print(f"Contatos únicos válidos: {len(contatos)}")

    if not contatos:
        return

    with sqlite3.connect(REGISTRO) as conn:
        preparar_registro(conn)

        PERFIL_EDGE.mkdir(parents=True, exist_ok=True)

        opcoes = webdriver.EdgeOptions()
        opcoes.add_argument(f"--user-data-dir={PERFIL_EDGE}")
        opcoes.add_argument("--profile-directory=Default")
        opcoes.add_argument("--start-maximized")

        driver = webdriver.Edge(options=opcoes)

        acionados = 0
        ignorados = 0
        falhas = 0

        try:
            driver.get("https://web.whatsapp.com/")

            print("Aguardando login. Leia o QR Code se necessário.")

            WebDriverWait(driver, 180).until(
                lambda navegador: any(
                    elemento.is_displayed()
                    for elemento in navegador.find_elements(
                        By.ID, "pane-side"
                    )
                )
            )

            print("WhatsApp conectado. Iniciando automaticamente.")

            for indice, telefone in enumerate(contatos, 1):
                if not reservar_contato(conn, telefone):
                    ignorados += 1
                    print(
                        f"[{indice}/{len(contatos)}] "
                        "Registro anterior preservado: ignorado."
                    )
                    continue

                envio_iniciado = False
                etapa = "abrir conversa"

                try:
                    print(
                        f"\n[{indice}/{len(contatos)}] "
                        f"Contato final {telefone[-4:]}"
                    )

                    parametros = urlencode({
                        "phone": telefone,
                        "text": MENSAGEM.strip(),
                    })

                    driver.get(
                        "https://web.whatsapp.com/send?"
                        + parametros
                    )

                    espera = WebDriverWait(driver, 60)

                    etapa = "localizar o campo com a mensagem"
                    campo = espera.until(campo_com_mensagem)

                    etapa = "focar o campo"
                    campo.click()

                    etapa = "enviar com ENTER"

                    # Registra antes da ação para não repetir
                    # uma tentativa cujo resultado seja incerto.
                    envio_iniciado = True
                    campo.send_keys(Keys.ENTER)

                    etapa = "aguardar o campo esvaziar"
                    espera.until(campo_vazio)

                    atualizar_status(
                        conn, telefone, "acionado_na_interface"
                    )
                    acionados += 1

                    print("Envio acionado. Continuando automaticamente.")

                except Exception:
                    falhas += 1

                    status = (
                        "resultado_incerto"
                        if envio_iniciado
                        else "falha_pre_envio_v2"
                    )

                    atualizar_status(conn, telefone, status)

                    print(f"Falha na etapa: {etapa}")
                    traceback.print_exc()

                    if envio_iniciado:
                        print(
                            "Resultado incerto: não haverá "
                            "nova tentativa automática para este contato."
                        )
                    else:
                        print(
                            "Nenhum comando de envio foi acionado "
                            "para este contato."
                        )

                    # Se o navegador fechou, encerra o processamento.
                    try:
                        if not driver.window_handles:
                            break
                    except Exception:
                        break

                if indice < len(contatos):
                    print(
                        f"Avançando para o próximo em {INTERVALO} segundos..."
                    )
                    time.sleep(INTERVALO)

        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.")

        finally:
            print("\n" + "=" * 50)
            print(f"Envios acionados: {acionados}")
            print(f"Registros anteriores ignorados: {ignorados}")
            print(f"Falhas nesta execução: {falhas}")
            print("=" * 50)

            driver.quit()


if __name__ == "__main__":
    try:
        executar()
    except Exception:
        traceback.print_exc()

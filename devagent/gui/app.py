"""Interface gráfica moderna para análise de projetos."""

from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable

import customtkinter as ctk

from ..models import ResultadoScanner
from ..exceptions import ErroVarreduraError
from ..scanner import ProjectScanner

# ── Paleta de cores ──────────────────────────────────────────────────
COR_FUNDO       = "#0D1117"
COR_CARTAO      = "#161B22"
COR_BORDA       = "#30363D"
COR_TEXTO       = "#C9D1D9"
COR_TEXTO_DIM   = "#8B949E"
COR_PRIMARIA    = "#58A6FF"
COR_SUCESSO     = "#3FB950"
COR_ERRO        = "#F85149"
COR_ALERTA      = "#D29922"
COR_ROSA        = "#F778BA"
COR_FUNDO_ENTRY = "#0D1117"

# ── Helpers ──────────────────────────────────────────────────────────
def _card(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """Cria um cartão visual padronizado.

    Args:
        parent: Widget pai do cartão.

    Returns:
        Frame estilizado para agrupar controles.
    """
    return ctk.CTkFrame(parent, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)

def _label(master, text: str, size: int = 13, weight: str = "normal", color: str = COR_TEXTO) -> ctk.CTkLabel:
    """Cria um rótulo com a tipografia visual da aplicação.

    Args:
        master: Widget pai do rótulo.
        text: Texto exibido.
        size: Tamanho da fonte.
        weight: Peso da fonte.
        color: Cor do texto.

    Returns:
        Rótulo configurado.
    """
    return ctk.CTkLabel(master, text=text, text_color=color, font=ctk.CTkFont(size=size, weight=weight))

def _badge(master, text: str) -> ctk.CTkLabel:
    """Cria um badge compacto para informações de estado ou versão.

    Args:
        master: Widget pai do badge.
        text: Texto exibido no badge.

    Returns:
        Rótulo estilizado como badge.
    """
    return ctk.CTkLabel(
        master, text=text,
        text_color=COR_PRIMARIA, font=ctk.CTkFont(size=11, weight="bold"),
        fg_color="#1F2937", corner_radius=6, padx=8, pady=2,
    )


# ── Header ───────────────────────────────────────────────────────────
class HeaderFrame(ctk.CTkFrame):
    """Cabeçalho com o nome, versão e estado atual da aplicação."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Inicializa o cabeçalho.

        Args:
            master: Widget pai do cabeçalho.
        """
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Título
        titulo = ctk.CTkFrame(self, fg_color="transparent")
        titulo.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            titulo, text="DevAgent", font=ctk.CTkFont(size=30, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            titulo, text="Analisador inteligente de projetos Python",
            text_color=COR_TEXTO_DIM, font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(2, 0))

        # Badge + status
        direita = ctk.CTkFrame(self, fg_color="transparent")
        direita.grid(row=0, column=1, sticky="e")
        _badge(direita, "v0.2.0")
        self._lbl_status = ctk.CTkLabel(
            direita, text="● Pronto", text_color=COR_SUCESSO,
            font=ctk.CTkFont(size=12), anchor="e",
        )
        self._lbl_status.pack(side="right", padx=(12, 0))

    @property
    def status_label(self) -> ctk.CTkLabel:
        """Retorna o rótulo usado para atualizar o estado da aplicação.

        Returns:
            Rótulo de status do cabeçalho.
        """
        return self._lbl_status


# ── Seleção de pasta ─────────────────────────────────────────────────
class SelecaoFrame(ctk.CTkFrame):
    """Painel para escolher a pasta do projeto."""

    def __init__(self, master: ctk.CTkBaseClass, ao_escolher: "Callable[[], None] | None" = None) -> None:
        """Inicializa os controles de seleção e análise.

        Args:
            master: Widget pai do painel.
            ao_escolher: Callback executado ao solicitar uma análise.
        """
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self._ao_escolher = ao_escolher or (lambda: None)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        ctk.CTkLabel(
            self, text="📁  Projeto", font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, padx=(16, 8), pady=(14, 6), sticky="w")

        self._var = ctk.StringVar()
        self.entrada = ctk.CTkEntry(
            self, textvariable=self._var,
            placeholder_text="/caminho/para/seu/projeto",
            fg_color=COR_FUNDO_ENTRY, border_color=COR_BORDA,
            text_color=COR_TEXTO, font=ctk.CTkFont(size=13),
        )
        self.entrada.grid(row=1, column=0, padx=(16, 8), pady=(0, 14), sticky="ew")
        self.entrada.bind("<Return>", lambda _: self._ao_escolher())

        ctk.CTkButton(
            self, text="Procurar…", width=110,
            fg_color="#21262D", hover_color="#30363D",
            border_width=1, border_color=COR_BORDA,
            command=self._escolher_pasta,
        ).grid(row=1, column=1, padx=(0, 8), pady=(0, 14))

        self.analisar_btn = ctk.CTkButton(
            self, text="🔍  Analisar", height=36,
            fg_color=COR_PRIMARIA, hover_color="#388BFF",
            command=self._ao_escolher,
        )
        self.analisar_btn.grid(row=1, column=2, padx=(0, 16), pady=(0, 14))

    def _escolher_pasta(self) -> None:
        """Abre o diálogo nativo e preenche o caminho selecionado."""
        pasta = filedialog.askdirectory(title="Selecione o projeto")
        if pasta:
            self.entrada.delete(0, "end")
            self.entrada.insert(0, pasta)

    def pasta(self) -> str:
        """Retorna o caminho digitado ou selecionado.

        Returns:
            Caminho sem espaços nas extremidades.
        """
        return self._var.get().strip()


# ── Métricas ─────────────────────────────────────────────────────────
class MetricasFrame(ctk.CTkFrame):
    """Cards de métricas resumidas."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Inicializa os cartões de métricas.

        Args:
            master: Widget pai do painel.
        """
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._cards: list[ctk.CTkLabel] = []
        dados = [
            ("Arquivos", "—", COR_PRIMARIA),
            ("Diretórios", "—", COR_ROSA),
            ("Tamanho", "—", COR_ALERTA),
            ("Extensões", "—", COR_SUCESSO),
        ]
        for i, (rotulo, valor, cor) in enumerate(dados):
            frame = ctk.CTkFrame(self, fg_color="transparent")
            frame.grid(row=0, column=i, padx=10, pady=12, sticky="ew")
            frame.grid_columnconfigure(0, weight=1)
            _label(frame, rotulo, size=11, weight="normal", color=COR_TEXTO_DIM).grid(row=0, column=0, sticky="w")
            lbl = _label(frame, valor, size=18, weight="bold", color=cor)
            lbl.grid(row=1, column=0, sticky="w", pady=(2, 0))
            self._cards.append(lbl)

    def atualizar(self, arquivos: int, diretorios: int, tamanho_bytes: int, extensoes: int) -> None:
        """Atualiza os valores exibidos nos cartões.

        Args:
            arquivos: Quantidade de arquivos encontrados.
            diretorios: Quantidade de diretórios encontrados.
            tamanho_bytes: Tamanho total dos arquivos em bytes.
            extensoes: Quantidade de extensões distintas.
        """
        valores = [
            f"{arquivos:,}",
            f"{diretorios:,}",
            self._formatar_tamanho(tamanho_bytes),
            str(extensoes),
        ]
        for lbl, v in zip(self._cards, valores):
            lbl.configure(text=v)

    @staticmethod
    def _formatar_tamanho(bytes_: int) -> str:
        """Converte bytes para uma unidade legível.

        Args:
            bytes_: Tamanho a converter.

        Returns:
            Tamanho formatado em B, KB, MB ou GB.
        """
        if bytes_ >= 1_073_741_824:
            return f"{bytes_ / 1_073_741_824:.1f} GB"
        if bytes_ >= 1_048_576:
            return f"{bytes_ / 1_048_576:.1f} MB"
        if bytes_ >= 1024:
            return f"{bytes_ / 1024:.1f} KB"
        return f"{bytes_} B"


# ── Barra de progresso ───────────────────────────────────────────────
class ProgressoFrame(ctk.CTkFrame):
    """Exibe o progresso e o estado textual da análise."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Inicializa a barra de progresso.

        Args:
            master: Widget pai do painel.
        """
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        self.barra = ctk.CTkProgressBar(
            self, mode="indeterminate",
            progress_color=COR_PRIMARIA, height=6,
        )
        self.barra.grid(row=0, column=0, padx=28, sticky="ew")
        self.barra.set(0)

        self._lbl = ctk.CTkLabel(
            self, text="Pronto", text_color=COR_TEXTO_DIM,
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self._lbl.grid(row=1, column=0, padx=28, pady=(2, 0), sticky="w")

    def iniciar(self) -> None:
        """Inicia a animação de progresso indeterminado."""
        self.barra.start()
        self._lbl.configure(text="Analisando…", text_color=COR_PRIMARIA)

    def concluir(self) -> None:
        """Marca a análise como concluída."""
        self.barra.stop()
        self.barra.set(1)
        self._lbl.configure(text="Concluído", text_color=COR_SUCESSO)

    def falhar(self) -> None:
        """Marca a análise como falha e zera a barra."""
        self.barra.stop()
        self.barra.set(0)
        self._lbl.configure(text="Falha", text_color=COR_ERRO)

    def resetar(self) -> None:
        """Retorna o painel ao estado inicial."""
        self.barra.stop()
        self.barra.set(0)
        self._lbl.configure(text="Pronto", text_color=COR_TEXTO_DIM)


# ── Abas ─────────────────────────────────────────────────────────────
class AbasFrame(ctk.CTkTabview):
    """Agrupa as visualizações de árvore, estatísticas e JSON."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Inicializa as abas e seus campos de texto.

        Args:
            master: Widget pai do painel.
        """
        super().__init__(master, fg_color=COR_CARTAO, border_width=0, corner_radius=12)
        self.tab_arborescente = self.add("🌳  Árvore")
        self.tab_estatistica = self.add("📊  Estatísticas")
        self.tab_json = self.add("📄  JSON")

        # Árvore
        self.tab_arborescente.grid_rowconfigure(0, weight=1)
        self.tab_arborescente.grid_columnconfigure(0, weight=1)
        self.arvore = ctk.CTkTextbox(
            self.tab_arborescente, wrap="none",
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color=COR_FUNDO_ENTRY, border_color=COR_BORDA,
        )
        self.arvore.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        # Estatísticas
        self.tab_estatistica.grid_rowconfigure(0, weight=1)
        self.tab_estatistica.grid_columnconfigure(0, weight=1)
        self.estatisticas_box = ctk.CTkTextbox(
            self.tab_estatistica, wrap="word",
            font=ctk.CTkFont(size=13),
            fg_color=COR_FUNDO_ENTRY, border_color=COR_BORDA,
        )
        self.estatisticas_box.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        # JSON
        self.tab_json.grid_rowconfigure(1, weight=1)
        self.tab_json.grid_columnconfigure(0, weight=1)
        self.json_box = ctk.CTkTextbox(
            self.tab_json, wrap="none",
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color=COR_FUNDO_ENTRY, border_color=COR_BORDA,
        )
        self.json_box.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

    def limpar_tudo(self) -> None:
        """Remove o conteúdo de todas as abas de resultados."""
        for w in (self.arvore, self.estatisticas_box, self.json_box):
            w.delete("1.0", "end")


# ── Log de execução ──────────────────────────────────────────────────
class LogFrame(ctk.CTkFrame):
    """Exibe o log textual da execução da análise."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        """Inicializa o painel de log.

        Args:
            master: Widget pai do painel.
        """
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="ew")
        _label(top, "📋  Log de execução", size=14, weight="bold").pack(side="left")
        self._btn_limpar = ctk.CTkButton(
            top, text="Limpar", width=80, height=28,
            fg_color="#21262D", hover_color="#30363D",
            border_width=1, border_color=COR_BORDA,
            command=self.limpar,
        )
        self._btn_limpar.pack(side="right")

        self.caixa = ctk.CTkTextbox(
            self, wrap="word", state="disabled",
            font=ctk.CTkFont(family="Courier", size=11),
            fg_color=COR_FUNDO_ENTRY, border_color=COR_BORDA,
        )
        self.caixa.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")

    def adicionar(self, mensagem: str) -> None:
        """Adiciona uma mensagem ao final do log.

        Args:
            mensagem: Texto que será registrado.
        """
        self.caixa.configure(state="normal")
        self.caixa.insert("end", mensagem + "\n")
        self.caixa.see("end")
        self.caixa.configure(state="disabled")

    def limpar(self) -> None:
        """Remove todas as mensagens do log."""
        self.caixa.configure(state="normal")
        self.caixa.delete("1.0", "end")
        self.caixa.configure(state="disabled")


# ── Janela principal ─────────────────────────────────────────────────
class DevAgentApp(ctk.CTk):
    """Janela principal com análise assíncrona, progresso e muito mais."""

    def __init__(self) -> None:
        """Inicializa a janela principal e agenda o processamento da fila."""
        super().__init__()
        self.title("DevAgent — Analisador de Projetos")
        self.geometry("1200x800")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COR_FUNDO)

        self._fila: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._cancelar_event = threading.Event()
        self._resultado: ResultadoScanner | None = None

        self._construir_interface()
        self.after(100, self._processar_fila)

    # ── Interface ──────────────────────────────────────────────────
    def _construir_interface(self) -> None:
        """Cria e posiciona todos os painéis da janela."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        HeaderFrame(self).grid(row=0, column=0, padx=28, pady=(20, 8), sticky="ew")
        self._selecao = SelecaoFrame(self, ao_escolher=self._iniciar_analise)
        self._selecao.grid(row=1, column=0, padx=28, pady=8, sticky="ew")
        MetricasFrame(self).grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        ProgressoFrame(self).grid(row=3, column=0, padx=28, pady=(4, 0), sticky="ew")
        AbasFrame(self).grid(row=4, column=0, padx=28, pady=8, sticky="nsew")
        LogFrame(self).grid(row=5, column=0, padx=28, pady=(8, 20), sticky="nsew")

        self._metricas = MetricasFrame(self.winfo_children()[2])  # type: ignore[arg-type]
        self._progress = ProgressoFrame(self.winfo_children()[3])  # type: ignore[arg-type]
        self._abas = AbasFrame(self.winfo_children()[4])  # type: ignore[arg-type]
        self._log = LogFrame(self.winfo_children()[5])  # type: ignore[arg-type]
        self._status = HeaderFrame(self.winfo_children()[0]).status_label  # type: ignore[arg-type]

    # ── Ações ──────────────────────────────────────────────────────
    def _iniciar_analise(self) -> None:
        """Valida o caminho e inicia uma análise em segundo plano.

        Raises:
            O diálogo gráfico informa caminhos inválidos ao usuário sem lançar
            exceção para o loop principal.
        """
        caminho = Path(self._selecao.pasta()).expanduser()
        if not caminho.exists() or not caminho.is_dir():
            ctk.messagebox.showwarning("Caminho inválido", "Informe uma pasta válida para analisar.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._cancelar_event.clear()
        self._selecao.analisar_btn.configure(state="disabled")
        self._progress.iniciar()
        self._status.configure(text="● Analisando…", text_color=COR_PRIMARIA)
        self._log.adicionar(f"[{self._agora()}] Iniciando análise: {caminho}")
        self._thread = threading.Thread(
            target=self._analisar_em_background, args=(caminho,), daemon=True,
        )
        self._thread.start()

    def _analisar_em_background(self, caminho: Path) -> None:
        """Executa o scanner fora da thread da interface.

        Args:
            caminho: Raiz do projeto que será analisado.
        """
        try:
            resultado = ProjectScanner(caminho).escanear()
            if self._cancelar_event.is_set():
                self._fila.put(("cancelado", None))
            else:
                self._fila.put(("sucesso", resultado))
        except (OSError, PermissionError, ValueError, ErroVarreduraError) as erro:
            self._fila.put(("erro", str(erro)))

    def _processar_fila(self) -> None:
        """Processa resultados da thread e atualiza os widgets com segurança."""
        try:
            tipo, valor = self._fila.get_nowait()
        except queue.Empty:
            self.after(100, self._processar_fila)
            return

        self._selecao.analisar_btn.configure(state="normal")

        if tipo == "cancelado":
            self._progress.falhar()
            self._status.configure(text="● Cancelado", text_color=COR_ALERTA)
            self._log.adicionar(f"[{self._agora()}] Análise cancelada.")
        elif tipo == "erro":
            self._progress.falhar()
            self._status.configure(text="● Falha", text_color=COR_ERRO)
            self._log.adicionar(f"[{self._agora()}] ERRO: {valor}")
            ctk.messagebox.showerror("Erro na análise", str(valor))
        else:
            resultado = valor
            assert isinstance(resultado, ResultadoScanner)
            self._resultado = resultado
            self._progress.concluir()
            self._status.configure(text="● Concluído", text_color=COR_SUCESSO)
            self._log.adicionar(f"[{self._agora()}] Análise concluída.")

            # Árvore
            self._abas.arvore.delete("1.0", "end")
            self._abas.arvore.insert("1.0", resultado.para_arvore_texto())

            # Estatísticas
            self._abas.estatisticas_box.delete("1.0", "end")
            for ext, dados in resultado.estatisticas_extensao.items():
                self._abas.estatisticas_box.insert(
                    "end",
                    f"{ext}: {dados['quantidade']} arquivo(s)  —  "
                    f"total {MetricasFrame._formatar_tamanho(dados['tamanho_total'])}  —  "
                    f"médio {MetricasFrame._formatar_tamanho(dados['tamanho_medio'])}\n",
                )

            # JSON
            self._abas.json_box.delete("1.0", "end")
            self._abas.json_box.insert("1.0", resultado.para_json())

            # Métricas
            self._metricas.atualizar(
                resultado.total_arquivos,
                resultado.total_diretorios,
                resultado.tamanho_total_bytes,
                len(resultado.estatisticas_extensao),
            )

        self.after(100, self._processar_fila)

    @staticmethod
    def _agora() -> str:
        """Retorna o horário atual para timestamp dos logs.

        Returns:
            Horário local no formato ``HH:MM:SS``.
        """
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")


def main() -> None:
    """Cria a janela principal e inicia o loop gráfico."""
    DevAgentApp().mainloop()


if __name__ == "__main__":
    main()

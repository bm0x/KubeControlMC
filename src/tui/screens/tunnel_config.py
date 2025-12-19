from textual.screen import ModalScreen
from textual.widgets import Button, RichLog, Label, Static
from textual.containers import Vertical, Horizontal, Container
from textual.app import ComposeResult
import pyperclip

class TunnelConfigScreen(ModalScreen):
    CSS = """
    TunnelConfigScreen {
        align: center middle;
        background: rgba(0,0,0,0.8);
    }
    
    #tunnel-dialog {
        width: 85%;
        height: 80%;
        background: $surface;
        border: solid $accent;
        padding: 1;
        layout: vertical;
    }
    
    #tunnel-header {
        text-align: center;
        text-style: bold;
        padding-bottom: 1;
        border-bottom: solid $secondary;
        color: $accent;
        height: auto;
    }
    
    #tunnel-log {
        height: 1fr;
        border: solid $secondary;
        background: $surface-lighten-1;
        margin: 1 0;
        overflow-y: auto;
        padding: 1;
    }
    
    #claim-area {
        height: auto;
        background: $secondary;
        padding: 1;
        margin-bottom: 1;
        display: none;
    }
    
    #claim-link {
        width: 1fr;
        color: $accent-lighten-2;
        text-style: underline;
    }
    
    #actions {
        align: center middle;
        height: auto;
    }
    
    Button {
        margin-right: 1;
    }
    """
    
    def __init__(self, tunnel_manager):
        super().__init__()
        self.tunnel_manager = tunnel_manager
        self.claim_url = None

    def compose(self) -> ComposeResult:
        yield Container(
            Label("Configuración de Túnel Playit.gg", id="tunnel-header"),
            
            # Setup Log
            RichLog(id="tunnel-log", markup=True, auto_scroll=True),
            
            # Claim Area (Hidden until URL found)
            Horizontal(
                Label("🔗 Link de Vinculación:", classes="label"),
                Static("", id="claim-link"),
                Button("Copiar", id="btn-copy-link", variant="primary", classes="btn-small"),
                id="claim-area"
            ),
            
            # Actions
            Horizontal(
                Button("Cancelar / Cerrar", id="btn-close", variant="error"),
                Button("Minimizar (Segundo Plano)", id="btn-bg", variant="default"),
                id="actions"
            ),
            
            id="tunnel-dialog"
        )

    def on_mount(self):
        self.log_write("[cyan]Iniciando proceso de configuración...[/cyan]")
        self.log_write("[dim]Por favor espera a que se genere el link de vinculación.[/dim]")

    def log_write(self, message: str):
        log = self.query_one("#tunnel-log", RichLog)
        log.write(message)
        
        # Detect URL locally too, just in case, for highlighting
        if "https://" in message and "playit.gg" in message:
             # Extract URL rudimentary
             parts = message.split()
             for p in parts:
                 if "https://" in p:
                     self.show_claim_url(p.strip())

    def show_claim_url(self, url: str):
        self.claim_url = url
        area = self.query_one("#claim-area")
        link_lbl = self.query_one("#claim-link", Static)
        
        area.display = True
        link_lbl.update(url)
        self.log_write(f"[bold green]¡Link generado! Copialo y ábrelo en tu navegador.[/bold green]")

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        
        if btn_id == "btn-close":
            # If we close, maybe stop the tunnel? Or just dismiss?
            # User request: "avoid errors". Safe to stop if not claimed.
            self.dismiss(result="close")
            
        elif btn_id == "btn-bg":
            self.dismiss(result="background")
            
        elif btn_id == "btn-copy-link":
            if self.claim_url:
                try:
                    pyperclip.copy(self.claim_url)
                    self.log_write("[green]Link copiado al portapapeles.[/green]")
                except:
                    self.log_write("[red]No se pudo copiar (falta xclip/xsel). Copialo manualmente.[/red]")

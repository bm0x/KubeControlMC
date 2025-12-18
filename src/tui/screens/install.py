from textual.screen import ModalScreen
from textual.widgets import Label, Button, Select
from textual.containers import Container, Vertical

class InstallScreen(ModalScreen):
    """Modal screen for selecting server type to install."""
    
    CSS = """
    InstallScreen {
        align: center middle;
    }
    #dialog {
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        width: 60;
        height: auto;
    }
    Label {
        margin-bottom: 2;
        text-align: center;
        width: 100%;
    }
    Select {
        margin-bottom: 2;
    }
    """

    def __init__(self):
        super().__init__()
        self.selected_type = None

    def compose(self):
        yield Container(
            Vertical(
                Label("No se detectó ningún servidor instalado.", id="lbl-title"),
                Label("Selecciona el tipo de servidor para descargar e instalar:", id="lbl-desc"),
                Select([
                    ("PaperMC (Recomendado)", "paper"),
                    ("Folia (Experimental/Alto Rendimiento)", "folia"),
                    ("Velocity (Proxy)", "velocity")
                ], prompt="Selecciona una opción", id="select-type"),
                Button("Instalar", variant="success", id="btn-do-install", disabled=True),
                Button("Cancelar", variant="default", id="btn-cancel"),
                id="dialog"
            )
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        # Store the selection
        val = event.value
        # Check for Select.BLANK (sentinel value when nothing selected)
        if val is None or val == Select.BLANK:
            self.selected_type = None
            self.query_one("#btn-do-install").disabled = True
        else:
            self.selected_type = str(val)
            self.query_one("#btn-do-install").disabled = False
        self.log(f"[DEBUG] Select changed: {val} -> stored: {self.selected_type}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        self.log(f"[DEBUG] Button pressed: {btn_id}")
        
        if btn_id == "btn-do-install":
            if self.selected_type:
                self.log(f"[DEBUG] Dismissing with: {self.selected_type}")
                self.dismiss(self.selected_type)
            else:
                self.log("[DEBUG] No selection, not dismissing")
        elif btn_id == "btn-cancel":
            self.log("[DEBUG] Cancelled by user")
            self.dismiss(None)



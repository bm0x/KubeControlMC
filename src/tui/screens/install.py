from textual.screen import ModalScreen
from textual.widgets import Label, Button, Select
from textual.containers import Container, Vertical

class InstallScreen(ModalScreen):
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
                Button("Instalar", variant="success", id="btn-install", disabled=True),
                id="dialog"
            )
        )

    def on_select_changed(self, event: Select.Changed) -> None:
        self.query_one("#btn-install").disabled = event.value is None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-install":
            sel = self.query_one("#select-type").value
            self.dismiss(sel)

from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Input, Header, Footer
from textual.containers import Vertical, Horizontal, Container
from textual.app import ComposeResult
from src.core.config_manager import ConfigManager

class PropertiesEditorScreen(ModalScreen):
    CSS = """
    PropertiesEditorScreen {
        align: center middle;
        background: rgba(0,0,0,0.7);
    }
    
    #editor-dialog {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $accent;
        padding: 1;
    }
    
    #props-table {
        height: 1fr;
        border: solid $secondary;
        margin-bottom: 1;
    }
    
    #edit-area {
        height: auto;
        border-top: solid $secondary;
        padding-top: 1;
        margin-bottom: 1;
    }
    
    #key-label {
        width: 30%;
        content-align: right middle;
        padding-right: 1;
    }
    
    #value-input {
        width: 1fr;
    }
    
    #actions-row {
        align: center middle;
        height: auto;
    }
    
    Button {
        margin-right: 1;
    }
    """
    
    def __init__(self, server_dir: str):
        super().__init__()
        self.server_dir = server_dir
        self.properties = {}
        self.selected_key = None

    def compose(self) -> ComposeResult:
        yield Container(
            Label("[bold]Editor de Configuración (server.properties)[/bold]", id="title"),
            DataTable(id="props-table"),
            
            # Edit Area
            Horizontal(
                Label("Selecciona una propiedad...", id="key-label"),
                Input(placeholder="Valor", id="value-input", disabled=True),
                Button("Aplicar Cambio", id="btn-apply-val", variant="primary", disabled=True),
                id="edit-area"
            ),
            
            # Actions
            Horizontal(
                Button("Guardar y Cerrar", id="btn-save", variant="success"),
                Button("Cancelar", id="btn-cancel", variant="error"),
                id="actions-row"
            ),
            
            id="editor-dialog"
        )

    def on_mount(self):
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Propiedad", "Valor Actual")
        
        # Load properties
        self.load_properties()

    def load_properties(self):
        self.properties = ConfigManager.get_all_properties(self.server_dir)
        table = self.query_one(DataTable)
        table.clear()
        
        # Sort keys
        for key in sorted(self.properties.keys()):
            table.add_row(key, self.properties[key], key=key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        # Determine key from row_key if set, or get from cell
        # row_key was set to the property key
        key = event.row_key.value
        if not key: 
            return # Should not happen if set correctly
            
        self.selected_key = key
        val = self.properties.get(key, "")
        
        self.query_one("#key-label").update(f"[bold]{key}[/bold]:")
        inp = self.query_one("#value-input")
        inp.disabled = False
        inp.value = val
        self.query_one("#btn-apply-val").disabled = False
        inp.focus()

    def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        
        if btn_id == "btn-apply-val":
            self.apply_single_change()
        elif btn_id == "btn-save":
            self.save_and_exit()
        elif btn_id == "btn-cancel":
            self.dismiss()

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "value-input":
            self.apply_single_change()

    def apply_single_change(self):
        if not self.selected_key:
            return
            
        new_val = self.query_one("#value-input").value
        self.properties[self.selected_key] = new_val
        
        # Update table
        table = self.query_one(DataTable)
        table.update_cell(self.selected_key, "Valor Actual", new_val)
        
        # Feedback (optional, maybe toast?)
        # For now visual update in table is enough

    def save_and_exit(self):
        try:
            ConfigManager.save_all_properties(self.server_dir, self.properties)
            self.dismiss(result=True)
        except Exception as e:
            # In a modal, handling errors is tricky without another modal
            # We'll dismiss and let the main app log the error if we want, or simple print
            self.dismiss(result=False)

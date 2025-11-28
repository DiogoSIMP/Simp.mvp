import os
from datetime import datetime

def get_week_folder(base_folder: str):
    """
    Gera (e cria se não existir) a subpasta da semana atual.
    Exemplo: uploads/semanas/semana46
    """
    week_number = datetime.now().isocalendar()[1]
    week_folder = os.path.join(base_folder, "semanas", f"semana{week_number}")
    os.makedirs(week_folder, exist_ok=True)
    return week_folder

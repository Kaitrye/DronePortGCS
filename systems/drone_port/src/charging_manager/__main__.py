import sys
import os

# Добавляем корень проекта в путь
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, root_dir)


from src.charging_manager.src.charging_manager import main

if __name__ == "__main__":
    main()
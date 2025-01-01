import os
import ast
import discord
from typing import List, Dict

class CommandScanner:
    @staticmethod
    def scan_directory(directory: str) -> List[Dict]:
        commands = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        tree = ast.parse(content)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.FunctionDef):
                                if any(decorator.id == 'command' for decorator in node.decorator_list if isinstance(decorator, ast.Name)):
                                    commands.append({
                                        'name': node.name,
                                        'file': filepath,
                                        'module': os.path.splitext(os.path.basename(filepath))[0]
                                    })
                    except:
                        continue
        return commands

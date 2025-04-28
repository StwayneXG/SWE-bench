import os
import ast
import csv
import shlex
from typing import Dict
import argparse

# Enhanced Method Name Transformer
class MethodNameTransformer(ast.NodeTransformer):
    def __init__(self, method_mapping: Dict[str, str]):
        self.method_mapping = method_mapping
        self.has_changes = False
        
    def visit_Call(self, node: ast.Call) -> ast.Call:
        if isinstance(node.func, ast.Name) and node.func.id in self.method_mapping:
            old_name = node.func.id
            node.func.id = self.method_mapping[old_name]
            self.has_changes = True
        elif isinstance(node.func, ast.Attribute) and node.func.attr in self.method_mapping:
            old_name = node.func.attr
            node.func.attr = self.method_mapping[old_name]
            self.has_changes = True
        return self.generic_visit(node)
    
    def get_has_changes(self) -> bool:
        return self.has_changes

def modify_files(repo_path: str, csv_path: str, mode: str = "rename") -> None:
    """
    Modify Python files in the given repo based on CSV content.
    
    Args:
        repo_path (str): Path to the repo containing Python files.
        csv_path (str): Path to the CSV file containing method modifications.
        mode (str): "replace" to modify method bodies, "rename" to rename methods, or "both" to do both.
    """
    # Read CSV file
    csv_content = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        csv_content = list(reader)
    
    if mode in ["replace", "both"]:
        # validity_logger.info("Starting Patch Replacing strategy.")
        for row in csv_content:
            file_path = os.path.join(repo_path, row['file'])
            try:
                start_line, end_line = int(row['start_line']), int(row['end_line'])
                new_code = row['code'].split('\n')
                
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                lines[start_line-1:end_line] = [line + '\n' for line in new_code]
                
                with open(file_path, 'w') as f:
                    f.writelines(lines)
                
                # validity_logger.info(f"Updated method body in {file_path}")
            except Exception as e:
                print(f"Failed to process {file_path}: {str(e)}")
    
    if mode in ["rename", "both"]:
        # validity_logger.info("Starting Patch Renaming strategy.")
        method_mapping = {row['method_name']: row['new_method_name']
                          for row in csv_content if row['method_name'] != row['new_method_name']}
        
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        transformer = MethodNameTransformer(method_mapping)
                        modified_tree = transformer.visit(tree)
                        
                        if transformer.get_has_changes():
                            modified_code = ast.unparse(modified_tree)
                            with open(file_path, 'w') as f:
                                f.write(modified_code)
#                            print(f"Renamed methods in {file_path}")
                    except Exception as e:
                        print(f"Failed to process {file_path}: {str(e)}")

def main(csv_filename: str, repo_path: str = '/testbed', mode: str = "rename") -> None:
    modify_files(repo_path, csv_filename, mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_filename", type=str, required=True)
    parser.add_argument("--repo_path", type=str, default="/testbed")
    parser.add_argument("--mode", type=str, default="rename")
    args = parser.parse_args()

    main(args.csv_filename, args.repo_path, args.mode)
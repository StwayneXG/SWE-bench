import os
import csv
import builtins
import logging
from typing import Dict
import libcst as cst
import argparse

import logging

def get_console_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Creates and returns a logger that logs to the console only.

    Args:
        name (str): Name of the logger (usually use __name__).
        level (int): Logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers if already configured
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Avoid propagating logs to ancestor loggers (like root logger)
        logger.propagate = False

    return logger

logger = get_console_logger(__name__, level=logging.INFO)

class LibCSTMethodRenamer(cst.CSTTransformer):
    def __init__(self, method_mapping: Dict[str, str]):
        self.method_mapping = method_mapping
        self.has_changes = False

    def leave_FunctionDef(self, original_node, updated_node):
        if original_node.name.value in self.method_mapping:
            new_name = self.method_mapping[original_node.name.value]
            self.has_changes = True
            return updated_node.with_changes(name=cst.Name(new_name))
        return updated_node
    
    def leave_Attribute(self, original_node: cst.Attribute, updated_node: cst.Attribute) -> cst.CSTNode:
        if isinstance(updated_node.attr, cst.Name) and updated_node.attr.value in self.method_mapping:
            new_attr = cst.Name(self.method_mapping[updated_node.attr.value])
            self.has_changes = True
            return updated_node.with_changes(attr=new_attr)
        return updated_node

    def leave_Name(self, original_node: cst.Name, updated_node: cst.Name) -> cst.CSTNode:
        # Handles bare function references like: some_var = make_bytes
        if updated_node.value in self.method_mapping:
            self.has_changes = True
            return updated_node.with_changes(value=self.method_mapping[updated_node.value])
        return updated_node
    
    def leave_Call(self, original_node, updated_node):
        func = updated_node.func
        if isinstance(func, cst.Name) and func.value in self.method_mapping:
            new_name = self.method_mapping[func.value]
            self.has_changes = True
            return updated_node.with_changes(func=cst.Name(new_name))
        elif isinstance(func, cst.Attribute) and func.attr.value in self.method_mapping:
            new_attr = self.method_mapping[func.attr.value]
            self.has_changes = True
            return updated_node.with_changes(func=func.with_changes(attr=cst.Name(new_attr)))
        return updated_node

    def get_has_changes(self) -> bool:
        return self.has_changes


def guard_rails(old_method_name: str) -> bool:
    builtin_funcs = dir(builtins)
    common_names = {
        "fit", "predict", "transform", "get", "set", "update", "read", "write", "open", "close", "eval", "print",
        "format", "sum", "map", "filter", "reduce", "input", "type", "len", "all", "any", "abs", "min", "max",
        "next", "iter", "zip", "range", "super", "reversed", "sorted", "help", "dir", "delattr", "hasattr", "setattr",
        "vars", "isinstance", "issubclass", "compile", "globals", "locals", "callable", "classmethod", "staticmethod",
        "property", "slice", "hash", "id", "memoryview", "exec", "classmethod", "staticmethod", "complex", "int",
        "float", "str", "bytes", "bytearray", "bool", "enumerate", "list", "dict", "tuple", "set", "frozenset", "object"
    }

    if old_method_name in builtin_funcs or old_method_name in common_names or (old_method_name.startswith("__") and old_method_name.endswith("__")):
        return False
    return True


def modify_files(repo_path: str, csv_path: str, mode: str = "rename") -> None:
    """
    Modify Python files in the given repo based on CSV content using libcst to preserve comments.

    Args:
        repo_path (str): Path to the repo containing Python files.
        csv_path (str): Path to the CSV file containing method rename mappings.
    """
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        csv_content = list(reader)

    logger.debug(f"Renaming methods in repository in {repo_path}")

    method_mapping = {
        row['method_name']: row['new_method_name']
        for row in csv_content
        if row['method_name'] != row['new_method_name']
    }

    guarded_method_mapping = {
        old: new for old, new in method_mapping.items() if guard_rails(old)
    }

    for old in method_mapping:
        if old not in guarded_method_mapping:
            logger.debug(f"Skipping renaming of guarded method: {old}")

    logger.debug(f"Methods to be renamed:")
    for old, new in guarded_method_mapping.items():
        logger.debug(f"{old} → {new}")

    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()

                    tree = cst.parse_module(source_code)
                    transformer = LibCSTMethodRenamer(guarded_method_mapping)
                    modified_tree = tree.visit(transformer)

                    if transformer.get_has_changes():
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(modified_tree.code)

                        logger.debug(f"Renamed methods in {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to process {file_path}: {str(e)}")

def main(csv_filename: str, repo_path: str = '/testbed', mode: str = "rename") -> None:
    modify_files(repo_path, csv_filename, mode)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_filename", type=str, required=True)
    parser.add_argument("--repo_path", type=str, default="/testbed")
    parser.add_argument("--mode", type=str, default="rename")
    args = parser.parse_args()

    main(args.csv_filename, args.repo_path, args.mode)
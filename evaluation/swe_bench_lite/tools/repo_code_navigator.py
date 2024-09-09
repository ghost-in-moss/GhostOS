import os
import tree_sitter
from pydantic import BaseModel, Field
from typing import List, Optional
from tree_sitter import Language, Parser
from tree_sitter_languages import get_language, get_parser
import pylint.lint
from pylint.reporters.text import TextReporter
from io import StringIO


_PythonParser = get_parser('python')


class CodeLocation(BaseModel):
    file_path: str = Field(
        description="The full path to the file where the definition is found"
    )
    line_number: int = Field(
        description="The line number where the definition starts (1-indexed)"
    )
    column_number: int = Field(
        description="The column number where the definition starts (1-indexed)"
    )
    context: List[str] = Field(
        description="A list of strings representing the lines of code around the definition, typically including a few lines before and after for context"
    )

    def __str__(self):
        context_str = '\n'.join(f"    {line.rstrip()}" for line in self.context)
        return f"Definition found:\n" \
               f"  File: {self.file_path}\n" \
               f"  Line: {self.line_number}, Column: {self.column_number}\n" \
               f"  Context:\n{context_str}"



class CodeReference(BaseModel):
    file_path: str = Field(
        description="The full path to the file where the reference is found"
    )
    line_number: int = Field(
        description="The line number where the reference is found (1-indexed)"
    )
    column_number: int = Field(
        description="The column number where the reference starts (1-indexed)"
    )
    context: str = Field(
        description="The line of code containing the reference"
    )

    def __str__(self):
        return f"Reference found:\n" \
               f"  File: {self.file_path}\n" \
               f"  Line: {self.line_number}, Column: {self.column_number}\n" \
               f"  Context: {self.context.strip()}"



class RepositoryCodeNavigator:
    def __init__(self, repo_path):
        self.parser = _PythonParser
        self.repo_path = os.path.abspath(repo_path)
        self.file_trees = {}
        self._parse_repository()

    def _parse_repository(self):
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.relpath(os.path.join(root, file), self.repo_path)
                    with open(os.path.join(self.repo_path, file_path), 'r') as f:
                        code = f.read()
                    tree = self.parser.parse(bytes(code, 'utf8'))
                    self.file_trees[file_path] = tree

    def go_to_definition(self, file_path, line_number, target_string) -> Optional[CodeLocation]:
        # Convert relative path to absolute path
        abs_file_path = os.path.join(self.repo_path, file_path)
        
        # First, try to find the definition in the current file
        definition = self._find_definition_in_file(abs_file_path, line_number, target_string)
        if definition:
            # Convert absolute path back to relative path in the result
            definition.file_path = os.path.relpath(definition.file_path, self.repo_path)
            return definition

        # If not found, search in all files
        for rel_path, tree in self.file_trees.items():
            definition = self._find_definition_in_tree(tree, target_string)
            if definition:
                # Path is already relative in this case
                return definition

        return None
    
    def find_references(self, file_path, line_number, target_string) -> List[CodeReference]:
        """
        TODO: IDE的find_usages功能并不需要每次都遍历所有文件，只需要遍历与当前文件相关的文件即可。可以通过文件的import关系来确定。
        """
        references = []
        
        # Search in all files
        for rel_path, tree in self.file_trees.items():
            # Read the content of the file
            with open(os.path.join(self.repo_path, rel_path), 'r') as file:
                content = file.read()
            
            root_node = tree.root_node
            cursor = root_node.walk()
            
            reached_root = False
            while not reached_root:
                if cursor.node.type == 'identifier' and cursor.node.text.decode('utf8') == target_string:
                    start_line = cursor.node.start_point[0] + 1
                    start_column = cursor.node.start_point[1] + 1
                    context_line = content.splitlines()[start_line - 1]
                    references.append(CodeReference(
                        file_path=rel_path,  # Use relative path
                        line_number=start_line,
                        column_number=start_column,
                        context=context_line
                    ))
                
                if not cursor.goto_first_child():
                    while not cursor.goto_next_sibling():
                        if not cursor.goto_parent():
                            reached_root = True
                            break
        return references

    def find_implementations(self, target_string: str) -> List[CodeLocation]:
        implementations = []
        for rel_path, tree in self.file_trees.items():
            root_node = tree.root_node
            implementation_nodes = self._find_implementation_nodes(root_node, target_string)
            
            if implementation_nodes:
                file_path = os.path.join(self.repo_path, rel_path)
                with open(file_path, 'r') as file:
                    content = file.read()
                    lines = content.splitlines()
                
                for node in implementation_nodes:
                    start_line = node.start_point[0] + 1
                    start_column = node.start_point[1] + 1
                    
                    context_start = max(0, start_line - 3)
                    context_end = min(len(lines), start_line + 4)
                    context = lines[context_start:context_end]
                    
                    implementations.append(CodeLocation(
                        file_path=rel_path,
                        line_number=start_line,
                        column_number=start_column,
                        context=context
                    ))
        
        return implementations

    def _find_implementation_nodes(self, root_node, target_string):
        implementation_nodes = []
        cursor = root_node.walk()
        
        reached_root = False
        while not reached_root:
            if cursor.node.type in ['function_definition', 'class_definition', 'method_definition']:
                name_node = cursor.node.child_by_field_name('name')
                if name_node and name_node.text.decode('utf8') == target_string:
                    implementation_nodes.append(cursor.node)
            
            if not cursor.goto_first_child():
                while not cursor.goto_next_sibling():
                    if not cursor.goto_parent():
                        reached_root = True
                        break
        
        return implementation_nodes

    def _find_definition_in_file(self, file_path, line_number, target_string):
        with open(file_path, 'r') as file:
            content = file.read()
    
        tree = self.parser.parse(bytes(content, 'utf8'))
        root_node = tree.root_node
    
        target_node = self._find_node_by_line_and_string(root_node, line_number, target_string)
    
        if target_node:
            start_line = target_node.start_point[0]
            end_line = target_node.end_point[0]
            
            # Capture more lines before and after for context
            context_start = max(0, start_line - 3)
            context_end = min(len(content.splitlines()), end_line + 4)
            
            context_lines = content.splitlines()[context_start:context_end]
            
            return CodeLocation(
                file_path=file_path,
                line_number=start_line + 1,
                column_number=target_node.start_point[1] + 1,
                context=context_lines
            )
        
        return None

    def _find_definition_in_tree(self, tree, target_string) -> Optional[CodeLocation]:
        root_node = tree.root_node
        definition_node = self._find_definition(root_node, target_string)
        if definition_node:
            file_path = next((path for path, t in self.file_trees.items() if t == tree), None)
            if file_path:
                with open(os.path.join(self.repo_path, file_path), 'r') as file:
                    lines = file.readlines()
                def_line = definition_node.start_point[0] + 1
                def_column = definition_node.start_point[1] + 1
                context = lines[max(0, def_line-3):def_line+2]
                return CodeLocation(
                    file_path=file_path,  # This is already a relative path
                    line_number=def_line,
                    column_number=def_column,
                    context=context
                )
        return None

    def _find_node_by_line_and_string(self, root_node, line_number, target_string):
        for node in root_node.children:
            if node.start_point[0] + 1 <= line_number <= node.end_point[0] + 1:
                cursor = node.walk()
                reached_end = False
                while not reached_end:
                    current_node = cursor.node
                    if current_node.type in ['function_definition', 'class_definition', 'method_definition'] and \
                       current_node.child_by_field_name('name').text.decode('utf8') == target_string:
                        return current_node
                    if not cursor.goto_first_child():
                        while not cursor.goto_next_sibling():
                            if not cursor.goto_parent():
                                reached_end = True
                                break
        return None

    def _find_definition_from_node(self, start_node, target_string):
        current = start_node
        while current.parent:
            current = current.parent
            if current.type in ['function_definition', 'class_definition', 'assignment', 'expression_statement']:
                # 检查是否是目标的定义
                if self._is_definition_of(current, target_string):
                    return current
        return None

    def _is_definition_of(self, node, target_string):
        if node.type in ['function_definition', 'class_definition']:
            name_node = node.child_by_field_name('name')
            return name_node and name_node.text.decode('utf8') == target_string
        elif node.type == 'assignment':
            left_side = node.child_by_field_name('left')
            if left_side:
                if left_side.type == 'identifier':
                    return left_side.text.decode('utf8') == target_string
                elif left_side.type == 'pattern_list':
                    # Handle multiple assignments
                    for child in left_side.children:
                        if child.type == 'identifier' and child.text.decode('utf8') == target_string:
                            return True
        elif node.type == 'expression_statement':
            child = node.child_by_field_name('expression')
            if child and child.type == 'assignment':
                return self._is_definition_of(child, target_string)
        elif node.type == 'identifier' and node.text.decode('utf8') == target_string:
            # Check if the identifier is part of an assignment
            parent = node.parent
            if parent and parent.type == 'assignment':
                return True
        return False

    def _find_definition(self, root_node, target_string):
        cursor = root_node.walk()
        
        reached_root = False
        while not reached_root:
            if cursor.node.type in ['function_definition', 'class_definition', 'assignment', 'expression_statement']:
                if self._is_definition_of(cursor.node, target_string):
                    return cursor.node
            
            if not cursor.goto_first_child():
                while not cursor.goto_next_sibling():
                    if not cursor.goto_parent():
                        reached_root = True
                        break
        return None



# 使用示例
if __name__ == "__main__":
    repo_path = '/home/llm/Project/PythonProjects/auto-code-rover'
    helper = RepositoryCodeNavigator(repo_path)
    
    file_path = 'app/api/manage.py'  # Now using relative path
    target_string = 'SearchManager'

    definition = helper.go_to_definition(file_path, 81, target_string)
    print(f"Definition: {definition}")


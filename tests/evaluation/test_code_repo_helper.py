import os
import sys

# Print sys.path for debugging
print("sys.path:", sys.path)

from evaluation.swe_bench_lite.tools.repo_code_navigator import RepositoryCodeNavigator, CodeLocation, CodeReference

def setup_repo_helper():
    # Using the tests directory as the repo path
    repo_path = os.path.dirname(os.path.dirname(__file__))
    return RepositoryCodeNavigator(repo_path)

def test_go_to_definition():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'MockClass'
    
    definition = repo_helper.go_to_definition(file_path, 1, target_string)
    
    print(f"Definition: {definition}")  # Add this line to print the definition
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == file_path
    assert definition.line_number == 1  # MockClass should be defined on line 1
    assert 'class MockClass:' in definition.context, f"Expected 'class MockClass:' in context, but got: {definition.context}"

def test_go_to_definition_method():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'mock_method'
    
    definition = repo_helper.go_to_definition(file_path, 5, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == file_path
    assert definition.line_number == 5  # mock_method should be defined on line 5
    assert any('def mock_method(self):' in line for line in definition.context), f"Expected 'def mock_method(self):' in context, but got: {definition.context}"

def test_go_to_definition_function():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'mock_function'
    
    definition = repo_helper.go_to_definition(file_path, 8, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == file_path
    assert definition.line_number == 8  # mock_function should be defined on line 8
    assert 'def mock_function():' in definition.context

def test_go_to_definition_constant():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'MOCK_CONSTANT'
    
    definition = repo_helper.go_to_definition(file_path, 11, target_string)
    
    print(f"Context: {definition.context}")  # Add this line to print the context
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == file_path
    assert definition.line_number == 11  # MOCK_CONSTANT should be defined on line 11
    context_str = '\n'.join(definition.context)
    assert 'MOCK_CONSTANT = ' in context_str

def test_go_to_definition_not_found():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'NonExistentClass'
    
    definition = repo_helper.go_to_definition(file_path, 1, target_string)
    
    assert definition is None

# Placeholder tests for other methods
def test_find_references():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'MockClass'
    
    references = repo_helper.find_references(file_path, 1, target_string)
    
    print(f"References: {references}")  # Add this line to print the references
    
    assert isinstance(references, list)
    assert len(references) > 0
    assert all(isinstance(ref, CodeReference) for ref in references)
    
    # Print each reference for debugging
    for ref in references:
        print(f"Reference found: {ref.file_path} at line {ref.line_number}, column {ref.column_number}")
    
    # Check if there's a reference in both mock_code.py and mock_code_2.py
    assert any(ref.file_path == 'evaluation/mock_code.py' for ref in references), "Expected reference in 'evaluation/mock_code.py' not found"
    assert any(ref.file_path == 'evaluation/mock_code_2.py' for ref in references), "Expected reference in 'evaluation/mock_code_2.py' not found"

def test_find_references_method():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'mock_method'
    
    references = repo_helper.find_references(file_path, 5, target_string)
    
    assert isinstance(references, list)
    assert len(references) > 0
    assert all(isinstance(ref, CodeReference) for ref in references)
    
    # Check if there's a reference in mock_code_2.py
    assert any(ref.file_path == 'evaluation/mock_code_2.py' for ref in references)

def test_find_references_constant():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'MOCK_CONSTANT'
    
    references = repo_helper.find_references(file_path, 11, target_string)
    
    assert isinstance(references, list)
    assert len(references) > 0
    assert all(isinstance(ref, CodeReference) for ref in references)

def test_find_references_not_found():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'NonExistentIdentifier'
    
    references = repo_helper.find_references(file_path, 1, target_string)
    
    assert isinstance(references, list)
    assert len(references) == 0

def test_get_lint_errors():
    # This test is a placeholder and should be implemented when get_lint_errors is ready
    pass

def test_cross_file_class_definition():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code_2.py'
    target_string = 'MockClass'
    
    definition = repo_helper.go_to_definition(file_path, 1, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == 'evaluation/mock_code.py'
    assert definition.line_number == 1
    assert 'class MockClass:' in '\n'.join(definition.context)

def test_cross_file_method_definition():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code_2.py'
    target_string = 'mock_method'
    
    definition = repo_helper.go_to_definition(file_path, 7, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == 'evaluation/mock_code.py'
    assert definition.line_number == 5
    assert 'def mock_method(self):' in '\n'.join(definition.context)

def test_cross_file_constant_reference():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'ANOTHER_MOCK_CONSTANT'
    
    definition = repo_helper.go_to_definition(file_path, 1, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == 'evaluation/mock_code_2.py'
    assert 'ANOTHER_MOCK_CONSTANT = ' in '\n'.join(definition.context)

def test_cross_file_function_reference():
    repo_helper = setup_repo_helper()
    file_path = 'evaluation/mock_code.py'
    target_string = 'another_mock_function'
    
    definition = repo_helper.go_to_definition(file_path, 1, target_string)
    
    assert isinstance(definition, CodeLocation)
    assert definition.file_path == 'evaluation/mock_code_2.py'
    assert 'def another_mock_function(value):' in '\n'.join(definition.context)

if __name__ == "__main__":
    test_go_to_definition()
    test_go_to_definition_method()
    test_go_to_definition_function()
    test_go_to_definition_constant()
    test_go_to_definition_not_found()
    test_cross_file_class_definition()
    test_cross_file_method_definition()
    test_cross_file_constant_reference()
    test_cross_file_function_reference()
    test_find_references()
    test_find_references_method()
    test_find_references_constant()
    test_find_references_not_found()
    print("All tests passed!")

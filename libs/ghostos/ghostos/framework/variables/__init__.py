from ghostos.contracts.variables import Variables
from ghostos.framework.variables.variables_impl import VariablesImpl, WorkspaceVariablesProvider
from ghostos.framework.storage import MemStorage

test_variables = VariablesImpl(MemStorage())

__all__ = ("Variables", "VariablesImpl", "WorkspaceVariablesProvider", "test_variables")

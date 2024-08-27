import hide
import os


from hide.model import Repository
from hide.toolkit import Toolkit

hc = hide.Client()

project = hc.create_project(
    repository=Repository(url="https://github.com/liz-starfield/LizAgents.git"),
)

toolkit = Toolkit(project=project, client=hc)
#
# # your_agent.with_tools(toolkit).run("Do stuff")
print("do stuff")


